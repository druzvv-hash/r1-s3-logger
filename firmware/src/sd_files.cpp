#include "sd_files.h"
#include "pins.h"
#include "recorder.h"
#include <SD.h>
#include <SPI.h>
#include <esp_system.h>
#include <atomic>
#include <cstring>
#include <memory>
#include <algorithm>

namespace sd_files {
namespace {
QueueHandle_t requests=nullptr, responses=nullptr;
SemaphoreHandle_t gate=nullptr;
std::atomic<bool> busy{false};
File file;
uint32_t session=0, expectedSize=0, touched=0;
bool directory=false;
char directoryPath[PATH_BYTES];
struct Work { uint32_t id, expires; Request request; };
struct Done { uint32_t id; Response response; };

String quote(const char* text){
    String s="\"";
    for(;*text;++text){
        const uint8_t c=*text;
        if(c=='"'||c=='\\'){s+='\\';s+=char(c);}
        else if(c<32){char escaped[7];snprintf(escaped,sizeof(escaped),"\\u%04x",c);s+=escaped;}
        else s+=char(c);
    }
    return s+'"';
}
void close(){file.close();SD.end();session=0;busy.store(false);}
void error(Response& r,const char* message){
    r.ok=false;const String s="{\"ok\":false,\"message\":"+quote(message)+"}";
    s.toCharArray(r.json,sizeof(r.json));
}
bool mount(){
    pinMode(pins::SD_CS,OUTPUT);digitalWrite(pins::SD_CS,HIGH);
    SPI.begin(pins::SD_SCK,pins::SD_MISO,pins::SD_MOSI,pins::SD_CS);
    return SD.begin(pins::SD_CS,SPI,10000000,"/sd",5,false)&&SD.cardType()!=CARD_NONE;
}
void page(Response& r){
    String json="{\"ok\":true,\"session\":"+String(session)+",\"entries\":[";
    unsigned count=0;
    // Six worst-case FAT names + hex paths fit the bounded UART JSON reply.
    while(count<6){
        File entry=file.openNextFile(FILE_READ);
        if(!entry){r.more=false;break;}
        const String name=String(entry.name());
        const String path=String(directoryPath)+(strcmp(directoryPath,"/")?"/":"")+name;
        if(count++)json+=',';
        json+="{\"name\":"+quote(name.c_str())+",\"directory\":"+(entry.isDirectory()?"true":"false")+",\"size\":"+String(entry.size());
        json+=",\"path\":"+(path.length()<PATH_BYTES?quote(encodePath(path.c_str()).c_str()):String("null"))+"}";
        entry.close();r.more=true;
    }
    r.ok=true;r.session=session;
    json+=String("],\"more\":")+(r.more?"true":"false")+"}";
    if(json.length()>=sizeof(r.json)){error(r,"Directory response too large");close();return;}
    json.toCharArray(r.json,sizeof(r.json));
    if(!r.more)close();
}
uint32_t crc32(const uint8_t* data,size_t n){
    uint32_t crc=0xffffffff;
    for(size_t i=0;i<n;++i){crc^=data[i];for(unsigned b=0;b<8;++b)crc=(crc>>1)^((crc&1)?0xedb88320:0);}
    return ~crc;
}
void execute(const Request& q,Response& r){
    if(session&&millis()-touched>30000)close();
    if(recorder::busy()){error(r,"Stop recording before reading SD files");return;}
    if(q.op==Op::Close){
        if(session&&q.session!=session){error(r,"Expired or foreign file session");return;}
        close();r.ok=true;strlcpy(r.json,"{\"ok\":true}",sizeof(r.json));return;
    }
    if(q.op==Op::List||q.op==Op::Open||q.op==Op::Check){
        if(session){error(r,"SD busy: another file transfer is active");return;}
        if(!mount()){close();error(r,"SD mount failed: check card and connection");return;}
        file=SD.open(q.op==Op::Check?"/":q.path,FILE_READ);
        if(!file){close();error(r,"File or directory not found");return;}
        directory=file.isDirectory();
        if(q.op==Op::Check){const bool ok=directory;close();r.ok=ok;if(ok)strlcpy(r.json,"{\"ok\":true}",sizeof(r.json));else error(r,"SD root read failed");return;}
        if(directory!=(q.op==Op::List)){close();error(r,"Wrong file type");return;}
        session=esp_random();if(!session)session=1;busy.store(true);
        expectedSize=file.size();touched=millis();
        if(directory){strlcpy(directoryPath,q.path,sizeof(directoryPath));page(r);return;}
        r.ok=true;r.session=session;r.size=expectedSize;
        snprintf(r.json,sizeof(r.json),"{\"ok\":true,\"session\":%lu,\"size\":%lu,\"chunk_bytes\":%u}",
                 static_cast<unsigned long>(session),static_cast<unsigned long>(expectedSize),unsigned(CHUNK));
        return;
    }
    if(!session||session!=q.session){error(r,"File session expired: restart download");return;}
    touched=millis();
    if(q.op==Op::Next&&directory){page(r);return;}
    if(q.op!=Op::Read||directory){error(r,"Wrong file operation");return;}
    if(file.size()!=expectedSize||q.offset>expectedSize){error(r,"File changed or invalid offset");close();return;}
    const size_t amount=std::min(size_t(expectedSize-q.offset),CHUNK);
    if(!file.seek(q.offset)||(amount&&file.read(r.data,amount)!=amount)){
        error(r,"SD read interrupted: download incomplete");close();return;
    }
    r.ok=true;r.session=session;r.size=expectedSize;r.offset=q.offset;r.count=amount;r.crc=crc32(r.data,amount);
}
void task(void*){
    Work work{};static Done done;
    for(;;){
        recorder::storageStep(session!=0);
        if(xQueueReceive(requests,&work,pdMS_TO_TICKS(recorder::busy()?1:20))==pdTRUE){
            done={};done.id=work.id;
            if(int32_t(millis()-work.expires)>0)error(done.response,"Expired SD request");
            else execute(work.request,done.response);
            xQueueOverwrite(responses,&done);
        }
        if(session&&millis()-touched>30000)close();
    }
}
int nibble(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
bool number(const char* s,uint32_t& n){
    if(!*s||strlen(s)>10)return false;uint64_t v=0;
    for(;*s;++s){if(*s<'0'||*s>'9')return false;v=v*10+*s-'0';}
    if(v>UINT32_MAX)return false;n=v;return true;
}
}
bool decodePath(const char* hex,char* output){
    const size_t n=strlen(hex);if(n<2||n%2||n/2>=PATH_BYTES)return false;
    for(size_t i=0;i<n;i+=2){int a=nibble(hex[i]),b=nibble(hex[i+1]);if(a<0||b<0)return false;const unsigned c=a*16+b;
        if(c<32||c==127||c=='\\'||c==':')return false;output[i/2]=char(c);}
    output[n/2]=0;
    if(output[0]!='/'||strstr(output,"//"))return false;
    if(n==2)return true;
    if(output[n/2-1]=='/')return false;
    const char* part=output+1;
    while(*part){const char* end=strchr(part,'/');const size_t len=end?size_t(end-part):strlen(part);
        if((len==1&&part[0]=='.')||(len==2&&part[0]=='.'&&part[1]=='.'))return false;
        if(!end)break;part=end+1;}
    return true;
}
String encodePath(const char* p){String s;const char* h="0123456789abcdef";for(;*p;++p){s+=h[uint8_t(*p)>>4];s+=h[uint8_t(*p)&15];}return s;}
void begin(){
    requests=xQueueCreate(1,sizeof(Work));responses=xQueueCreate(1,sizeof(Done));gate=xSemaphoreCreateMutex();
    if(requests&&responses&&gate)xTaskCreatePinnedToCore(task,"sd-files",16384,nullptr,1,nullptr,1);
}
bool request(const Request& input,Response& output){
    if(!gate||xSemaphoreTake(gate,pdMS_TO_TICKS(100))!=pdTRUE){error(output,"SD request busy");return false;}
    static uint32_t next=0;Work work{};work.id=++next;work.expires=millis()+7000;work.request=input;
    // Heap storage avoids stacking two 8 KiB responses on the HTTP/UART task stack.
    auto done=std::unique_ptr<Done>(new(std::nothrow) Done);
    bool received=false;
    if(done&&xQueueSend(requests,&work,0)==pdTRUE){
        const uint32_t began=millis();
        while(millis()-began<8000){if(xQueueReceive(responses,done.get(),pdMS_TO_TICKS(100))==pdTRUE&&done->id==work.id){received=true;break;}}
    }
    if(received)output=done->response;else error(output,"SD timeout: download incomplete");
    xSemaphoreGive(gate);return received&&output.ok;
}
bool active(){return busy.load();}
String protocol(const char* command){
    char text[600];if(strlen(command)>=sizeof(text))return "{\"ok\":false,\"message\":\"File command too large\"}";
    strlcpy(text,command,sizeof(text));char* save=nullptr;
    char* op=strtok_r(text," ",&save);char* arg=strtok_r(nullptr," ",&save);char* offset=strtok_r(nullptr," ",&save);
    Request q;bool valid=op!=nullptr;
    if(valid&&(!strcmp(op,"LIST")||!strcmp(op,"OPEN"))){q.op=!strcmp(op,"LIST")?Op::List:Op::Open;valid=arg&&!offset&&decodePath(arg,q.path);}
    else if(valid&&(!strcmp(op,"NEXT")||!strcmp(op,"CLOSE")||!strcmp(op,"READ"))){
        q.op=!strcmp(op,"NEXT")?Op::Next:!strcmp(op,"CLOSE")?Op::Close:Op::Read;
        valid=arg&&number(arg,q.session)&&(q.op==Op::Read?(offset&&number(offset,q.offset)):!offset);
    }else valid=false;
    if(strtok_r(nullptr," ",&save))valid=false;
    if(!valid)return "{\"ok\":false,\"message\":\"Invalid file command or path\"}";
    Response r;if(!request(q,r)||q.op!=Op::Read)return String(r.json);
    String s="{\"ok\":true,\"session\":"+String(r.session)+",\"size\":"+String(r.size)+",\"offset\":"+String(r.offset)+",\"crc32\":"+String(r.crc)+",\"hex\":\"";
    s.reserve(s.length()+r.count*2+3);const char* h="0123456789abcdef";
    for(size_t i=0;i<r.count;++i){s+=h[r.data[i]>>4];s+=h[r.data[i]&15];}
    return s+"\"}";
}
}
