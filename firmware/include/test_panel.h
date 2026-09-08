#pragma once
#include <Arduino.h>
struct PanelHardware {
    const char* sd; const char* eeprom; const char* rtc; const char* ina;
    bool oled; unsigned i2cCount; unsigned i2cErrors;
    uint32_t oledFrames, oledChunkUs;
};
using PanelAction = bool (*)(const char* verb, const char* argument, const char*& message);
// Called only by the core 1 hardware owner. HTTP never touches Wire, SD or settings.
void panelBegin(PanelAction action);
void panelPoll();
void panelPublish(const PanelHardware& hardware);
bool panelHandleSerial(const char* line);
