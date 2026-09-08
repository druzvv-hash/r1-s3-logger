#include "rate_benchmark.h"
#if R1_BENCHMARK
#include "settings.h"
#include "ina228_test.h"
#include "recorder.h"
#include "sd_files.h"
#include <Wire.h>
#include <esp_timer.h>
#include <algorithm>
namespace {
settings::Config original;
uint32_t originalBus=100000;
uint64_t deadline=0;
bool active=false,observedRunning=false;
}
bool rateBenchmarkActive(){return active;}
bool rateBenchmarkStart(const char* argument,const char*& message,PanelAction action){
    unsigned hz=0,ct=0,avg=0,bus=0,seconds=0;int consumed=0;
    if(active||recorder::busy()||sd_files::active()){message="Finish the active recording/transfer first";return false;}
    if(sscanf(argument,"%u %u %u %u %u%n",&hz,&ct,&avg,&bus,&seconds,&consumed)!=5||argument[consumed]||hz<10||hz>1000||ct>7||avg>7||(bus!=100000&&bus!=400000)||seconds<5||seconds>600){message="BENCH expects Hz CT AVG I2C_Hz seconds (5..600)";return false;}
    original=appliedSettings();originalBus=Wire.getClock();auto candidate=original;
    candidate.requested_rate_hz=hz;candidate.vshunt_ct_code=ct;candidate.vbus_ct_code=ct;candidate.temp_ct_code=ct;candidate.average_code=avg;
    candidate.max_gap_us=std::max(candidate.max_gap_us,uint32_t(2000000/hz));
    candidate.ready_timeout_us=std::max(candidate.ready_timeout_us,settings::conversionUs(candidate)+1000);
    if(!settings::timingFeasible(candidate)){message="ADC conversion exceeds the requested period";return false;}
    if(!Wire.setClock(bus)||!panelApplySettings(settings::encode(candidate),message)){Wire.setClock(originalBus);return false;}
    if(!action("START","",message)){
        const char* restored="";Wire.setClock(originalBus);panelApplySettings(settings::encode(original),restored);return false;
    }
    deadline=esp_timer_get_time()+uint64_t(seconds)*1000000;observedRunning=false;active=true;
    Serial.printf("BENCH armed hz=%u ct=%u avg=%u bus=%u duration=%u; automatic STOP/restore\n",hz,ct,avg,bus,seconds);
    message="Timed benchmark started; automatic STOP and volatile configuration restore";return true;
}
void rateBenchmarkStep(){
    if(!active||!acquisitionIdle())return;
    const auto phase=recorder::state();if(phase==recorder::State::Running)observedRunning=true;
    if(esp_timer_get_time()>=deadline&&phase==recorder::State::Running){const char* message="";recorder::stop(message);return;}
    if(recorder::busy()||(!observedRunning&&phase!=recorder::State::Error))return;
    acquisitionPause();setSettingsRecording(false);Wire.setClock(originalBus);
    const char* message="";const bool restored=panelApplySettings(settings::encode(original),message);
    acquisitionResume();active=false;
    Serial.printf("BENCH ended restored=%u %s\n",restored,message);
}
#endif
