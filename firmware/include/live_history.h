#pragma once
#include <Arduino.h>
struct LivePoint {
    uint64_t id, tUs;
    double volts, amps;
    uint32_t revision;
    uint8_t quality;
};
bool liveHistoryBegin();
// Owner never waits for UI; a contended preview copy is counted, not hidden.
void liveHistoryPush(const LivePoint& point);
String liveHistoryJson(uint64_t after);
uint32_t liveHistoryDrops();
