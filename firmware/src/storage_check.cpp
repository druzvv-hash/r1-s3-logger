#include <Arduino.h>
#include <Wire.h>
#include <cstring>
#include "storage_check.h"

namespace {
bool readImage(uint8_t* image) {
    for (unsigned offset = 0; offset < 4096; offset += 32) {
        Wire.beginTransmission(0x50);
        Wire.write(uint8_t(offset >> 8));
        Wire.write(uint8_t(offset));
        if (Wire.endTransmission(false) != 0 ||
            Wire.requestFrom(uint8_t(0x50), uint8_t(32)) != 32) return false;
        for (unsigned i = 0; i < 32; ++i) image[offset+i] = Wire.read();
    }
    return true;
}
uint32_t imageCrc(const uint8_t* p) {
    uint32_t crc = 0xFFFFFFFF;
    for (unsigned i = 0; i < 4096; ++i) {
        crc ^= p[i];
        for (unsigned b = 0; b < 8; ++b) crc = (crc >> 1) ^ ((crc & 1) ? 0xEDB88320 : 0);
    }
    return ~crc;
}
uint8_t first[4096], second[4096];
bool readVerified() {
    return readImage(first) && readImage(second) && memcmp(first, second, sizeof(first)) == 0;
}
}
const char* checkEepromReadOnly() {
    if (!readVerified()) {
        Serial.println("EEPROM READ FAIL: two full reads did not complete/match; no writes.");
        return "FAIL";
    }
    Serial.printf("EEPROM READ OK: 4096 bytes, repeated read matched, CRC32=%08lX; no writes.\n",
                  (unsigned long)imageCrc(first));
    return "READ";
}
void dumpEepromReadOnly() {
    if (!readVerified()) {
        Serial.println("EEPROM DUMP ERROR: read/match failed; no writes.");
        return;
    }
    Serial.printf("EEPROM BEGIN 4096 %08lX\n", (unsigned long)imageCrc(first));
    for (unsigned offset = 0; offset < 4096; offset += 32) {
        Serial.printf("EEPROM HEX %04X ", offset);
        for (unsigned j = 0; j < 32; ++j) Serial.printf("%02X", first[offset+j]);
        Serial.println();
    }
    Serial.println("EEPROM END");
}
