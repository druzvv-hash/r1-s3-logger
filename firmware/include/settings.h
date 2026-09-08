#pragma once
#include "settings_core.h"
void initSettings();
bool handleSettingsCommand(const char* line);
const settings::Config& appliedSettings();
bool settingsReady();
const char* settingsStatus();
void setSettingsRecording(bool recording);
