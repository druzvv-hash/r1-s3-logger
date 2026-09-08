#pragma once
#include <stdint.h>

// Absolute schedule: a late owner skips elapsed slots, never emits a catch-up burst.
class SampleClock {
public:
    void reset(uint64_t now, uint32_t hz) { period_=1000000/hz; next_=now+period_; }
    bool due(uint64_t now) const { return now>=next_; }
    uint32_t slack(uint64_t now) const { return now>=next_?0:uint32_t(next_-now); }
    uint32_t take(uint64_t now, uint32_t& lateUs) {
        const uint64_t elapsed=now-next_;
        const uint32_t skipped=elapsed/period_;
        lateUs=elapsed%period_;
        next_+=(uint64_t(skipped)+1)*period_;
        return skipped;
    }
    uint32_t period() const { return period_; }
private:
    uint64_t next_=0;
    uint32_t period_=20000;
};
