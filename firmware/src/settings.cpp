#include "settings.h"
#include "ina228_test.h"
#include <Arduino.h>
#include <Wire.h>
#include <mbedtls/sha256.h>
#include <algorithm>
#include <cstring>
namespace {
class Eeprom : public settings::Storage {
public:
 bool read(uint16_t addr,uint8_t* p,size_t n) override {
    if(size_t(addr)+n>4096)return false;
    while(n){size_t count=std::min(n,size_t(32));Wire.beginTransmission(0x50);Wire.write(uint8_t(addr>>8));Wire.write(uint8_t(addr));
      if(Wire.endTransmission(false)!=0||Wire.requestFrom(uint8_t(0x50),count)!=count){while(Wire.available())Wire.read();return false;}
      for(size_t i=0;i<count;++i)*p++=Wire.read();addr+=count;n-=count;
    }return true;
 }
 bool write(uint16_t addr,const uint8_t* p,size_t n) override {
    if(!n||n>32||addr%32+n>32||size_t(addr)+n>3072)return false;
    Wire.beginTransmission(0x50);Wire.write(uint8_t(addr>>8));Wire.write(uint8_t(addr));
    if(Wire.write(p,n)!=n||Wire.endTransmission()!=0)return false;
    const uint32_t began=millis();while(millis()-began<20){Wire.beginTransmission(0x50);if(Wire.endTransmission()==0)return true;delay(1);}return false;
 }
} eeprom;
settings::Config applied,draft;
settings::Selection persisted;
bool ready=false,recording=false,receiving=false,saveUncertain=false;
size_t expected=0;
settings::Bytes incoming;
uint32_t revision=1;
void fail(const char* why){Serial.printf("CONFIG ERROR %s\n",why);}
void state(){Serial.printf("CONFIG STATUS %s generation=%llu draft_changed=%u recording=%u\n",settingsStatus(),persisted.selected.generation,!settings::equal(applied,draft),recording);}
int hex(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
void output(const settings::Config& c){
 const auto b=settings::encode(c);uint8_t hash[32];mbedtls_sha256_ret(b.data(),b.size(),hash,0);
 Serial.printf("CONFIG BEGIN %u ",unsigned(b.size()));for(auto x:hash)Serial.printf("%02x",x);Serial.println();
 for(size_t p=0;p<b.size();p+=32){Serial.printf("CONFIG HEX %04X ",unsigned(p));for(size_t j=p;j<std::min(p+32,b.size());++j)Serial.printf("%02X",b[j]);Serial.println();}
 Serial.println("CONFIG END");state();
}
}
const settings::Config& appliedSettings(){return applied;}
bool settingsReady(){return ready&&!persisted.blocked&&inaSettingsHealthy();}
const char* settingsStatus(){if(persisted.blocked)return "BLOCKED";if(!ready||!inaSettingsHealthy())return "APPLY FAIL";if(saveUncertain||persisted.index<0||!settings::equal(applied,persisted.selected.config))return "UNSAVED";return "SAVED";}
void setSettingsRecording(bool value){recording=value;}
// Budget for 100 kHz I2C trigger/readback and scheduler overhead, beyond ADC time.
bool runtimeTimingFeasible(const settings::Config& c){
 return settings::timingFeasible(c) && settings::conversionUs(c)+4000<=1000000/c.requested_rate_hz;
}
void initSettings(){
 persisted=settings::scan(eeprom);draft=persisted.index>=0?persisted.selected.config:settings::Config{};
 ready=runtimeTimingFeasible(draft)&&applyInaSettings(draft);if(ready)applied=draft;
 Serial.println("CONFIG: boot read only; defaults/invalid slots never saved automatically.");state();
}
bool handleSettingsCommand(const char* line){
 if(strncmp(line,"CONFIG ",7))return false;
 if(!strcmp(line,"CONFIG STATUS")){state();return true;}
 if(!strcmp(line,"CONFIG GET")){output(applied);return true;}
 if(!strcmp(line,"CONFIG DRAFT")){output(draft);return true;}
 if(!strcmp(line,"CONFIG PERSISTED")){if(persisted.index<0)fail("no saved config");else output(persisted.selected.config);return true;}
 if(recording){fail("STOP required");return true;}
 ++revision; // Invalidate stale panel drafts, including an in-progress UART transfer.
 if(!strcmp(line,"CONFIG DEFAULTS")){draft=settings::Config{};receiving=false;Serial.println("CONFIG OK DEFAULTS draft only");return true;}
 unsigned n=0;int consumed=0;
 if(sscanf(line,"CONFIG BEGIN %u%n",&n,&consumed)==1&&line[consumed]==0){
    receiving=false;incoming.clear();if(!n||n>1472){fail("invalid payload size");return true;}expected=n;receiving=true;Serial.println("CONFIG OK BEGIN");return true;
 }
 if(!strncmp(line,"CONFIG HEX ",11)){
    unsigned pos=0;char data[65]={};consumed=0;
    if(!receiving||sscanf(line,"CONFIG HEX %x %64s%n",&pos,data,&consumed)!=2||line[consumed]!=0||pos!=incoming.size()||strlen(data)%2||incoming.size()+strlen(data)/2>expected){receiving=false;fail("chunk order/size");return true;}
    for(size_t i=0;i<strlen(data);i+=2){const int a=hex(data[i]),b=hex(data[i+1]);if(a<0||b<0){receiving=false;fail("hex");return true;}incoming.push_back(a*16+b);}Serial.println("CONFIG OK HEX");return true;
 }
 unsigned checksum=0;consumed=0;
 if(sscanf(line,"CONFIG END %x%n",&checksum,&consumed)==1&&line[consumed]==0){
    bool valid=receiving&&incoming.size()==expected&&settings::crc32(incoming.data(),incoming.size())==checksum;receiving=false;settings::Config candidate;
    if(!valid||!settings::decode(incoming,candidate)){fail("CRC/schema/bounds");return true;}draft=candidate;Serial.println("CONFIG OK DRAFT");return true;
 }
 if(receiving && (!strcmp(line,"CONFIG APPLY") || !strcmp(line,"CONFIG SAVE"))){fail("finish draft transfer first");return true;}
 if(!strcmp(line,"CONFIG APPLY")){
    if(!runtimeTimingFeasible(draft)){fail("conversion duration exceeds requested period/timeout");return true;}
    if(!applyInaSettings(draft)){fail("hardware apply/readback; previous settings retained or INA latched off");return true;}
    applied=draft;ready=true;Serial.println("CONFIG OK APPLY");state();return true;
 }
 if(!strcmp(line,"CONFIG SAVE")){
    if(!ready||!settings::equal(applied,draft)){fail("apply valid draft first");return true;}
    if(!settings::save(eeprom,applied,persisted)){saveUncertain=true;fail("SAVE failed/blocked; persistence uncertain until reread, previous good slot untouched");return true;}
    saveUncertain=false;Serial.println("CONFIG OK SAVE");state();return true;
 }
 fail("unknown command");return true;
}

uint32_t settingsRevision(){return revision;}
uint64_t settingsGeneration(){return persisted.index>=0?persisted.selected.generation:0;}
bool panelApplySettings(const settings::Bytes& payload,const char*& error){
 if(recording||receiving){error="STOP required or UART draft transfer active";return false;}
 if(persisted.blocked){error="Unsupported/ambiguous EEPROM configuration";return false;}
 settings::Config candidate;
 if(!settings::decode(payload,candidate)||!runtimeTimingFeasible(candidate)){error="Invalid configuration or ADC timing";return false;}
 ++revision;
 if(!applyInaSettings(candidate)){error="INA apply/readback failed; inspect device state";return false;}
 applied=candidate;draft=candidate;ready=true;return true;
}
bool panelSaveSettings(const char*& error){
 if(recording||receiving||!settingsReady()||!settings::equal(applied,draft)){error="Apply valid settings first; finish UART transfer";return false;}
 ++revision;
 if(!settings::save(eeprom,applied,persisted)){saveUncertain=true;error="EEPROM save/readback failed; persistence uncertain";return false;}
 saveUncertain=false;return true;
}
