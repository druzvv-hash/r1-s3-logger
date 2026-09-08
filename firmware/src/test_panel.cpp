#include "test_panel.h"
#include "settings.h"
#include "ina228_test.h"
#include "rtc_test.h"
#include "recording_memory.h"
#include "panel_assets.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_system.h>
#include <atomic>
#include <cstring>

namespace {
constexpr size_t STATE_BYTES=6000, COMMAND_BYTES=3100;
char cached[STATE_BYTES]="{\"ready\":false}";
portMUX_TYPE snapshotLock=portMUX_INITIALIZER_UNLOCKED;
char bootId[9], ssid[24], password[17];
std::atomic<bool> networkReady{false};
PanelAction ownerAction=nullptr;
struct Command { uint32_t id, expires; char text[COMMAND_BYTES]; };
struct Reply { uint32_t id; char json[256]; };
QueueHandle_t commands=nullptr, replies=nullptr;

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
void webTask(void*){
    WiFi.mode(WIFI_AP);
    networkReady.store(WiFi.softAP(ssid,password,1,0,2));
    WebServer server(80);
    const char* headers[]={"X-R1-Panel","Origin"};server.collectHeaders(headers,2);
    server.on("/",HTTP_GET,[&]{server.sendHeader("Cache-Control","no-store");server.sendHeader("Content-Encoding","gzip");server.send_P(200,"text/html; charset=utf-8",reinterpret_cast<const char*>(PANEL_HTML),sizeof(PANEL_HTML));});
    server.on("/api/state",HTTP_GET,[&]{server.sendHeader("Cache-Control","no-store");server.send(200,"application/json",snapshot());});
    server.on("/api/command",HTTP_POST,[&]{
        if(server.header("X-R1-Panel")!="1" || (server.hasHeader("Origin")&&server.header("Origin")!=String("http://")+server.hostHeader())){server.send(403,"application/json","{\"ok\":false,\"message\":\"Origin/header rejected\"}");return;}
        const String body=server.arg("plain");
        if(body.length()==0||body.length()>=COMMAND_BYTES){server.send(413,"application/json","{\"ok\":false,\"message\":\"Command too large\"}");return;}
        static uint32_t id=0;Command command{};command.id=++id;command.expires=millis()+7000;body.toCharArray(command.text,sizeof(command.text));
        if(xQueueSend(commands,&command,0)!=pdTRUE){server.send(409,"application/json","{\"ok\":false,\"message\":\"Device busy\"}");return;}
        Reply reply{};const uint32_t began=millis();bool received=false;
        while(millis()-began<8000){if(xQueueReceive(replies,&reply,pdMS_TO_TICKS(100))==pdTRUE&&reply.id==id){received=true;break;}}
        server.send(received?200:504,"application/json",received?reply.json:"{\"ok\":false,\"message\":\"Timeout; refresh device state, do not repeat blindly\"}");
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
    if(commands&&replies)xTaskCreatePinnedToCore(webTask,"test-web",24576,nullptr,1,nullptr,0);
    Serial.printf("PANEL AP: %s password=%s URL=http://192.168.4.1/; USB PANEL protocol ready.\n",ssid,password);
}
void panelPoll(){
    Command command{};if(!commands||xQueueReceive(commands,&command,0)!=pdTRUE)return;
    const String response=int32_t(millis()-command.expires)>0?result(false,"Expired command; no action taken"):execute(command.text);
    Reply reply{};reply.id=command.id;response.toCharArray(reply.json,sizeof(reply.json));xQueueOverwrite(replies,&reply);
}
void panelPublish(const PanelHardware& h){
    const auto& r=latestIna228Reading();const auto payload=settings::encode(appliedSettings());
    String hex;hex.reserve(payload.size()*2);const char* digits="0123456789abcdef";for(auto b:payload){hex+=digits[b>>4];hex+=digits[b&15];}
    String s;s.reserve(4800);
    s="{\"ready\":true,\"firmware\":\"0.14\",\"boot\":"+quoted(bootId)+",\"revision\":"+String(settingsRevision());
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
    s+=",\"buffer_ready\":"+(recording::memoryReady()?String("true"):String("false"))+",\"sd_block_bytes\":"+String(recording::SD_BLOCK_BYTES)+",\"recording_available\":false,\"diagnostic_interval_ms\":1000";
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
    else if(!strncmp(line+n,"DO ",3))response=execute(line+n+3);
    else response=result(false,"Unknown panel request");
    Serial.printf("PANEL %u %s\n",id,response.c_str());return true;
}
