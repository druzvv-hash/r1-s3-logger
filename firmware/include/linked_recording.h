#pragma once
#include <stdint.h>

// Owner-driven coordinator. CAN capture is confirmed before R1 acquisition;
// this is a shared session, not a simultaneous hardware trigger.
namespace linked_recording {
enum Phase : uint8_t { Idle, CanStarting, R1Starting, Running, Stopping, Recovering, Closed, Failed };
enum Action : uint8_t { None=0, StartR1=1, StopR1=2, StopCan=4 };
struct Observation {
    bool fresh=false, canOwned=false, canRecording=false, canClosed=false;
    bool r1Busy=false, r1Running=false, r1Failed=false;
};
struct Coordinator {
    Phase phase=Idle;
    uint64_t began=0, lastStop=0;
    bool active()const{return phase>=CanStarting&&phase<=Recovering;}
    bool begin(uint64_t now){if(active())return false;phase=CanStarting;began=now;lastStop=0;return true;}
    void stop(){if(active()&&phase!=Recovering)phase=Stopping;}
    void fail(){if(active())phase=Recovering;}
    uint8_t step(uint64_t now,const Observation& o){
        if(!active())return None;
        if(phase==CanStarting){
            if(o.fresh&&o.canOwned&&o.canRecording){phase=R1Starting;return StartR1;}
            if(now-began>20000000)fail();
        }else if(phase==R1Starting){
            if(o.r1Failed||!o.fresh||!o.canOwned||!o.canRecording||now-began>30000000)fail();
            else if(o.r1Running)phase=Running;
        }else if(phase==Running){
            if(!o.r1Running||!o.fresh||!o.canOwned||!o.canRecording)fail();
        }
        if(phase==Stopping||phase==Recovering){
            if(o.r1Busy)return StopR1;
            // The queued START expires after 2 s; its echoed status TTL is 5 s.
            // Wait past both before accepting idle as proof of cancellation.
            if(o.fresh&&o.canClosed&&now-began>8000000){phase=phase==Recovering?Failed:Closed;return None;}
            if(o.fresh&&o.canOwned&&(!lastStop||now-lastStop>=2000000)){lastStop=now;return StopCan;}
        }
        return None;
    }
};
}
