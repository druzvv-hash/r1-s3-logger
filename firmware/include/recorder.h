#pragma once
#include "recording_format.h"
#include <Arduino.h>
namespace recorder {
enum class State : uint8_t { Ready, Starting, Running, Stopping, Error };
struct Status {
    char path[160]={}, error[96]={};
    uint64_t rows=0, bytes=0, elapsedUs=0;
    uint32_t queued=0, highWater=0, overflows=0, maxWriteUs=0, maxSyncUs=0, part=0;
    double wh=0, ah=0;
};
// Start/stop/push belong to the acquisition owner, at conversion boundaries.
bool start(const recording::SessionInfo& info, const char*& message);
bool stop(const char*& message);
void push(const recording::Sample& sample);
bool busy();
State state();
const char* stateName();
Status status();
// Called only by the existing SD owner. It serializes all mount/write/close and
// download admission; the acquisition task never waits on SD operations.
void storageStep(bool transferActive);
}
