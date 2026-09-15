#include "linked_recording.h"
#include <cassert>
#include <iostream>
using namespace linked_recording;
int main(){
    Coordinator c;Observation o;
    assert(c.begin(100));assert(!c.begin(200));
    o.fresh=true;o.canRecording=true;
    assert(c.step(1000,o)==None); // another session never starts R1
    o.canOwned=true;assert(c.step(2000,o)==StartR1);
    o.r1Busy=o.r1Running=true;c.step(3000,o);assert(c.phase==Running);
    c.stop();assert(c.step(4000,o)==StopR1);
    o.r1Busy=o.r1Running=false;assert(c.step(5000,o)==StopCan);
    assert(c.step(6000,o)==None); // bounded stop retries
    o.canClosed=true;o.canRecording=false;c.step(9000000,o);assert(c.phase==Closed);
    assert(c.begin(10000000));c.stop();o={};o.fresh=o.canClosed=true;
    c.step(10000001,o);assert(c.active()); // queued START has not expired
    o.canOwned=o.canRecording=true;o.canClosed=false;
    assert(c.step(11000000,o)==StopCan); // late START cancelled
    o.fresh=false;c.step(50000000,o);assert(c.active()); // never invent closure offline
    o.fresh=o.canClosed=true;o.canOwned=o.canRecording=false;c.step(51000000,o);assert(c.phase==Closed);
    c.begin(60000000);o={};c.step(81000000,o);assert(c.phase==Recovering);
    o.fresh=o.canClosed=true;c.step(82000000,o);assert(c.phase==Failed);
    c.begin(90000000);o={};o.fresh=o.canOwned=o.canRecording=true;
    assert(c.step(90000001,o)==StartR1);o.r1Failed=true;c.step(90000002,o);assert(c.phase==Recovering);
    o.canOwned=false;o.canClosed=false;assert(c.step(99000000,o)==None);assert(c.active()); // foreign recording must not be stopped
    Coordinator d;d.begin(1);o={};o.fresh=o.canOwned=o.canRecording=true;d.step(2,o);
    o.r1Busy=o.r1Running=true;d.step(3,o);o.fresh=false;
    assert(d.step(4,o)==StopR1);assert(d.phase==Recovering);
    std::cout<<"LINKED RECORDING PASS\n";
}
