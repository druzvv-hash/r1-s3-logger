#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <cstring>
#include <cmath>
#include <Adafruit_SH110X.h>
#include "pins.h"
#include "eeprom_test.h"
#include "rtc_test.h"
#include "ina228_test.h"
#include "storage_check.h"
#include "settings.h"
#include "local_input.h"
#include "recording_memory.h"
#include "test_panel.h"
#include "live_history.h"
#include "sd_files.h"
#include "recorder.h"
#include "build_provenance.h"
#include "firmware_version.h"
#include "rate_benchmark.h"
#include "r3_ble_client.h"
#include <esp_timer.h>
#include <esp_system.h>

#ifndef R1_SERVICE_TESTS
#define R1_SERVICE_TESTS 0
#endif

bool i2cReady = false;
bool sdPassed = false;
const char* sdStatus = "WAIT";
bool oledReady = false;
const char* eepromStatus = "NOT RUN";
const char* rtcStatus = "WAIT";
const char* inaStatus = "WAIT";
unsigned i2cCount = 0;
unsigned i2cErrors = 0;
Adafruit_SH1106G oled(128, 64, &Wire, -1, 100000, 100000);

uint8_t oledFrame[1024];
unsigned oledOffset=1024;
uint32_t oledFrames=0, oledChunkUs=0;
int lastContrast=-1;

void updateOled() {
    if (!oledReady) return;

    oled.clearDisplay();
    oled.setTextColor(SH110X_WHITE);
    oled.setTextWrap(false);
    oled.setTextSize(1);
    oled.setCursor(4, 3);
    oled.print("R1-S3");
    const auto& reading = latestIna228Reading();
    static double shownVolts=0, shownAmps=0;
    static uint32_t lastDisplay=0;
    static bool filterValid=false;
    const auto& config=appliedSettings();
    const uint32_t tick=millis();
    if (reading.valid) {
        const double alpha=filterValid && config.display_filter_tau_ms
            ? -std::expm1(-double(uint32_t(tick-lastDisplay))/config.display_filter_tau_ms) : 1.0;
        shownVolts+=alpha*(reading.busVolts-shownVolts);
        shownAmps+=alpha*(reading.currentAmps-shownAmps);
        filterValid=true;
    } else filterValid=false;
    lastDisplay=tick;
    if (reading.valid) {
        oled.setCursor(58, 3);
        oled.printf("T:%5.1f C", reading.temperatureC);
        oled.setTextSize(2);
        oled.setCursor(4, 15);
        oled.printf("%7.3f V", shownVolts);
        oled.setCursor(4, 33);
        if (shownAmps >= 1000 || shownAmps <= -1000)
            oled.printf("%+8.2f A", shownAmps);
        else
            oled.printf("%+8.3f A", shownAmps);
    } else {
        oled.setCursor(4, 18);
        oled.printf("INA: %s", inaStatus);
        oled.setCursor(4, 33);
        oled.print("U: ---  I: ---");
    }
    oled.setTextSize(1);
    oled.setCursor(4, 53);
    // Alternate diagnostics without crowding the two measurement lines.
    if (recorder::busy() || recorder::state()==recorder::State::Error)
        oled.printf("REC:%s",recorder::stateName());
    else if ((millis() / 3000) % 2 == 0)
        oled.printf("SD:%s %s", sdStatus, settingsStatus());
    else
        oled.printf("RTC:%s E:%u", rtcStatus, i2cErrors);
    oled.drawRect(0, 0, 128, 64, SH110X_WHITE);
    memcpy(oledFrame,oled.getBuffer(),sizeof(oledFrame));
    oledOffset=0;
}

// A frozen frame is sent in small, individually addressed pieces by the I2C owner.
// No complete-frame Wire transfer can block the next acquisition deadline.
void oledStep() {
    if(!oledReady)return;
    const uint64_t began=esp_timer_get_time();
    if(lastContrast!=appliedSettings().oled_contrast){
        Wire.beginTransmission(0x3C);Wire.write(0);Wire.write(0x81);Wire.write(appliedSettings().oled_contrast);
        if(Wire.endTransmission()==0)lastContrast=appliedSettings().oled_contrast;else ++i2cErrors;
    }else if(oledOffset<sizeof(oledFrame)){
        const uint8_t col=(oledOffset%128)+2;
        Wire.beginTransmission(0x3C);Wire.write(0);Wire.write(0xB0+oledOffset/128);
        Wire.write(col&15);Wire.write(0x10|(col>>4));
        bool ok=Wire.endTransmission()==0;
        if(ok){
            Wire.beginTransmission(0x3C);Wire.write(0x40);Wire.write(oledFrame+oledOffset,8);
            ok=Wire.endTransmission()==0;
        }
        if(ok){oledOffset+=8;if(oledOffset==sizeof(oledFrame))++oledFrames;}
        else{++i2cErrors;oledOffset=sizeof(oledFrame);}
    }
    const uint32_t elapsed=esp_timer_get_time()-began;
    if(elapsed>oledChunkUs)oledChunkUs=elapsed;
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

#if R1_SERVICE_TESTS
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
#else
void checkSdReadOnly() {
    sdPassed = false; // A failed re-test must replace the previous successful result.
    pinMode(pins::SD_CS, OUTPUT);
    digitalWrite(pins::SD_CS, HIGH);
    SPI.begin(pins::SD_SCK, pins::SD_MISO, pins::SD_MOSI, pins::SD_CS);
    if (SD.begin(pins::SD_CS, SPI, 10000000, "/sd", 5, false) && SD.cardType() != CARD_NONE) {
        File root = SD.open("/", FILE_READ);
        sdPassed = root && root.isDirectory();
        root.close();
    }
    sdStatus = sdPassed ? "READ" : "FAIL";
    Serial.printf("SD %s: mount/root read only; no test files or formatting.\n", sdStatus);
    SD.end();
}
#endif

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

bool runPanelAction(const char* verb, const char* argument, const char*& message) {
    if(!strcmp(verb,"BLE"))return r3BleCommand(argument,message);
#if R1_BENCHMARK
    if(!strcmp(verb,"BENCH"))return rateBenchmarkStart(argument,message,runPanelAction);
#endif
    if(!strcmp(verb,"STOP")&&!*argument)return recorder::stop(message);
    if(!strcmp(verb,"START")&&!*argument){
        if(!settingsReady()){message="Valid INA settings required";return false;}
        recording::SessionInfo info;info.config=appliedSettings();info.generation=settingsGeneration();info.revision=settingsRevision();
        if(!captureInaIdentity(info.manufacturer,info.device,info.adc)){message="INA identity/config readback failed";return false;}
        rtcStatus=pollRtc(false);info.utcUs=rtcUtcNow()*1000000;info.originUs=esp_timer_get_time();
        info.measuredHz=acquisitionStats().measuredHz;info.commit=R1_BUILD_COMMIT;info.dirty=R1_BUILD_DIRTY;info.version=R1_FIRMWARE_VERSION;
        info.id=recording::sessionId(info.utcUs,esp_random(),esp_random());
        return recorder::start(info,message);
    }
    if (!i2cReady) { message="I2C unavailable"; return false; }
    if (!strcmp(verb,"MEASURE") && !*argument) {
        inaStatus=testIna228();message=inaStatus;return latestIna228Reading().valid;
    }
    if (!strcmp(verb,"I2C") && !*argument) {
        scanI2c();message="I2C scan completed; inspect device count and errors";return i2cErrors==0;
    }
    if (!strcmp(verb,"SD") && !*argument) {
#if R1_SERVICE_TESTS
        message="SD command disabled in service build";return false;
#else
        sd_files::Request q;sd_files::Response r;
        sdPassed=sd_files::request(q,r);sdStatus=sdPassed?"READ":"FAIL";
        message=sdPassed?"SD mount/root read passed":"SD unavailable or file transfer active";return sdPassed;
#endif
    }
    if (!strcmp(verb,"EEPROM") && !*argument) {
        eepromStatus=checkEepromReadOnly();message=eepromStatus;return !strcmp(eepromStatus,"READ");
    }
    if (!strcmp(verb,"RTC") && !*argument) {
        rtcStatus=pollRtc();message=rtcStatus;return rtcUtcNow()!=0;
    }
    if (!strcmp(verb,"TIME")) {
        uint64_t epoch=0;const size_t n=strlen(argument);
        if(n!=10){message="Expected Unix seconds";return false;}
        for(size_t i=0;i<n;++i){if(argument[i]<'0'||argument[i]>'9'){message="Invalid UTC";return false;}epoch=epoch*10+argument[i]-'0';}
        const bool ok=panelSetRtcUtc(epoch);rtcStatus=pollRtc();
        message=ok?"RTC UTC written and verified":"RTC write/readback failed";return ok;
    }
    message="Unknown or unavailable test";return false;
}

void setup() {
#if !ARDUINO_USB_CDC_ON_BOOT
    Serial.setRxBufferSize(8192);
#endif
    Serial.begin(115200);
    delay(2000);
    Serial.println("\nR1-S3 PANEL v" R1_FIRMWARE_VERSION ": direct Wi-Fi + SD session recording");
    Serial.printf("RESET reason=%u\n",unsigned(esp_reset_reason()));
    Serial.println(R1_SERVICE_TESTS ? "SERVICE BUILD: SD/EEPROM write tests enabled."
                                 : "NORMAL BUILD: no SD/EEPROM test writes. Command: EEPROM DUMP");
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
#if R1_SERVICE_TESTS
    testSd();
    sdStatus = sdPassed ? "PASS" : "FAIL";
#else
    checkSdReadOnly();
#endif
    initOled();
#if R1_SERVICE_TESTS
    if (i2cReady && sdPassed) {
        eepromStatus = testEeprom();
        updateOled();
    } else {
        Serial.println("EEPROM SKIP: I2C and SD must pass first.");
    }
#else
    if (i2cReady) eepromStatus = checkEepromReadOnly();
#endif
    if (i2cReady) rtcStatus = pollRtc();
    if (i2cReady) { initSettings(); inaStatus = testIna228(); }
    local_input::begin();
    Serial.println("INPUT: encoder stub; no GPIO assigned or accessed.");
    const bool buffersReady = recording::prepareMemory(appliedSettings().queue_bytes);
    Serial.printf("BUFFER %s: PSRAM=%lu bytes, slots=%lu, sample=%u bytes, internal SD block=%lu bytes.\n",
                  buffersReady ? "PREPARED" : "FAIL",
                  static_cast<unsigned long>(recording::allocatedQueueBytes()),
                  static_cast<unsigned long>(recording::sampleQueue().capacity()),
                  static_cast<unsigned>(sizeof(recording::Sample)),
                  static_cast<unsigned long>(buffersReady ? recording::SD_BLOCK_BYTES : 0));
    Serial.println("BUFFER: acquisition -> PSRAM FIFO -> SD owner; recording starts only on START.");
    Serial.printf("LIVE history in PSRAM: %s\n",liveHistoryBegin()?"READY":"FAIL");
    sd_files::begin();
    r3BleBegin();
    panelBegin(runPanelAction);
    panelPublish({sdStatus,eepromStatus,rtcStatus,inaStatus,oledReady,i2cCount,i2cErrors,oledFrames,oledChunkUs});
    updateOled();
}

void loop() {
    static bool started=false;
    static uint32_t lastRtc=0,lastDisplay=0,lastPublish=0,publishedRevision=0;
    if(!started){vTaskPrioritySet(nullptr,3);acquisitionBegin();started=true;}
    setSettingsRecording(recorder::busy());
    acquisitionStep();
    rateBenchmarkStep();
    if(acquisitionIdle())panelPoll();
    inaStatus=acquisitionStatus();
    // Publish before optional OLED work consumes the remaining acquisition slack.
    // Otherwise a healthy 100 Hz acquisition can leave the UI snapshot stale for seconds.
    if((millis()-lastPublish>=500 || publishedRevision!=settingsRevision()) && acquisitionWorkBudgetUs()>300){
        panelPublish({sdStatus,eepromStatus,rtcStatus,inaStatus,oledReady,i2cCount,i2cErrors,oledFrames,oledChunkUs});
        lastPublish=millis();publishedRevision=settingsRevision();
    }
    if(i2cReady && millis()-lastRtc>=10000 && acquisitionWorkBudgetUs()>(Wire.getClock()>100000?1600:4500)){
        rtcStatus=pollRtc(false);lastRtc=millis();
    }
    if(oledOffset==sizeof(oledFrame) && millis()-lastDisplay>=1000/appliedSettings().display_hz && acquisitionWorkBudgetUs()>1500){
        updateOled();lastDisplay=millis();
    }
    if(acquisitionWorkBudgetUs()>(Wire.getClock()>100000?700:2600))oledStep();
    // Leave a tick for SD/idle whenever it fits. Near a deadline avoid adding a
    // whole tick to every trigger and conversion-ready check.
    if(acquisitionWorkBudgetUs()>1300)delay(1);
    else delayMicroseconds(40);
}
