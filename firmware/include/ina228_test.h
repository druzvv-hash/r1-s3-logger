#pragma once

#include "settings_core.h"
// Diagnostic-rate triggered conversion with applied coefficients; restores ADC_CONFIG.
bool applyInaSettings(const settings::Config& config);
bool inaSettingsHealthy();
bool captureInaIdentity(uint16_t& manufacturer,uint16_t& device,uint16_t& adc);
const char* testIna228();

struct Ina228Reading {
    bool valid = false;
    double busVolts = 0;
    double currentAmps = 0;
    double temperatureC = 0;
    int32_t shuntRaw = 0;
    uint32_t busRaw = 0;
    int32_t tempRaw = 0;
    double shuntMicrovolts = 0;
    uint32_t sampleId = 0;
    uint32_t sampledAt = 0;
};
const Ina228Reading& latestIna228Reading();
void acquisitionBegin();
void acquisitionStep();
bool acquisitionIdle();
uint32_t acquisitionSlackUs();
// Time until the next trigger or conversion-ready check, including ADC wait.
uint32_t acquisitionWorkBudgetUs();
void acquisitionPause();
void acquisitionResume();
const char* acquisitionStatus();
struct AcquisitionStats {
    uint32_t requestedHz=0, valid=0, invalid=0, missed=0, maxLateUs=0;
    uint32_t maintenance=0, maintenanceMs=0, maxReadUs=0;
    double measuredHz=0;
};
const AcquisitionStats& acquisitionStats();
