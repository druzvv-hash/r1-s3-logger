#pragma once
#include "settings_core.h"
void initSettings();
bool handleSettingsCommand(const char* line);
const settings::Config& appliedSettings();
bool settingsReady();
const char* settingsStatus();
void setSettingsRecording(bool recording);
// Owner-task only; web/USB commands use the same validated hardware/store path.
uint32_t settingsRevision();
uint64_t settingsGeneration();
bool panelApplySettings(const settings::Bytes& payload, const char*& error);
bool panelSaveSettings(const char*& error);
