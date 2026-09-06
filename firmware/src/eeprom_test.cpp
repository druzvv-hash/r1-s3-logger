#include <Arduino.h>
#include <Wire.h>
#include <SD.h>
#include <SPI.h>
#include <cstring>
#include "pins.h"
#include "eeprom_test.h"

namespace {
constexpr uint8_t address = 0x50;
constexpr uint16_t size = 4096;
constexpr uint16_t testOffset = size - 32;
uint8_t original[size];

bool readBlock(uint16_t offset, uint8_t* bytes, size_t count) {
    Wire.beginTransmission(address);
    Wire.write(static_cast<uint8_t>(offset >> 8));
    Wire.write(static_cast<uint8_t>(offset));
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(address, count) != count) return false;
    for (size_t i = 0; i < count; ++i) bytes[i] = Wire.read();
    return true;
}

bool writeBlock(const uint8_t* bytes) {
    Wire.beginTransmission(address);
    Wire.write(static_cast<uint8_t>(testOffset >> 8));
    Wire.write(static_cast<uint8_t>(testOffset));
    Wire.write(bytes, 16); // Partial page, never crosses a 32-byte boundary.
    if (Wire.endTransmission() != 0) return false;
    const uint32_t started = millis();
    do {
        delay(1);
        Wire.beginTransmission(address);
        if (Wire.endTransmission() == 0) return true;
    } while (millis() - started < 25);
    return false;
}

bool backup() {
    if (!SD.begin(pins::SD_CS, SPI, 10000000, "/sd", 5, false)) return false;
    char path[40];
    bool unused = false;
    for (unsigned n = 0; n < 10000; ++n) {
        snprintf(path, sizeof(path), "/eeprom_before_%04u.bin", n);
        if (!SD.exists(path)) { unused = true; break; }
    }
    if (!unused) { SD.end(); return false; }
    File file = SD.open(path, FILE_WRITE);
    if (!file) { SD.end(); return false; }
    const size_t written = file.write(original, size);
    file.flush();
    file.close();
    file = SD.open(path, FILE_READ);
    bool valid = file && file.size() == size && written == size;
    uint8_t check[32];
    for (uint16_t offset = 0; valid && offset < size; offset += sizeof(check)) {
        valid = file.read(check, sizeof(check)) == sizeof(check) &&
                memcmp(check, original + offset, sizeof(check)) == 0;
    }
    file.close();
    SD.end();
    if (valid) Serial.printf("EEPROM backup verified: %s (4096 bytes)\n", path);
    return valid;
}
}

const char* testEeprom() {
    Serial.println("\nEEPROM 24C32: 0x50, backup + test + restore");
    for (uint16_t offset = 0; offset < size; offset += 32) {
        if (!readBlock(offset, original + offset, 32)) {
            Serial.println("EEPROM FAIL: read failed; no data written.");
            return "READ FAIL";
        }
    }
    if (!backup()) {
        Serial.println("EEPROM SKIP: verified SD backup unavailable; no EEPROM write.");
        return "SKIP";
    }
    // No calibration map exists yet: only test an apparently unused final page.
    bool allFF = true, allZero = true;
    for (uint16_t i = testOffset; i < size; ++i) {
        allFF &= original[i] == 0xFF;
        allZero &= original[i] == 0;
    }
    if (!allFF && !allZero) {
        Serial.println("EEPROM SKIP: final page contains data; choose a reserved area first.");
        return "SKIP";
    }
    uint8_t pattern[16], check[32];
    for (unsigned i = 0; i < sizeof(pattern); ++i) pattern[i] = 0xA5 ^ (i * 13);
    const bool written = writeBlock(pattern);
    const bool matches = readBlock(testOffset, check, sizeof(pattern)) &&
                         memcmp(check, pattern, sizeof(pattern)) == 0;
    // Always attempt restoration, even after a failed/partial test write.
    bool restored = false;
    for (unsigned attempt = 0; attempt < 3 && !restored; ++attempt) {
        writeBlock(original + testOffset);
        restored = readBlock(testOffset, check, sizeof(pattern)) &&
                   memcmp(check, original + testOffset, sizeof(pattern)) == 0;
    }
    for (uint16_t offset = 0; restored && offset < size; offset += 32) {
        restored = readBlock(offset, check, sizeof(check)) &&
                   memcmp(check, original + offset, sizeof(check)) == 0;
    }
    if (!restored) {
        Serial.println("EEPROM RESTORE FAIL: retain SD backup; stop EEPROM writes.");
        return "RESTORE FAIL";
    }
    Serial.println(written && matches
        ? "EEPROM PASS: pattern matched; all 4096 original bytes restored and verified."
        : "EEPROM FAIL: pattern write/read failed (check WP); original image verified.");
    return written && matches ? "PASS" : "FAIL";
}
