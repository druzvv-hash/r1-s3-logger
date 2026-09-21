#pragma once
#include <Arduino.h>
// Begin/tick on the network task. Configuration requests are copied to its queue.
void wifiStationBegin();
void wifiStationTick();
bool wifiStationConfigure(const char* hexPair,const char*& message);
String wifiStationJson();
