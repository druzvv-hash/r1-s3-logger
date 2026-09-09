#include "ecosystem_owner.h"
#include "r3_ble_protocol.h"
#include "recorder.h"
#include "settings.h"
#include "ina228_test.h"
#include "rtc_test.h"
#include "sd_files.h"
#include "build_provenance.h"
#include "firmware_version.h"
#include <esp_timer.h>
#include <esp_system.h>
#include <cstring>

namespace {
// Owned on core 1, never accessed by a BLE callback. Reset after a manual RTC
// adjustment or boot; no unsupported persistence of old accuracy claims.
recording::SessionInfo::ClockCorrection correction;
uint64_t sessionId=0;
uint64_t sessionGroupId=0;
uint32_t lastPublication=0;

uint64_t newSessionId(){
    uint64_t value=(uint64_t(esp_random())<<32)|esp_random();
    return value?value:1;
}
void publish(bool i2cReady,bool sdReady){
    const auto phase=recorder::state();
    const auto status=recorder::status();
    R3BleOwnerSnapshot out;
    out.state=static_cast<R3BleOwnerState>(phase);
    out.sessionId=sessionId;
    out.groupId=sessionGroupId;
    out.rtcValid=rtcUtcNow()!=0;
    out.clockSynced=out.rtcValid&&correction.applied;
    out.ready=(phase==recorder::State::Ready||phase==recorder::State::Error)&&
        i2cReady&&sdReady&&settingsReady()&&settingsGeneration()!=0&&
        (out.rtcValid||appliedSettings().allow_unknown_utc)&&!sd_files::active();
    // Published status can still belong to a previous file during STARTING.
    // Match the actual storage owner's identity before exposing its outcome.
    if(sessionId&&status.controlSessionId==sessionId){
        strlcpy(out.file,status.path,sizeof(out.file));
        strlcpy(out.error,status.error,sizeof(out.error));
        const size_t n=strlen(status.path);
        out.fileClosed=phase==recorder::State::Ready&&!status.error[0]&&n>4&&
            !strcmp(status.path+n-4,".csv");
    }
    r3BlePublishOwner(out);
    lastPublication=millis();
}
}

void ecosystemForgetClockEvidence(){correction={};}

bool ecosystemStartRecording(const R3BleOwnerRequest* remote,const char*& message){
    if(recorder::busy()){message="Recording is already starting, running or stopping";return false;}
    if(!settingsReady()){message="Valid INA settings required";return false;}
    if(sd_files::active()){message="SD transfer is active";return false;}
    if(remote&&(!remote->sessionId||!remote->groupId||!r3BleOwnerActionCurrent(*remote))){
        message="Remote START expired or no longer authorized";return false;
    }
    if(remote){
        char authority[18];r3_ble::formatDevice(remote->sourceDevice,authority);
        if(!correction.applied||correction.authorityBoot!=remote->sourceBoot||
           correction.revision!=remote->clockRevision||correction.authorityId!=authority){
            message="Fresh R3 RTC correction required before remote START";return false;
        }
    }
    recording::SessionInfo info;
    info.schema=2;info.config=appliedSettings();info.generation=settingsGeneration();info.revision=settingsRevision();
    if(!captureInaIdentity(info.manufacturer,info.device,info.adc)){
        message="INA identity/config readback failed";return false;
    }
    pollRtc(false);info.utcUs=rtcUtcNow()*1000000;info.originUs=esp_timer_get_time();
    info.measuredHz=acquisitionStats().measuredHz;info.commit=R1_BUILD_COMMIT;
    info.dirty=R1_BUILD_DIRTY;info.version=R1_FIRMWARE_VERSION;
    info.id=recording::sessionId(info.utcUs,esp_random(),esp_random());
    info.controlSessionId=remote?remote->sessionId:newSessionId();
    info.bootId=r3BleBootId();
    uint8_t localId[6];char address[18];r3BleCopyDeviceId(localId);
    r3_ble::formatDevice(localId,address);info.deviceId=address;
    info.clockCorrection=correction;
    if(remote){
        info.groupId=remote->groupId;info.coordinatorBoot=remote->sourceBoot;
        r3_ble::formatDevice(remote->sourceDevice,address);info.coordinatorId=address;
        // Identity/RTC reads above may take time. Recheck just before admission.
        if(!r3BleOwnerActionCurrent(*remote)){message="Remote START expired before admission";return false;}
    }
    if(!recorder::start(info,message))return false;
    sessionId=info.controlSessionId;
    sessionGroupId=info.groupId;
    return true;
}

void ecosystemOwnerPoll(bool i2cReady,bool sdReady){
    R3BleOwnerRequest request;
    if(!r3BleTakeOwnerAction(request)){
        if(millis()-lastPublication>=200)publish(i2cReady,sdReady);
        return;
    }
    const bool wasBusy=recorder::busy();
    bool ok=false;
    const char* message="Remote action unavailable";
    if(!r3BleOwnerActionCurrent(request))message="Remote action expired or connection changed";
    else if(request.kind==R3BleOwnerRequest::Stop){
        if(!request.sessionId||request.sessionId!=sessionId)message="STOP session does not match current recording";
        else ok=recorder::stop(message);
    }else if(wasBusy)message="Recording/finalization active; request fresh time or action after closure";
    else{
        acquisitionPause();
        if(request.kind==R3BleOwnerRequest::Start){
            if(!i2cReady||!sdReady)message="I2C or SD is unavailable";
            else ok=ecosystemStartRecording(&request,message);
        }else if(request.kind==R3BleOwnerRequest::SetTime){
            const uint64_t now=esp_timer_get_time();
            if(!i2cReady||now<request.receivedLocalUs||now-request.receivedLocalUs>1000000||
               request.sourceReadAgeMs>1500||request.roundtripUs>1000000||
               !r3BleOwnerActionCurrent(request))message="RTC source or time exchange is stale";
            else{
                // Whole-second calendar correction only. No offset/drift claim.
                const uint64_t utc=request.unixS+(now-request.receivedLocalUs)/1000000;
                ecosystemForgetClockEvidence();
                ok=panelSetRtcUtc(utc);
                pollRtc(false);
                ok=ok&&rtcUtcNow()!=0;
                if(ok){
                    char id[18];r3_ble::formatDevice(request.sourceDevice,id);
                    correction.applied=true;correction.authorityId=id;
                    correction.authorityBoot=request.sourceBoot;correction.revision=request.clockRevision;
                    correction.requestId=request.requestId;correction.unixS=uint32_t(utc);
                    correction.receivedLocalUs=request.receivedLocalUs;correction.appliedLocalUs=now;
                    correction.sourceCaptureUs=request.sourceCaptureUs;
                    correction.sourceReadAgeMs=request.sourceReadAgeMs;correction.roundtripUs=request.roundtripUs;
                }
                message=ok?"RTC corrected from R3; calendar accuracy unqualified":"RTC correction/readback failed";
            }
        }
        acquisitionResume();
    }
    publish(i2cReady,sdReady);
    r3BleCompleteOwnerAction(request,ok,message);
}
