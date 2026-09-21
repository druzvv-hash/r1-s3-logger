#include "wifi_station.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <cstring>
#include "recorder.h"
#include "sd_files.h"

namespace {
struct WifiSeed {const char* ssid;const char* password;};
#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#else
static const WifiSeed WIFI_SEEDS[]={{"",""}};
#endif
struct Profile {char ssid[33]={};char password[64]={};};
Profile profiles[3];unsigned count=0,profileIndex=0;
QueueHandle_t changes=nullptr;
uint32_t attempted=0,published=0;bool wasConnected=false,mdns=false;
char hostname[32];
struct Status {bool connected=false;char ssid[33]={},ip[16]={},host[32]={},error[80]={};int rssi=0;unsigned profiles=0;} status;
portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
String quote(const char* text){String s="\"";for(const uint8_t* p=(const uint8_t*)text;*p;++p){if(*p=='"'||*p=='\\')s+='\\';if(*p<32){char b[7];snprintf(b,sizeof(b),"\\u%04x",*p);s+=b;}else s+=char(*p);}return s+'"';}
bool storeProfile(Preferences& p,unsigned i,const Profile& v){
 char key[12];snprintf(key,sizeof(key),"profile%u",i);
 return p.putBytes(key,&v,sizeof(v))==sizeof(v);
}
void connect(){if(!count)return;attempted=millis();WiFi.begin(profiles[profileIndex].ssid,profiles[profileIndex].password);}
bool decode(const char* text,size_t n,char* out,size_t cap){
 if(!n||n%2||n/2>=cap)return false;
 auto hex=[](char c){return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;};
 for(size_t i=0;i<n;i+=2){int a=hex(text[i]),b=hex(text[i+1]);if(a<0||b<0||!(a||b))return false;out[i/2]=char(a*16+b);}out[n/2]=0;return true;
}
}
void wifiStationBegin(){
 snprintf(hostname,sizeof(hostname),"r1-s3-%04x",unsigned(ESP.getEfuseMac()>>32)&0xffff);
 WiFi.setHostname(hostname);WiFi.persistent(false);WiFi.setAutoReconnect(false);
 changes=xQueueCreate(1,sizeof(Profile));
 Preferences p;
 if(p.begin("r1-wifi",false)){
  count=std::min(unsigned(p.getUChar("count",0)),3u);
  unsigned valid=0;
  for(unsigned i=0;i<count;++i){char key[12];snprintf(key,sizeof(key),"profile%u",i);Profile v;
   if(p.getBytesLength(key)==sizeof(v)&&p.getBytes(key,&v,sizeof(v))==sizeof(v)&&
      memchr(v.ssid,0,sizeof(v.ssid))&&memchr(v.password,0,sizeof(v.password))&&*v.ssid&&strlen(v.password)>=8)profiles[valid++]=v;
  }
  count=valid;
  if(!count){
   for(const auto& seed:WIFI_SEEDS){if(count==3)break;if(!*seed.ssid)continue;
    Profile v;strlcpy(v.ssid,seed.ssid,sizeof(v.ssid));strlcpy(v.password,seed.password,sizeof(v.password));
    if(storeProfile(p,count,v))profiles[count++]=v;
   }
   if(count)p.putUChar("count",count);
  }
  p.end();
 }
 connect();
}
bool wifiStationConfigure(const char* arg,const char*& message){
 const char* space=strchr(arg,' ');Profile p;
 if(!space||strchr(space+1,' ')||!decode(arg,space-arg,p.ssid,sizeof(p.ssid))||!decode(space+1,strlen(space+1),p.password,sizeof(p.password))||strlen(p.password)<8){message="SSID: 1-32 bytes; password: 8-63 bytes";return false;}
 if(!changes||xQueueSend(changes,&p,0)!=pdTRUE){message="Wi-Fi configuration busy";return false;}
 message="Wi-Fi change queued; check network status and new address";return true;
}
void wifiStationTick(){
 Profile next;
 if(changes&&xQueueReceive(changes,&next,0)==pdTRUE){
  if(recorder::busy()||sd_files::active()){
   portENTER_CRITICAL(&lock);strlcpy(status.error,"Wi-Fi change rejected: recording/download active",sizeof(status.error));portEXIT_CRITICAL(&lock);
   return;
  }
  Preferences p;bool ok=p.begin("r1-wifi",false);
  if(ok){ok=storeProfile(p,0,next);if(ok)ok=p.putUChar("count",count?count:1)>0;p.end();}
  portENTER_CRITICAL(&lock);strlcpy(status.error,ok?"":"Wi-Fi settings could not be saved",sizeof(status.error));portEXIT_CRITICAL(&lock);
  if(ok){profiles[0]=next;count=std::max(count,1u);profileIndex=0;WiFi.disconnect(false,false);connect();}
 }
 const bool connected=WiFi.status()==WL_CONNECTED;
 if(connected&&!wasConnected){if(!mdns){mdns=MDNS.begin(hostname);if(mdns)MDNS.addService("http","tcp",80);}Serial.printf("PANEL LAN: http://%s/ http://%s.local/\n",WiFi.localIP().toString().c_str(),hostname);}
 if(!connected&&wasConnected)attempted=millis()-20000;
 if(!connected&&count&&uint32_t(millis()-attempted)>=20000){profileIndex=(profileIndex+1)%count;WiFi.disconnect(false,false);connect();}
 wasConnected=connected;
 if(uint32_t(millis()-published)>=500){
  published=millis();const String ip=connected?WiFi.localIP().toString():"";Status s;
  s.connected=connected;s.rssi=connected?WiFi.RSSI():0;s.profiles=count;
  strlcpy(s.ssid,count?profiles[profileIndex].ssid:"",sizeof(s.ssid));strlcpy(s.ip,ip.c_str(),sizeof(s.ip));strlcpy(s.host,hostname,sizeof(s.host));
  portENTER_CRITICAL(&lock);memcpy(s.error,status.error,sizeof(s.error));status=s;portEXIT_CRITICAL(&lock);
 }
}
String wifiStationJson(){Status s;portENTER_CRITICAL(&lock);s=status;portEXIT_CRITICAL(&lock);
 return String("{\"connected\":")+(s.connected?"true":"false")+",\"ssid\":"+quote(s.ssid)+",\"ip\":"+quote(s.ip)+",\"hostname\":"+quote(s.host)+",\"rssi\":"+String(s.rssi)+",\"profiles\":"+String(s.profiles)+",\"error\":"+quote(s.error)+"}";
}
