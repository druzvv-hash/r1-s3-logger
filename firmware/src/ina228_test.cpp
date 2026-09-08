#include <Arduino.h>
#include <Wire.h>
#include "pins.h"
#include "ina228_test.h"
#include "settings.h"
#include "sample_clock.h"
#include "live_history.h"
#include "recorder.h"
#include <esp_timer.h>

namespace {
Ina228Reading latest;
bool restoreFailed = false;
constexpr uint8_t address = 0x40;
constexpr int32_t signed20(uint32_t word) {
    return (word >> 4) & 0x80000 ? int32_t(word >> 4) - 0x100000 : int32_t(word >> 4);
}
constexpr int32_t signed16(uint32_t word) {
    return word & 0x8000 ? int32_t(word) - 0x10000 : int32_t(word);
}
static_assert(signed20(0xFFFFF0) == -1, "negative shunt LSB");
static_assert(signed20(0x800000) == -524288, "negative shunt limit");
static_assert(signed20(0x7FFFF0) == 524287, "positive shunt limit");
static_assert(signed20(0) == 0 && signed20(0x10) == 1, "zero and positive LSB");
static_assert(signed16(0xFF80) == -128, "negative temperature");

bool readRegister(uint8_t reg, uint8_t length, uint32_t& value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(address, length) != length) {
        while (Wire.available()) Wire.read();
        return false;
    }
    value = 0;
    for (uint8_t i = 0; i < length; ++i) value = (value << 8) | uint8_t(Wire.read());
    return true;
}
bool writeRegister(uint8_t reg, uint16_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(uint8_t(value >> 8));
    Wire.write(uint8_t(value));
    return Wire.endTransmission() == 0;
}
}

const char* testIna228() {
    ++latest.sampleId;
    latest.sampledAt = millis();
    latest.valid = false;
    const auto& active = appliedSettings();
    if (restoreFailed) return "RESTORE FAIL";
    if (!settingsReady()) return "CONFIG FAIL";
    uint32_t manufacturer, device, config, adc;
    Serial.println("\nINA228: identity and fresh triggered ADC test at 0x40");
    if (!readRegister(0x3E, 2, manufacturer) || !readRegister(0x3F, 2, device) ||
        !readRegister(0x00, 2, config) || !readRegister(0x01, 2, adc)) {
        Serial.println("INA228 FAIL: register read failed.");
        return "I2C FAIL";
    }
    Serial.printf("INA228 manufacturer=0x%04lX device=0x%04lX CONFIG=0x%04lX ADC=0x%04lX\n",
                  (unsigned long)manufacturer, (unsigned long)device,
                  (unsigned long)config, (unsigned long)adc);
    if (manufacturer != 0x5449 || (device >> 4) != 0x228) {
        Serial.println("INA228 FAIL: unexpected identity; no registers changed.");
        return "ID FAIL";
    }
    // Use applied conversion times/averaging. Writing clears stale CNVRF.
    // CONFIG (including conversion delay/range) and calibration remain unchanged.
    const char* result = "I2C FAIL";
    uint32_t diag = 0, shunt = 0, bus = 0, temperature = 0;
    if (writeRegister(0x01, 0x7000 | settings::adcBits(active))) {
        const uint32_t start = micros();
        result = "TIMEOUT";
        while (micros() - start < active.ready_timeout_us) {
            // Reading DIAG_ALRT clears conversion-ready / latched diagnostic flags.
            if (!readRegister(0x0B, 2, diag)) { result = "I2C FAIL"; break; }
            if (diag & 0x02) {
                result = readRegister(0x04, 3, shunt) && readRegister(0x05, 3, bus) &&
                         readRegister(0x06, 2, temperature) ? "ADC OK" : "I2C FAIL";
                break;
            }
            delay(2);
        }
    }
    uint32_t restored = 0;
    if (!writeRegister(0x01, uint16_t(adc)) || !readRegister(0x01, 2, restored) || restored != adc) {
        restoreFailed = true;
        Serial.println("INA228 RESTORE FAIL: further INA tests disabled until reboot.");
        return "RESTORE FAIL";
    }
    if (strcmp(result, "ADC OK") == 0) {
        pinMode(pins::INA228_ALERT, INPUT);
        Serial.printf("INA228 raw VSHUNT=0x%06lX VBUS=0x%06lX TEMP=0x%04lX DIAG=0x%04lX\n",
                      (unsigned long)shunt, (unsigned long)bus,
                      (unsigned long)temperature, (unsigned long)diag);
        const bool narrow = config & 0x10;
        const double shuntMicrovolts = signed20(shunt) * (narrow ? 0.078125 : 0.3125);
        Serial.printf("INA228 VBUS=%.6f V; VSHUNT=%.4f uV; die=%.3f C; range=+/-%s mV\n",
                      (bus >> 4) * 0.0001953125,
                      shuntMicrovolts,
                      signed16(temperature) * 0.0078125, narrow ? "40.96" : "163.84");
        Serial.printf("INA228 ALERT GPIO14=%d (passive level only); ADC_CONFIG restored.\n",
                      digitalRead(pins::INA228_ALERT));
        if ((bus & 0x80000F) || (shunt & 0x0F)) {
            result = "DATA FAIL";
        } else if (signed20(shunt) == -524288 || signed20(shunt) == 524287) {
            result = "SHUNT LIMIT";
            Serial.println("INA228: shunt ADC at rail; current withheld.");
        } else {
            latest.busVolts = ((bus >> 4) * 0.0001953125 - active.u_zero_V) * active.u_gain;
            latest.currentAmps = active.polarity * (shuntMicrovolts-active.i_zero_uV) / active.shunt_uohm * active.i_gain;
            latest.temperatureC = signed16(temperature) * 0.0078125;
            latest.shuntRaw = signed20(shunt);
            latest.busRaw = bus >> 4;
            latest.tempRaw = signed16(temperature);
            latest.shuntMicrovolts = shuntMicrovolts;
            latest.sampledAt = millis();
            latest.valid = true;
            Serial.printf("INA228 I_applied=%+.4f A U_applied=%.6f V; shunt=%.3f uOhm calibrated=%u\n",
                          latest.currentAmps, latest.busVolts, active.shunt_uohm, active.calibration_valid);
        }
        if (narrow) Serial.println("INA228: narrow range cannot cover this shunt's full 400 A rating.");
        Serial.println("Applied coefficients only; this sample does not validate calibration or active ALERT.");
    }
    Serial.printf("INA228 result: %s\n", result);
    return result;
}

const Ina228Reading& latestIna228Reading() { return latest; }


bool applyInaSettings(const settings::Config& c) {
    class InaRegisters : public settings::Registers {
        bool read(uint8_t reg,uint32_t& value) override { return readRegister(reg,2,value); }
        bool write(uint8_t reg,uint16_t value) override { return writeRegister(reg,value); }
    } io;
    const bool ok=settings::applyRegisters(io,c,restoreFailed);
    if (ok || restoreFailed) latest.valid=false;
    return ok;
}

bool inaSettingsHealthy() { return !restoreFailed; }
bool captureInaIdentity(uint16_t& manufacturer,uint16_t& device,uint16_t& adc){
    uint32_t m=0,d=0,a=0,c=0;
    if(!readRegister(0x3e,2,m)||!readRegister(0x3f,2,d)||!readRegister(1,2,a)||!readRegister(0,2,c))return false;
    manufacturer=m;device=d;adc=a;
    return m==0x5449&&(d>>4)==0x228&&(a&0x0fff)==settings::adcBits(appliedSettings())&&bool(c&0x10)==bool(appliedSettings().adc_range);
}

namespace {
SampleClock sampleClock;
AcquisitionStats stats;
bool started=false,pending=false,gapNext=false,paused=false;
uint64_t began=0,pollAt=0,sequence=0,windowAt=0,pauseAt=0;
uint32_t windowSamples=0;
const char* sampleStatus="WAIT";
uint8_t sampleQuality=0;
void completed(const char* status,bool valid,uint8_t quality=0,uint64_t observedUs=0){
    const uint64_t now=observedUs?observedUs:esp_timer_get_time();
    latest.valid=valid;latest.sampledAt=now/1000;latest.sampleId=++sequence;
    pending=false;sampleStatus=status;
    if(valid)++stats.valid;else ++stats.invalid;
    ++windowSamples;
    if(now-windowAt>=2000000){stats.measuredHz=windowSamples*1000000.0/(now-windowAt);windowAt=now;windowSamples=0;}
    liveHistoryPush({sequence,now,valid?latest.busVolts:0,valid?latest.currentAmps:0,settingsRevision(),uint8_t(quality|sampleQuality|(valid?0:1))});
    recording::Sample s{};s.seq=sequence;s.t_us=now;s.config_revision=settingsRevision();
    s.quality=quality|sampleQuality|(valid?0:1);s.raw_present=valid?7:0;
    if(valid){s.vshunt_raw=latest.shuntRaw;s.vbus_raw=latest.busRaw;s.temp_raw=latest.tempRaw;}
    recorder::push(s);
}
}
void acquisitionBegin(){
    stats={};stats.requestedHz=appliedSettings().requested_rate_hz;
    const uint64_t now=esp_timer_get_time();sampleClock.reset(now,stats.requestedHz);
    windowAt=now;windowSamples=0;started=true;paused=false;pending=false;
}
bool acquisitionIdle(){return !pending;}
uint32_t acquisitionSlackUs(){return pending?0:sampleClock.slack(esp_timer_get_time());}
const AcquisitionStats& acquisitionStats(){return stats;}
const char* acquisitionStatus(){return sampleStatus;}
void acquisitionPause(){
    if(!started||paused)return;
    paused=true;pauseAt=esp_timer_get_time();++stats.maintenance;
}
void acquisitionResume(){
    if(!started||!paused)return;
    const uint64_t now=esp_timer_get_time();stats.maintenanceMs+=(now-pauseAt)/1000;
    stats.requestedHz=appliedSettings().requested_rate_hz;sampleClock.reset(now,stats.requestedHz);
    // Exclude explicit maintenance from the cadence window; record it separately.
    windowAt=now;windowSamples=0;stats.measuredHz=0;gapNext=true;pending=false;paused=false;
}
void acquisitionStep(){
    if(!started||paused)return;
    const auto& c=appliedSettings();uint64_t now=esp_timer_get_time();
    if(!pending){
        if(!sampleClock.due(now))return;
        uint32_t late=0,skipped=sampleClock.take(now,late);
        stats.missed+=skipped;sequence+=skipped;if(late>stats.maxLateUs)stats.maxLateUs=late;
        sampleQuality=(gapNext||skipped)?2:0;gapNext=false;
        if(!settingsReady()){completed("CONFIG FAIL",false);return;}
        if(!writeRegister(1,0x7000|settings::adcBits(c))){completed("TRIGGER FAIL",false);return;}
        began=esp_timer_get_time();pollAt=began+settings::conversionUs(c);pending=true;return;
    }
    if(now<pollAt)return;
    uint32_t diag=0;
    if(!readRegister(0x0B,2,diag)){completed("I2C FAIL",false);return;}
    if(!(diag&2)){
        if(uint64_t(esp_timer_get_time())-began>=c.ready_timeout_us){completed("TIMEOUT",false);return;}
        pollAt=esp_timer_get_time()+300;return;
    }
    uint32_t shunt=0,bus=0,temp=0;const uint64_t readAt=esp_timer_get_time();
    if(!readRegister(4,3,shunt)||!readRegister(5,3,bus)||!readRegister(6,2,temp)){completed("I2C FAIL",false);return;}
    const uint32_t elapsed=esp_timer_get_time()-readAt;if(elapsed>stats.maxReadUs)stats.maxReadUs=elapsed;
    if((shunt&15)||(bus&0x80000F)){completed("DATA FAIL",false);return;}
    const int32_t raw=signed20(shunt);
    if(raw==-524288||raw==524287){completed("SHUNT LIMIT",false,4);return;}
    latest.shuntRaw=raw;latest.busRaw=bus>>4;latest.tempRaw=signed16(temp);
    latest.shuntMicrovolts=raw*(c.adc_range?0.078125:0.3125);
    latest.busVolts=(latest.busRaw*0.0001953125-c.u_zero_V)*c.u_gain;
    latest.currentAmps=c.polarity*(latest.shuntMicrovolts-c.i_zero_uV)/c.shunt_uohm*c.i_gain;
    latest.temperatureC=latest.tempRaw*0.0078125;
    completed("ADC OK",true,0,readAt);
}
