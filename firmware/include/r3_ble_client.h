#pragma once
#include <Arduino.h>

// All radio/discovery work runs on a separate core-0 worker. Owner commands
// only validate and enqueue. S1 observes coarse beacons; never disciplines time.
void r3BleBegin();
bool r3BleCommand(const char* argument, const char*& message);
String r3BleStatusJson();
