#include "sample_clock.h"
#include <cassert>
#include <iostream>
int main(){
    SampleClock c;uint32_t late=0;
    // Fixed deadlines do not drift with I2C/UI latency.
    c.reset(123456789000ULL,100);
    assert(!c.due(123456798999ULL));
    assert(c.due(123456799000ULL));
    assert(c.take(123456799400ULL,late)==0&&late==400);
    assert(c.slack(123456799400ULL)==9600);
    assert(c.take(123456829750ULL,late)==2&&late==750);
    assert(c.slack(123456829750ULL)==9250); // Skip, never replay missed conversions.
    // Microsecond timestamps exceed 32 bits and remain correctly ordered.
    for(unsigned hz:{10,50,100}){
        uint64_t t=0x100000000ULL;
        c.reset(t,hz);const uint32_t period=1000000/hz;
        for(unsigned i=1;i<=hz*10;++i){
            assert(!c.due(t+i*period-1));
            assert(c.take(t+i*period+350,late)==0&&late==350);
        }
        assert(c.slack(t+10000000ULL)==period);
    }
    // Explicit maintenance/rate changes start a fresh schedule.
    c.reset(9000000000ULL,10);
    assert(c.slack(9000000000ULL)==100000);
    std::cout<<"SAMPLE CLOCK PASS\n";
}
