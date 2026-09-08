#include <Arduino.h>
#include <Wire.h>
#include <cstring>
#include "rtc_test.h"

namespace {
int bcd(uint8_t value) {
    if ((value & 15) > 9 || (value >> 4) > 9) return -1;
    return (value >> 4) * 10 + (value & 15);
}
bool leap(int year) {
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}
bool previousValid = false;
uint64_t previousSeconds = 0;
uint32_t previousMillis = 0;
bool trustedUtc = false;
}

const char* pollRtc() {
    trustedUtc = false;
    uint8_t r[19];
    Wire.beginTransmission(0x68);
    Wire.write(0x00); // Register pointer only; no register contents written.
    if (Wire.endTransmission(false) != 0 ||
        Wire.requestFrom(static_cast<uint8_t>(0x68), sizeof(r)) != sizeof(r)) {
        previousValid = false;
        Serial.println("RTC FAIL: DS3231 read failed.");
        return "READ FAIL";
    }
    for (auto& byte : r) byte = Wire.read();
    const uint32_t sampledAt = millis();
    const int second = bcd(r[0]);
    const int minute = bcd(r[1]);
    int hour = bcd(r[2] & 0x3F);
    if (r[2] & 0x40) {
        const int hour12 = bcd(r[2] & 0x1F);
        hour = hour12 >= 1 && hour12 <= 12
            ? hour12 % 12 + ((r[2] & 0x20) ? 12 : 0) : -1;
    }
    const int day = bcd(r[4]);
    const int month = bcd(r[5] & 0x1F);
    const int yy = bcd(r[6]);
    // Interpret the century bit relative to 2000 for this project.
    const int year = 2000 + ((r[5] & 0x80) ? 100 : 0) + yy;
    const int monthDays[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    const bool calendarValid = second >= 0 && second <= 59 &&
        minute >= 0 && minute <= 59 && hour >= 0 && hour <= 23 &&
        yy >= 0 && month >= 1 && month <= 12 && day >= 1 &&
        day <= monthDays[month - 1] + ((month == 2 && leap(year)) ? 1 : 0) &&
        r[3] >= 1 && r[3] <= 7 && !(r[2] & 0x80) && !(r[5] & 0x60);
    const bool osf = r[15] & 0x80;
    const float temperature = static_cast<int8_t>(r[17]) + (r[18] >> 6) * 0.25f;
    Serial.printf("RTC DS3231: OSF=%u EOSC=%u temperature=%.2f C\n",
                  osf, (r[14] >> 7) & 1, temperature);
    if (!calendarValid) {
        previousValid = false;
        Serial.println("RTC FAIL: invalid calendar/BCD; time left unchanged.");
        return "BAD DATE";
    }
    Serial.printf("RTC: %04d-%02d-%02d %02d:%02d:%02d DOW=%u (UTC after browser synchronization)\n",
                  year, month, day, hour, minute, second, r[3]);
    uint64_t days = 0;
    for (int y = 2000; y < year; ++y) days += leap(y) ? 366 : 365;
    for (int m = 1; m < month; ++m) days += monthDays[m - 1] + ((m == 2 && leap(year)) ? 1 : 0);
    days += day - 1;
    const uint64_t seconds = days * 86400 + hour * 3600 + minute * 60 + second;
    const char* result = "WAIT";
    if (previousValid && sampledAt - previousMillis >= 1500) {
        const uint32_t elapsed = sampledAt - previousMillis;
        const int64_t advance = static_cast<int64_t>(seconds) - previousSeconds;
        const int64_t errorMs = advance * 1000 - elapsed;
        const bool ticking = advance > 0 && errorMs >= -1500 && errorMs <= 1500;
        Serial.printf("RTC tick %s: RTC advanced %lld s over %lu ms\n",
                      ticking ? "PASS" : "FAIL", advance, static_cast<unsigned long>(elapsed));
        result = ticking ? (osf ? "SET TIME" : "TICK OK") : "TICK FAIL";
    }
    if (osf) Serial.println("RTC time untrusted: OSF set; no time set or flags cleared.");
    Serial.println("RTC: wall-clock accuracy and battery retention not verified.");
    previousSeconds = seconds;
    previousMillis = sampledAt;
    previousValid = true;
    trustedUtc = !osf;
    return result;
}

namespace {
bool readRtcRegisters(uint8_t address, uint8_t* data, size_t count) {
    Wire.beginTransmission(0x68);
    Wire.write(address);
    if (Wire.endTransmission(false) != 0 ||
        Wire.requestFrom(static_cast<uint8_t>(0x68), count) != count) return false;
    for (size_t i = 0; i < count; ++i) data[i] = Wire.read();
    return true;
}
bool writeRtcRegisters(uint8_t address, const uint8_t* data, size_t count) {
    Wire.beginTransmission(0x68);
    Wire.write(address);
    Wire.write(data, count);
    return Wire.endTransmission() == 0;
}
uint8_t toBcd(unsigned value) { return (value / 10) * 16 + value % 10; }
void encodeUtc(uint64_t epoch, uint8_t* r) {
    const uint64_t since2000 = epoch - 946684800ULL;
    unsigned days = since2000 / 86400;
    unsigned remaining = since2000 % 86400;
    r[0] = toBcd(remaining % 60);
    r[1] = toBcd(remaining / 60 % 60);
    r[2] = toBcd(remaining / 3600); // 24-hour mode
    r[3] = (days + 6) % 7 + 1; // Sunday=1, 2000-01-01 was Saturday
    unsigned year = 2000;
    while (days >= (leap(year) ? 366U : 365U)) {
        days -= leap(year) ? 366 : 365;
        ++year;
    }
    const unsigned monthDays[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    unsigned month = 0;
    while (true) {
        unsigned length = monthDays[month] + (month == 1 && leap(year) ? 1 : 0);
        if (days < length) break;
        days -= length;
        ++month;
    }
    r[4] = toBcd(days + 1);
    r[5] = toBcd(month + 1);
    r[6] = toBcd(year - 2000);
}
bool setRtcUtc(uint64_t epoch) {
    uint8_t control;
    if (!readRtcRegisters(0x0E, &control, 1)) return false;
    const uint8_t enabled = control & 0x7F; // Enable oscillator on battery, preserve other bits.
    if (enabled != control && !writeRtcRegisters(0x0E, &enabled, 1)) return false;
    uint8_t expected[7], actual[7], next[7];
    encodeUtc(epoch, expected);
    encodeUtc(epoch + 1, next);
    previousValid = false;
    if (!writeRtcRegisters(0, expected, 7) || !readRtcRegisters(0, actual, 7)) return false;
    if (memcmp(actual, expected, 7) != 0 && memcmp(actual, next, 7) != 0) return false;
    uint8_t status;
    if (!readRtcRegisters(0x0F, &status, 1)) return false;
    // Alarm flags are cleared by writing zero: write ones to preserve even newly raised flags.
    const uint8_t cleared = (status & 0x7F) | 0x03;
    if (!writeRtcRegisters(0x0F, &cleared, 1) || !readRtcRegisters(0x0F, &status, 1)) return false;
    if (status & 0x80) return false;
    return readRtcRegisters(0x0E, &control, 1) && !(control & 0x80);
}
}

#include "storage_check.h"
#include "settings.h"
#include "test_panel.h"

uint64_t rtcUtcNow(){return trustedUtc ? previousSeconds+946684800ULL+(uint32_t(millis()-previousMillis)/1000) : 0;}
bool panelSetRtcUtc(uint64_t epoch){return epoch>=946684800ULL&&epoch<4102444799ULL&&setRtcUtc(epoch);}

bool handleRtcSerial() {
    static char line[3200];
    static size_t length = 0;
    static bool overflow = false;
    while (Serial.available()) {
        const char ch = Serial.read();
        if (ch == '\r') continue;
        if (ch != '\n') {
            if (length < sizeof(line) - 1) line[length++] = ch;
            else overflow = true;
            continue;
        }
        line[length] = 0;
        if (!overflow && panelHandleSerial(line)) { length=0; return false; }
        if (!overflow && strcmp(line, "EEPROM DUMP") == 0) {
            length = 0;
            dumpEepromReadOnly();
            return false;
        }
        if (!overflow && handleSettingsCommand(line)) { length=0; return false; }
        uint64_t epoch = 0;
        bool valid = !overflow && length > 9 && strncmp(line, "TIME UTC ", 9) == 0 && length <= 19;
        for (size_t i = 9; valid && i < length; ++i) {
            valid = line[i] >= '0' && line[i] <= '9';
            if (valid) epoch = epoch * 10 + line[i] - '0';
        }
        // Restrict this bring-up protocol to 2000–2099; allow a one-second readback rollover.
        valid = valid && epoch >= 946684800ULL && epoch < 4102444799ULL;
        length = 0;
        overflow = false;
        if (!valid) {
            Serial.println("RTC SET ERROR: expected TIME UTC <Unix seconds, 2000-2099>");
            continue;
        }
        if (!setRtcUtc(epoch)) {
            Serial.println("RTC SET ERROR: I2C/write/readback/status verification failed; inspect RTC");
            return true;
        }
        Serial.printf("RTC SET OK UTC %llu: readback verified, OSF=0 EOSC=0\n", epoch);
        return true;
    }
    return false;
}
