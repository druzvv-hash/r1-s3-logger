#pragma once

#include "settings_core.h"
// Diagnostic-rate triggered conversion with applied coefficients; restores ADC_CONFIG.
bool applyInaSettings(const settings::Config& config);
bool inaSettingsHealthy();
const char* testIna228();

struct Ina228Reading {
    bool valid = false;
    double busVolts = 0;
    double currentAmps = 0;
    double temperatureC = 0;
};
const Ina228Reading& latestIna228Reading();
