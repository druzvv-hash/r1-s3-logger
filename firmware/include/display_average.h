#pragma once
#include <cstdint>
#include <cmath>

// Acquisition-owner only. Presentation data never feeds the recorder.
struct DisplayAverage {
    double volts=0, amps=0;
    uint32_t count=0, revision=0;
    void add(double u,double i,uint32_t rev,uint8_t quality) {
        if(revision!=rev || quality) { clear(); revision=rev; }
        if((quality&5) || !std::isfinite(u) || !std::isfinite(i))return;
        ++count;
        volts+=(u-volts)/count; amps+=(i-amps)/count;
    }
    void clear(){volts=amps=0;count=0;}
};
