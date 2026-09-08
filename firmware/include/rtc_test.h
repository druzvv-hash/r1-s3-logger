#pragma once
#include <stdint.h>
uint64_t rtcUtcNow();
bool panelSetRtcUtc(uint64_t epoch);
// Read-only DS3231 check. Call periodically; never sets time or clears OSF.
const char* pollRtc(bool verbose=true);

// Explicit TIME UTC command only; never sets time automatically on boot.
bool handleLegacyLine(const char* line);
