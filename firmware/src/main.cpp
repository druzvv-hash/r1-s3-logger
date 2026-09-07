#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <cstring>
#include <Adafruit_SH110X.h>
#include "pins.h"
#include "eeprom_test.h"
#include "rtc_test.h"
#include "ina228_test.h"

bool i2cReady = false;
bool sdPassed = false;
bool oledReady = false;
const char* eepromStatus = "NOT RUN";
const char* rtcStatus = "WAIT";
const char* inaStatus = "WAIT";
unsigned i2cCount = 0;
unsigned i2cErrors = 0;
Adafruit_SH1106G oled(128, 64, &Wire, -1, 100000, 100000);

void updateOled() {
    if (!oledReady) return;
    oled.clearDisplay();
    oled.setTextColor(SH110X_WHITE);
    oled.setTextWrap(false);
    oled.setTextSize(1);
    oled.setCursor(4, 3);
    oled.print("R1-S3");
    const auto& reading = latestIna228Reading();
    if (reading.valid) {
        oled.setCursor(58, 3);
        oled.printf("T:%5.1f C", reading.temperatureC);
        oled.setTextSize(2);
        oled.setCursor(4, 15);
        oled.printf("%7.3f V", reading.busVolts);
        oled.setCursor(4, 33);
        if (reading.currentAmps >= 1000 || reading.currentAmps <= -1000)
            oled.printf("%+8.2f A", reading.currentAmps);
        else
            oled.printf("%+8.3f A", reading.currentAmps);
    } else {
        oled.setCursor(4, 18);
        oled.printf("INA: %s", inaStatus);
        oled.setCursor(4, 33);
        oled.print("U: ---  I: ---");
    }
    oled.setTextSize(1);
    oled.setCursor(4, 53);
    // Alternate diagnostics without crowding the two measurement lines.
    if ((millis() / 3000) % 2 == 0)
        oled.printf("SD:%s EEP:%s", sdPassed ? "PASS" : "FAIL", eepromStatus);
    else
        oled.printf("RTC:%s E:%u", rtcStatus, i2cErrors);
    oled.drawRect(0, 0, 128, 64, SH110X_WHITE);
    oled.display();
}

void initOled() {
    if (!i2cReady) return;
    Wire.beginTransmission(0x3C);
    if (Wire.endTransmission() != 0) {
        Serial.println("OLED: no ACK at 0x3C; display test skipped.");
        return;
    }
    // Wire is initialized on GPIO8/9 before the display; no reset pin.
    oledReady = oled.begin(0x3C, false);
    oled.setRotation(2);  // Rotate 180 degrees for the installed display orientation.
    Serial.println(oledReady
        ? "OLED: SH1106 128x64 static test started; confirm complete border and readable text."
        : "OLED FAIL: initialization failed.");
    updateOled();
}

void testSd() {
    constexpr uint32_t frequency = 10000000;
    constexpr char payload[] = "R1-S3 HWTEST v0.2: SD write/read test\r\n";
    Serial.println("\nSD test: CS=10 MOSI=11 SCK=12 MISO=13, 10 MHz");
    pinMode(pins::SD_CS, OUTPUT);
    digitalWrite(pins::SD_CS, HIGH);
    SPI.begin(pins::SD_SCK, pins::SD_MISO, pins::SD_MOSI, pins::SD_CS);
    // Never format a card automatically.
    if (!SD.begin(pins::SD_CS, SPI, frequency, "/sd", 5, false)) {
        Serial.println("SD FAIL: mount failed; check card, power and SPI wiring.");
        SD.end();
        return;
    }
    if (SD.cardType() == CARD_NONE) {
        Serial.println("SD FAIL: no card detected.");
        SD.end();
        return;
    }
    Serial.printf("SD capacity: %llu MiB\n", SD.cardSize() / (1024ULL * 1024ULL));
    char path[32];
    bool available = false;
    for (unsigned index = 0; index < 10000; ++index) {
        snprintf(path, sizeof(path), "/r1s3_test_%04u.txt", index);
        if (!SD.exists(path)) {
            available = true;
            break;
        }
    }
    if (!available) {
        Serial.println("SD FAIL: no unused test filename; existing files preserved.");
        SD.end();
        return;
    }
    File output = SD.open(path, FILE_WRITE);
    if (!output) {
        Serial.println("SD FAIL: cannot create test file.");
        SD.end();
        return;
    }
    const size_t expected = sizeof(payload) - 1;
    const size_t written = output.write(reinterpret_cast<const uint8_t*>(payload), expected);
    output.flush();
    output.close();
    Serial.printf("SD file: %s; written %u/%u bytes\n", path,
                  static_cast<unsigned>(written), static_cast<unsigned>(expected));
    SD.end();
    if (written != expected) {
        Serial.println("SD FAIL: incomplete write.");
        return;
    }
    if (!SD.begin(pins::SD_CS, SPI, frequency, "/sd", 5, false)) {
        Serial.println("SD FAIL: remount after write failed.");
        SD.end();
        return;
    }
    File input = SD.open(path, FILE_READ);
    if (!input) {
        Serial.println("SD FAIL: cannot reopen test file.");
        SD.end();
        return;
    }
    uint8_t actual[sizeof(payload)] = {};
    const size_t fileSize = input.size();
    const size_t received = input.read(actual, sizeof(actual));
    input.close();
    const bool match = fileSize == expected && received == expected &&
                       memcmp(actual, payload, expected) == 0;
    sdPassed = match;
    SD.end();
    Serial.println(match ? "SD PASS: write, close, remount and exact readback matched."
                         : "SD FAIL: readback size or content mismatch.");
    Serial.println("Test file retained. Power-cycle persistence not tested.");
}

void scanI2c() {
    bool found[128] = {};
    unsigned count = 0;
    unsigned errors = 0;
    Serial.println("\nI2C scan: SDA=8 SCL=9, 100 kHz (7-bit addresses)");
    for (uint8_t address = 0x08; address <= 0x77; ++address) {
        Wire.beginTransmission(address);
        const uint8_t result = Wire.endTransmission();
        if (result == 0) {
            found[address] = true;
            ++count;
            Serial.printf("  ACK 0x%02X\n", address);
        } else if (result != 2) {
            ++errors;
            Serial.printf("  ERROR 0x%02X: code %u\n", address, result);
        }
        delay(2);
    }
    Serial.printf("Devices: %u; bus errors: %u\n", count, errors);
    i2cCount = count;
    i2cErrors = errors;
    Serial.printf("Expected addresses: OLED 0x3C=%s, INA228 0x40=%s, "
                  "24C32 0x50=%s, RTC 0x68=%s\n",
                  found[0x3C] ? "ACK" : "MISSING",
                  found[0x40] ? "ACK" : "MISSING",
                  found[0x50] ? "ACK" : "MISSING",
                  found[0x68] ? "ACK" : "MISSING");
    Serial.println("ACK confirms an address response, not device identity.");
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("\nR1-S3 HWTEST v0.10: OLED voltage/current + INA228 nominal current");
    Serial.printf("Chip: %s rev %u, CPU %u MHz\n", ESP.getChipModel(),
                  ESP.getChipRevision(), ESP.getCpuFreqMHz());
    Serial.printf("Flash: %u bytes, %u Hz\n", ESP.getFlashChipSize(),
                  ESP.getFlashChipSpeed());
    Serial.printf("PSRAM: %s, total %u bytes, free %u bytes\n",
                  psramFound() ? "DETECTED" : "NOT DETECTED",
                  ESP.getPsramSize(), ESP.getFreePsram());
    Serial.println("Memory sizes only; no memory stress test performed.");
    i2cReady = Wire.begin(pins::I2C_SDA, pins::I2C_SCL, 100000);
    Wire.setTimeOut(50);
    if (i2cReady) {
        scanI2c();
    } else {
        Serial.println("FAIL: I2C initialization failed.");
    }
    testSd();
    initOled();
    if (i2cReady && sdPassed) {
        eepromStatus = testEeprom();
        updateOled();
    } else {
        Serial.println("EEPROM SKIP: I2C and SD must pass first.");
    }
    if (i2cReady) rtcStatus = pollRtc();
    if (i2cReady) inaStatus = testIna228();
    updateOled();
}

void loop() {
    static uint32_t lastScan = millis();
    static uint32_t lastMeasurement = millis();
    if (i2cReady && handleRtcSerial()) {
        rtcStatus = pollRtc();
        updateOled();
        lastScan = millis();
    }
    const uint32_t now = millis();
    if (i2cReady && now - lastScan >= 10000) {
        lastScan = now;
        scanI2c();
        rtcStatus = pollRtc();
        updateOled();
    }
    if (i2cReady && millis() - lastMeasurement >= 1000) {
        inaStatus = testIna228();
        lastMeasurement = millis();
        updateOled();
    }
    delay(10);
}
