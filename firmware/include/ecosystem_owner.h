#pragma once
#include "r3_ble_client.h"

// Core-1 acquisition owner only. Call poll at a conversion boundary, after
// local panel commands so a local Stop takes priority over remote actions.
void ecosystemOwnerPoll(bool i2cReady, bool sdReady);
bool ecosystemStartRecording(const R3BleOwnerRequest* remote, const char*& message, uint64_t localGroup=0);
bool ecosystemLinkedCommand(const char* argument,const char*& message);
bool ecosystemLinkedActive();
void ecosystemForgetClockEvidence();
