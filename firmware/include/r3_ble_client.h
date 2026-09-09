#pragma once
#include <Arduino.h>

// Radio, pairing and NVS association work runs on core 0. The acquisition/I2C
// owner alone executes requests below; callbacks never access RTC or SD.
void r3BleBegin();
bool r3BleCommand(const char* argument, const char*& message);
String r3BleStatusJson();

enum class R3BleOwnerState : uint8_t { Ready, Starting, Running, Stopping, Error };
struct R3BleOwnerSnapshot {
    R3BleOwnerState state = R3BleOwnerState::Ready;
    uint64_t sessionId = 0, groupId = 0;
    bool ready = false, rtcValid = false, fileClosed = false, clockSynced = false;
    char file[160] = {}, error[96] = {};
};
struct R3BleOwnerRequest {
    enum Kind : uint8_t { Start, Stop, SetTime } kind;
    uint64_t requestId = 0, sourceBoot = 0, targetBoot = 0;
    uint64_t sessionId = 0, groupId = 0, expiresLocalUs = 0, receivedLocalUs = 0;
    uint64_t sourceCaptureUs = 0;
    uint32_t epoch = 0, unixS = 0, clockRevision = 0, startGeneration = 0;
    uint32_t sourceReadAgeMs = 0, roundtripUs = 0;
    uint8_t sourceDevice[6] = {};
};
uint64_t r3BleBootId();
void r3BleCopyDeviceId(uint8_t out[6]);
bool r3BleRemoteAllowed();
// Local STOP wins over remote START already received/queued on the other core.
void r3BleCancelPendingStarts();
void r3BlePublishOwner(const R3BleOwnerSnapshot& snapshot);
bool r3BleTakeOwnerAction(R3BleOwnerRequest& request);
// Recheck immediately before executing. This rejects lost links, changed
// connection epochs, expiry and revoked permission, including queued requests.
bool r3BleOwnerActionCurrent(const R3BleOwnerRequest& request);
void r3BleCompleteOwnerAction(const R3BleOwnerRequest& request, bool accepted,
                              const char* message);
