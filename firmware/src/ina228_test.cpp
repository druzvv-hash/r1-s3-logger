#include <Arduino.h>
#include <Wire.h>
#include "pins.h"
#include "ina228_test.h"
#include "shunt_config.h"

namespace {
Ina228Reading latest;
constexpr uint8_t address = 0x40;
constexpr int32_t signed20(uint32_t word) {
    return (word >> 4) & 0x80000 ? int32_t(word >> 4) - 0x100000 : int32_t(word >> 4);
}
constexpr int32_t signed16(uint32_t word) {
    return word & 0x8000 ? int32_t(word) - 0x10000 : int32_t(word);
}
static_assert(signed20(0xFFFFF0) == -1, "negative shunt LSB");
static_assert(signed20(0x800000) == -524288, "negative shunt limit");
static_assert(signed20(0x7FFFF0) == 524287, "positive shunt limit");
static_assert(signed20(0) == 0 && signed20(0x10) == 1, "zero and positive LSB");
static_assert(signed16(0xFF80) == -128, "negative temperature");

bool readRegister(uint8_t reg, uint8_t length, uint32_t& value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(address, length) != length) {
        while (Wire.available()) Wire.read();
        return false;
    }
    value = 0;
    for (uint8_t i = 0; i < length; ++i) value = (value << 8) | uint8_t(Wire.read());
    return true;
}
bool writeRegister(uint8_t reg, uint16_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(uint8_t(value >> 8));
    Wire.write(uint8_t(value));
    return Wire.endTransmission() == 0;
}
}

const char* testIna228() {
    latest.valid = false;
    static bool restoreFailed = false;
    if (restoreFailed) return "RESTORE FAIL";
    uint32_t manufacturer, device, config, adc;
    Serial.println("\nINA228: identity and fresh triggered ADC test at 0x40");
    if (!readRegister(0x3E, 2, manufacturer) || !readRegister(0x3F, 2, device) ||
        !readRegister(0x00, 2, config) || !readRegister(0x01, 2, adc)) {
        Serial.println("INA228 FAIL: register read failed.");
        return "I2C FAIL";
    }
    Serial.printf("INA228 manufacturer=0x%04lX device=0x%04lX CONFIG=0x%04lX ADC=0x%04lX\n",
                  (unsigned long)manufacturer, (unsigned long)device,
                  (unsigned long)config, (unsigned long)adc);
    if (manufacturer != 0x5449 || (device >> 4) != 0x228) {
        Serial.println("INA228 FAIL: unexpected identity; no registers changed.");
        return "ID FAIL";
    }
    // All three channels, 1052 us each, one sample. Writing clears stale CNVRF.
    // CONFIG (including conversion delay/range) and calibration remain unchanged.
    const char* result = "I2C FAIL";
    uint32_t diag = 0, shunt = 0, bus = 0, temperature = 0;
    if (writeRegister(0x01, 0x7B68)) {
        const uint32_t start = millis();
        result = "TIMEOUT";
        while (millis() - start < 1000) {
            // Reading DIAG_ALRT clears conversion-ready / latched diagnostic flags.
            if (!readRegister(0x0B, 2, diag)) { result = "I2C FAIL"; break; }
            if (diag & 0x02) {
                result = readRegister(0x04, 3, shunt) && readRegister(0x05, 3, bus) &&
                         readRegister(0x06, 2, temperature) ? "ADC OK" : "I2C FAIL";
                break;
            }
            delay(2);
        }
    }
    uint32_t restored = 0;
    if (!writeRegister(0x01, uint16_t(adc)) || !readRegister(0x01, 2, restored) || restored != adc) {
        restoreFailed = true;
        Serial.println("INA228 RESTORE FAIL: further INA tests disabled until reboot.");
        return "RESTORE FAIL";
    }
    if (strcmp(result, "ADC OK") == 0) {
        pinMode(pins::INA228_ALERT, INPUT);
        Serial.printf("INA228 raw VSHUNT=0x%06lX VBUS=0x%06lX TEMP=0x%04lX DIAG=0x%04lX\n",
                      (unsigned long)shunt, (unsigned long)bus,
                      (unsigned long)temperature, (unsigned long)diag);
        const bool narrow = config & 0x10;
        const double shuntMicrovolts = signed20(shunt) * (narrow ? 0.078125 : 0.3125);
        Serial.printf("INA228 VBUS=%.6f V; VSHUNT=%.4f uV; die=%.3f C; range=+/-%s mV\n",
                      (bus >> 4) * 0.0001953125,
                      shuntMicrovolts,
                      signed16(temperature) * 0.0078125, narrow ? "40.96" : "163.84");
        Serial.printf("INA228 ALERT GPIO14=%d (passive level only); ADC_CONFIG restored.\n",
                      digitalRead(pins::INA228_ALERT));
        if ((bus & 0x80000F) || (shunt & 0x0F)) {
            result = "DATA FAIL";
        } else if (signed20(shunt) == -524288 || signed20(shunt) == 524287) {
            result = "SHUNT LIMIT";
            Serial.println("INA228: shunt ADC at rail; current withheld.");
        } else {
            latest.busVolts = (bus >> 4) * 0.0001953125;
            latest.currentAmps = shunt::ampsFromMicrovolts(shuntMicrovolts);
            latest.temperatureC = signed16(temperature) * 0.0078125;
            latest.valid = true;
            Serial.printf("INA228 I_nominal=%+.4f A (60 mV / 400 A, %.1f uOhm; no offset/gain correction)\n",
                          shunt::ampsFromMicrovolts(shuntMicrovolts), shunt::microOhms);
        }
        if (narrow) Serial.println("INA228: narrow range cannot cover this shunt's full 400 A rating.");
        Serial.println("No current calibration, external voltage comparison or active ALERT test performed.");
    }
    Serial.printf("INA228 result: %s\n", result);
    return result;
}

const Ina228Reading& latestIna228Reading() { return latest; }
