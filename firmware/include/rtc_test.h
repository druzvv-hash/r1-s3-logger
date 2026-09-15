#pragma once
#include <stdint.h>
uint64_t rtcUtcNow();
uint64_t rtcUtcNowUs();
uint32_t rtcReadAgeMs();
uint32_t rtcClockRevision();
bool panelSetRtcUtc(uint64_t epoch);
// Read-only DS3231 check. Call periodically; never sets time or clears OSF.
const char* pollRtc(bool verbose=true);

// Legacy explicit TIME UTC command. The ecosystem owner separately performs
// idle-only, validated R3 calendar correction after authenticated enrollment.
bool handleLegacyLine(const char* line);
