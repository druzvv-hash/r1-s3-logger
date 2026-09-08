#include "test_panel.h"
#include "firmware_version.h"
#include "settings.h"
#include "ina228_test.h"
#include "rtc_test.h"
#include "recording_memory.h"
#include "live_history.h"
#include "sd_files.h"
#include "recorder.h"
#include "panel_assets.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_system.h>
#include <atomic>
#include <cstring>

namespace {
constexpr size_t STATE_BYTES=8192, COMMAND_BYTES=3100;
char cached[STATE_BYTES]="{\"ready\":false}";
portMUX_TYPE snapshotLock=portMUX_INITIALIZER_UNLOCKED;
char bootId[9], ssid[24], password[17];
std::atomic<bool> networkReady{false};
PanelAction ownerAction=nullptr;
struct Command { uint32_t id, expires; bool legacy; char text[COMMAND_BYTES]; };
struct Reply { uint32_t id; char json[256]; };
QueueHandle_t commands=nullptr, replies=nullptr;
SemaphoreHandle_t commandGate=nullptr;

String snapshot(){
    char copy[STATE_BYTES];
    portENTER_CRITICAL(&snapshotLock);memcpy(copy,cached,sizeof(copy));portEXIT_CRITICAL(&snapshotLock);
    return String(copy);
}
String quoted(const char* p){
    String s="\"";
    for(;*p;++p){if(*p=='"'||*p=='\\')s+='\\';if(uint8_t(*p)>=32)s+=*p;}
    return s+'"';
}
String result(bool ok,const char* message){
    return String("{\"ok\":")+(ok?"true":"false")+",\"message\":"+quoted(message)+",\"revision\":"+String(settingsRevision())+"}";
}
int nibble(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
String execute(const char* text){
    char boot[9]={},verb[16]={};unsigned revision=0;int consumed=0;
    if(sscanf(text,"%8s %u %15s%n",boot,&revision,verb,&consumed)!=3)return result(false,"Malformed command");
    if(strcmp(boot,bootId)||revision!=settingsRevision())return result(false,"STALE: reload settings from device before retrying");
    const char* arg=text+consumed;if(*arg==' ')++arg;
    const char* message="OK";bool ok=false;
    if(!strcmp(verb,"APPLY")){
        const size_t n=strlen(arg);
        if(!n||n%2||n>2944)return result(false,"Invalid payload length");
        settings::Bytes bytes;bytes.reserve(n/2);
        for(size_t i=0;i<n;i+=2){int a=nibble(arg[i]),b=nibble(arg[i+1]);if(a<0||b<0)return result(false,"Invalid payload hex");bytes.push_back(a*16+b);}
        ok=panelApplySettings(bytes,message);
    }else if(!strcmp(verb,"SAVE")&&!*arg){ok=panelSaveSettings(message);}
    else if(ownerAction){ok=ownerAction(verb,arg,message);}
    else message="Hardware owner unavailable";
    return result(ok,message);
}

// Both transports share one gate and one owner queue; only the owner touches I2C.
String submit(const char* body,bool legacy=false){
    if(!commandGate||strlen(body)>=COMMAND_BYTES||xSemaphoreTake(commandGate,pdMS_TO_TICKS(100))!=pdTRUE)
        return "{\"ok\":false,\"message\":\"Device busy\"}";
    static uint32_t nextId=0;
    Command cmd{};cmd.id=++nextId;cmd.expires=millis()+7000;cmd.legacy=legacy;
    strlcpy(cmd.text,body,sizeof(cmd.text));
    Reply reply{};bool received=false;
    if(xQueueSend(commands,&cmd,0)==pdTRUE){
        const uint32_t began=millis();
        while(millis()-began<8000){
            if(xQueueReceive(replies,&reply,pdMS_TO_TICKS(100))==pdTRUE && reply.id==cmd.id){received=true;break;}
        }
    }
    xSemaphoreGive(commandGate);
    return received?String(reply.json):String("{\"ok\":false,\"message\":\"Timeout; refresh state before retrying\"}");
}
bool cursorValue(const char* arg,uint64_t& cursor){
    if(!*arg||strlen(arg)>16)return false;cursor=0;
    for(;*arg;++arg){if(*arg<'0'||*arg>'9')return false;cursor=cursor*10+*arg-'0';}
    return cursor<=9007199254740991ULL; // Exact browser integer range.
}
String live(const char* arg){
    uint64_t cursor=0;
    if(!cursorValue(arg,cursor))return "{\"ok\":false,\"message\":\"Invalid live cursor\"}";
    String s=liveHistoryJson(cursor);s.remove(s.length()-1);
    return s+",\"boot\":"+quoted(bootId)+"}";
}
void serialTask(void*){
    char line[3200];size_t used=0;bool overflow=false;
    for(;;){
        while(Serial.available()){
            const char c=Serial.read();
            if(c=='\r')continue;
            if(c!='\n'){if(used<sizeof(line)-1)line[used++]=c;else overflow=true;continue;}
            line[used]=0;
            if(!overflow&&used){
                if(!panelHandleSerial(line))submit(line,true);
            }
            used=0;overflow=false;
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void downloadTask(void*){
    WebServer server(81);
    server.on("/api/download",HTTP_GET,[&]{
        sd_files::Request q;q.op=sd_files::Op::Open;
        if(!sd_files::decodePath(server.arg("path").c_str(),q.path)){
            server.send(400,"text/plain","Invalid file path");return;
        }
        sd_files::Response r;
        if(!sd_files::request(q,r)){server.send(409,"application/json",r.json);return;}
        const uint32_t id=r.session,size=r.size;
        const char* name=strrchr(q.path,'/')+1;
        String encoded;const char* hex="0123456789ABCDEF";
        for(const char* p=name;*p;++p){encoded+='%';encoded+=hex[uint8_t(*p)>>4];encoded+=hex[uint8_t(*p)&15];}
        server.sendHeader("Content-Disposition","attachment; filename=\"r1s3-download.bin\"; filename*=UTF-8''"+encoded);
        server.sendHeader("Cache-Control","no-store");server.sendHeader("X-Content-Type-Options","nosniff");
        server.setContentLength(size);server.send(200,"application/octet-stream","");
        WiFiClient client=server.client();bool complete=true;
        for(uint32_t offset=0;offset<size&&client.connected();){
            q.op=sd_files::Op::Read;q.session=id;q.offset=offset;
            if(!sd_files::request(q,r)||!r.count){complete=false;break;}
            size_t sent=0;const uint32_t began=millis();
            while(sent<r.count&&client.connected()&&millis()-began<10000){
                sent+=client.write(r.data+sent,r.count-sent);vTaskDelay(pdMS_TO_TICKS(1));
            }
            if(sent!=r.count){complete=false;break;}offset+=r.count;
        }
        if(!complete)client.stop(); // Content-Length makes a partial transfer fail at the receiver.
        q.op=sd_files::Op::Close;q.session=id;sd_files::request(q,r);
    });
    server.begin();
    for(;;){server.handleClient();vTaskDelay(pdMS_TO_TICKS(5));}
}

void webTask(void*){
    WiFi.mode(WIFI_AP);
    networkReady.store(WiFi.softAP(ssid,password,1,0,2));
    xTaskCreatePinnedToCore(downloadTask,"file-http",24576,nullptr,1,nullptr,0);
    WebServer server(80);
    const char* headers[]={"X-R1-Panel","Origin"};server.collectHeaders(headers,2);
    server.on("/",HTTP_GET,[&]{server.sendHeader("Cache-Control","no-store");server.sendHeader("Content-Encoding","gzip");server.send_P(200,"text/html; charset=utf-8",reinterpret_cast<const char*>(PANEL_HTML),sizeof(PANEL_HTML));});
    server.on("/api/state",HTTP_GET,[&]{server.sendHeader("Cache-Control","no-store");server.send(200,"application/json",snapshot());});
    server.on("/api/live",HTTP_GET,[&]{server.sendHeader("Cache-Control","no-store");server.send(200,"application/json",live(server.hasArg("after")?server.arg("after").c_str():"0"));});
    server.on("/api/files",HTTP_GET,[&]{
        server.sendHeader("Cache-Control","no-store");
        server.send(200,"application/json",sd_files::protocol(server.arg("command").c_str()));
    });
    server.on("/api/download",HTTP_GET,[&]{
        char path[sd_files::PATH_BYTES];
        if(!sd_files::decodePath(server.arg("path").c_str(),path)){server.send(400,"text/plain","Invalid file path");return;}
        server.sendHeader("Cache-Control","no-store");
        server.sendHeader("Location",String("http://")+WiFi.softAPIP().toString()+":81/api/download?path="+sd_files::encodePath(path));
        server.send(302,"text/plain","");
    });
    server.on("/api/command",HTTP_POST,[&]{
        if(server.header("X-R1-Panel")!="1" || (server.hasHeader("Origin")&&server.header("Origin")!=String("http://")+server.hostHeader())){server.send(403,"application/json","{\"ok\":false,\"message\":\"Origin/header rejected\"}");return;}
        const String body=server.arg("plain");
        if(body.length()==0||body.length()>=COMMAND_BYTES){server.send(413,"application/json","{\"ok\":false,\"message\":\"Command too large\"}");return;}
        server.send(200,"application/json",submit(body.c_str()));
    });
    server.onNotFound([&]{server.send(404,"text/plain","Not found");});
    server.begin();
    for(;;){server.handleClient();vTaskDelay(pdMS_TO_TICKS(5));}
}
}

void panelBegin(PanelAction action){
    ownerAction=action;snprintf(bootId,sizeof(bootId),"%08lx",static_cast<unsigned long>(esp_random()));
    snprintf(ssid,sizeof(ssid),"R1-S3-%04X",unsigned(ESP.getEfuseMac()>>32)&0xFFFF);
    // Only at boot, before the UI task. Credentials never enter EEPROM profiles/log files.
    Preferences prefs;const bool opened=prefs.begin("r1-panel",false);
    String saved=opened?prefs.getString("ap-pass",""):"";
    if(saved.length()!=16){char generated[17];snprintf(generated,sizeof(generated),"%08lx%08lx",static_cast<unsigned long>(esp_random()),static_cast<unsigned long>(esp_random()));saved=generated;if(opened)prefs.putString("ap-pass",saved);}
    saved.toCharArray(password,sizeof(password));if(opened)prefs.end();
    commands=xQueueCreate(1,sizeof(Command));replies=xQueueCreate(1,sizeof(Reply));
    commandGate=xSemaphoreCreateMutex();
    if(commands&&replies&&commandGate){
        xTaskCreatePinnedToCore(webTask,"test-web",24576,nullptr,1,nullptr,0);
        xTaskCreatePinnedToCore(serialTask,"panel-uart",24576,nullptr,1,nullptr,0);
    }
    Serial.printf("PANEL AP: %s password=%s URL=http://192.168.4.1/; USB PANEL protocol ready.\n",ssid,password);
}
void panelPoll(){
    Command command{};if(!commands||xQueueReceive(commands,&command,0)!=pdTRUE)return;
    const bool recording=recorder::busy();
    setSettingsRecording(recording);
    if(!recording)acquisitionPause();
    String response;
    if(int32_t(millis()-command.expires)>0)response=result(false,"Expired command; no action taken");
    else if(recording){
        char boot[9]={},verb[16]={};unsigned revision=0;int consumed=0;
        const bool stop=!command.legacy&&sscanf(command.text,"%8s %u %15s%n",boot,&revision,verb,&consumed)==3&&!strcmp(verb,"STOP")&&command.text[consumed]==0;
        response=stop?execute(command.text):result(false,"STOP required before settings, time or diagnostic commands");
    }
    else if(command.legacy){handleLegacyLine(command.text);response=result(true,"Legacy command completed");}
    else response=execute(command.text);
    if(!recording)acquisitionResume();
    Reply reply{};reply.id=command.id;response.toCharArray(reply.json,sizeof(reply.json));xQueueOverwrite(replies,&reply);
}
void panelPublish(const PanelHardware& h){
    const auto& r=latestIna228Reading();const auto payload=settings::encode(appliedSettings());
    String hex;hex.reserve(payload.size()*2);const char* digits="0123456789abcdef";for(auto b:payload){hex+=digits[b>>4];hex+=digits[b&15];}
    String s;s.reserve(4800);
    s="{\"ready\":true,\"firmware\":\"" R1_FIRMWARE_VERSION "\",\"boot\":"+quoted(bootId)+",\"revision\":"+String(settingsRevision());
    char generation[24];snprintf(generation,sizeof(generation),"%llu",settingsGeneration());
    s+=",\"generation\":"+quoted(generation)+",\"settings_status\":"+quoted(settingsStatus());
    s+=",\"config_hex\":\""+hex+"\",\"uptime_ms\":"+String(millis())+",\"owner_core\":"+String(xPortGetCoreID())+",\"ui_core\":0";
    s+=",\"sample_id\":"+String(r.sampleId)+",\"sample_at_ms\":"+String(r.sampledAt)+",\"valid\":"+(r.valid?"true":"false");
    s+=",\"volts\":"+(r.valid?String(r.busVolts,6):String("null"))+",\"amps\":"+(r.valid?String(r.currentAmps,6):String("null"));
    s+=",\"watts\":"+(r.valid?String(r.busVolts*r.currentAmps,6):String("null"))+",\"temp_c\":"+(r.valid?String(r.temperatureC,3):String("null"));
    s+=",\"shunt_uv\":"+(r.valid?String(r.shuntMicrovolts,5):String("null"))+",\"shunt_raw\":"+String(r.shuntRaw)+",\"bus_raw\":"+String(r.busRaw)+",\"temp_raw\":"+String(r.tempRaw);
    s+=",\"sd\":"+quoted(h.sd)+",\"eeprom\":"+quoted(h.eeprom)+",\"rtc\":"+quoted(h.rtc)+",\"ina\":"+quoted(h.ina)+",\"oled\":"+(h.oled?"true":"false");
    char utc[24];snprintf(utc,sizeof(utc),"%llu",rtcUtcNow());
    s+=",\"i2c_count\":"+String(h.i2cCount)+",\"i2c_errors\":"+String(h.i2cErrors)+",\"utc\":"+String(utc);
    s+=",\"psram_free\":"+String(ESP.getFreePsram())+",\"heap_free\":"+String(ESP.getFreeHeap())+",\"queue_bytes\":"+String(recording::allocatedQueueBytes());
    s+=",\"buffer_ready\":"+(recording::memoryReady()?String("true"):String("false"))+",\"sd_block_bytes\":"+String(recording::SD_BLOCK_BYTES)+",\"recording_available\":true,\"live_available\":true";
    const auto rec=recorder::status();
    s+=",\"recording_state\":"+quoted(recorder::stateName())+",\"recording_path\":"+quoted(rec.path)+",\"recording_error\":"+quoted(rec.error);
    char counters[600];snprintf(counters,sizeof(counters),",\"recording_rows\":%llu,\"recording_bytes\":%llu,\"recording_seconds\":%.3f,\"recording_wh\":%.12g,\"recording_ah\":%.12g,\"recording_queued\":%lu,\"recording_high_water\":%lu,\"recording_overflows\":%lu,\"recording_write_us\":%lu,\"recording_sync_us\":%lu,\"recording_part\":%lu",(unsigned long long)rec.rows,(unsigned long long)rec.bytes,rec.elapsedUs/1000000.0,rec.wh,rec.ah,(unsigned long)rec.queued,(unsigned long)rec.highWater,(unsigned long)rec.overflows,(unsigned long)rec.maxWriteUs,(unsigned long)rec.maxSyncUs,(unsigned long)rec.part);s+=counters;

    const auto& a=acquisitionStats();
    s+=",\"requested_hz\":"+String(a.requestedHz)+",\"measured_hz\":"+String(a.measuredHz,3);
    s+=",\"valid_samples\":"+String(a.valid)+",\"invalid_samples\":"+String(a.invalid)+",\"missed_samples\":"+String(a.missed);
    s+=",\"max_late_us\":"+String(a.maxLateUs)+",\"max_read_us\":"+String(a.maxReadUs);
    s+=",\"maintenance_count\":"+String(a.maintenance)+",\"maintenance_ms\":"+String(a.maintenanceMs);
    s+=",\"preview_drops\":"+String(liveHistoryDrops())+",\"oled_frames\":"+String(h.oledFrames)+",\"oled_chunk_us\":"+String(h.oledChunkUs);
    s+=",\"files_available\":"+String(recorder::busy()?"false":"true")+",\"file_transfer\":"+String(sd_files::active()?"true":"false");
    s+=",\"ap_ready\":"+(networkReady.load()?String("true"):String("false"))+",\"ssid\":"+quoted(ssid)+",\"ap_password\":"+quoted(password)+"}";
    if(s.length()>=STATE_BYTES)return;
    portENTER_CRITICAL(&snapshotLock);memcpy(cached,s.c_str(),s.length()+1);portEXIT_CRITICAL(&snapshotLock);
}
bool panelHandleSerial(const char* line){
    if(strncmp(line,"PANEL ",6))return false;
    unsigned id=0;int n=0;
    if(sscanf(line,"PANEL %u %n",&id,&n)!=1||n==0)return true;
    String response;
    if(!strcmp(line+n,"STATE"))response=snapshot();
    else if(!strncmp(line+n,"DO ",3))response=submit(line+n+3);
    else if(!strncmp(line+n,"LIVE ",5))response=live(line+n+5);
    else if(!strncmp(line+n,"FILES ",6))response=sd_files::protocol(line+n+6);
    else response="{\"ok\":false,\"message\":\"Unknown panel request\"}";
    Serial.printf("PANEL %u %s\n",id,response.c_str());return true;
}
