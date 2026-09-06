#include <Arduino.h>
#include <Wire.h>
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
}

const char* pollRtc() {
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
    Serial.printf("RTC: %04d-%02d-%02d %02d:%02d:%02d DOW=%u (timezone unspecified)\n",
                  year, month, day, hour, minute, second, r[3]);
    uint64_t days = 0;
    for (int y = 2000; y < year; ++y) days += leap(y) ? 366 : 365;
    for (int m = 1; m < month; ++m) days += monthDays[m - 1] + ((m == 2 && leap(year)) ? 1 : 0);
    days += day - 1;
    const uint64_t seconds = days * 86400 + hour * 3600 + minute * 60 + second;
    const char* result = "WAIT";
    if (previousValid) {
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
    return result;
}
