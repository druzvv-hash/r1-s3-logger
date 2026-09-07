#pragma once

// Temporary triggered conversion; restores ADC_CONFIG. Current uses nominal shunt resistance.
const char* testIna228();

struct Ina228Reading {
    bool valid = false;
    double busVolts = 0;
    double currentAmps = 0;
    double temperatureC = 0;
};
const Ina228Reading& latestIna228Reading();
