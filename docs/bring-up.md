# Hardware bring-up

Status: 2026-09-06, HWTEST v0.6. Validate each subsystem before porting the original R1 application. Results below distinguish owner reports and captured logs from checks still pending.

## 1. Power and boot stability

- [ ] Record actual supply voltages, measurement conditions and common ground.
- [ ] Verify 3.3 V logic and no SDA/SCL pull-ups to 5 V against module schematics.
- [ ] Establish stable startup and reliable bootloader entry.

Initial voltages were reported as normal. Later measurements reported LDO 3.35 V, GPIO0 at 0 V with BOOT pressed and varying roughly 3.17–3.7 V released. Repeat measurements on a cool board using the same ground point, especially EN and GPIO0 during Connecting. Cleaning/heating preceded temporary improvement but does not establish a cause.

## 2. I²C scan

- [x] Scan SDA=8, SCL=9 at 100 kHz.
- [x] Observe `0x3C`, `0x40`, `0x50`, `0x68` repeatedly with zero bus errors.

ACK confirms an address response, not identity or complete functionality. Check module configuration if addresses change.

## 3. SD

- [x] Initialize SCK=12, MISO=13, MOSI=11, CS=10 at 10 MHz.
- [x] Create a unique file, write the known payload, close and remount.
- [x] Compare file size and every byte; check output files on a PC.
- [ ] Test explicit power-loss retention, long recordings and fault recovery.

The startup test selects the first unused `/r1s3_test_0000.txt` through `/r1s3_test_9999.txt`. It never formats the card or overwrites an existing file. Each boot creates another file; the payload retains its v0.2 identifier. Insert the card with power off.

Captured v0.2 result: 29818 MiB card, 10 MHz SPI, `/r1s3_test_0001.txt`, 39/39 bytes written, close/remount/exact readback PASS. Two subsequent I²C scans found all four addresses with no errors. See [serial log](sd-test-v0.2-serial.txt). Both supplied test files were also checked on a PC.

## 4. OLED

- [x] Identify a working driver: SH1106G 128×64, address `0x3C`.
- [x] Confirm readable image and 180° rotation (`setRotation(2)`).
- [x] Display actual subsystem results.

The v0.3 SSD1306 driver produced noise and unreadable characters. Switching to Adafruit SH110X 2.1.12 in v0.4 produced a readable image; the owner subsequently confirmed rotation. Library initialization alone is not a visual test.

## 5. EEPROM 24C32

- [x] Back up all 4096 bytes to a new `/eeprom_before_NNNN.bin` file on SD and verify it.
- [x] Write a sample pattern without crossing a page boundary, then verify it.
- [x] Restore original bytes and compare the entire 4096-byte image.
- [ ] Define the production calibration layout.

The owner confirmed EEP PASS. The implementation uses 16-bit memory addresses at I²C `0x50`. It skips writes unless SD backup verification succeeds and the last page `0x0FE0–0x0FFF` is uniformly FF or 00. Only 16 bytes `0x0FE0–0x0FEF` are modified. ACK polling allows up to 25 ms; restoration is attempted even after a failed pattern write. PASS requires full-image equality.

This tests a sample region, not every cell. It currently runs at startup as temporary bring-up code. Keep power connected until restoration finishes. On RESTORE FAIL, preserve the backup and stop further writes.

Address/page reference: [Microchip AT24C32/64 documentation](https://ww1.microchip.com/downloads/en/DeviceDoc/doc0336.pdf).

## 6. DS3231 RTC

- [x] Owner identified the RTC as DS3231.
- [x] Implement read-only register, BCD/calendar, 12/24-hour format, OSF/EOSC and temperature checks.
- [x] Owner reports SET TIME: tick check passes with OSF=1.
- [ ] Agree on UTC/local-time policy and set the clock once.
- [ ] Verify date/time accuracy and battery-backed retention with main power removed.

v0.6 reads registers `0x00–0x12` at `0x68` without writing time, alarms or control/status registers. Every 10 seconds it compares RTC advancement with millis, allowing 1.5 seconds for reading granularity. Display states: WAIT, TICK OK, SET TIME, TICK FAIL, BAD DATE, READ FAIL. TICK OK does not verify the actual date or battery. Century interpretation uses a 2000 base; timezone is not assigned.

Register reference: [DS3231 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds3231.pdf).

## 7. INA228

Only address ACK has been confirmed. All functional checks are pending:

- [ ] Read and validate Manufacturer ID and Device ID.
- [ ] With no substantial current, read VBUS, raw shunt voltage and die temperature.
- [ ] Compare voltage readings with a meter; record polarity, offset and agreed tolerances.
- [ ] Record shunt resistance and measurement range before computing/calibrating current.
- [ ] Exercise ALERT on GPIO14 using a controlled condition and verify assertion/clearing.

## Upload diagnosis and history

Early v0.1/v0.2 attempts encountered Windows error 433 (device missing) and Access denied (port unavailable/in use), followed by successful uploads. Separate No serial data / Wrong boot mode errors remain intermittent. Native USB enumeration is not confirmed. These are distinct observations, not one established diagnosis.

The default `esp32-s3-uart-manual` environment uses COM5, CDC=0, 115200 baud and esptool `no_reset` before/after upload. Close serial applications, hold BOOT, press/release RESET, release BOOT, then upload. Press RESET after a successful upload. Disabling esptool reset sequences does not guarantee that opening the port has no electrical effect through the driver/bridge circuit.

Builds passed with espressif32 6.12.0 / Arduino 2.0.17. Reliable entry into ROM download mode is still unproven. Next steps are EN/GPIO0 measurements during Connecting and inspection of USB–UART, BOOT/RESET and solder joints. Do not infer eFuse changes from an upload error.

## Recording evidence

For each test record the date, board revision/photos, firmware commit, platform versions, test parameters, expected and observed values, PASS/FAIL/NOT RUN and serial-log link. Historical Ukrainian notes are preserved in [the owner notes](uk/README.md); earlier pending statuses there are superseded by the results above.

After subsystem validation, restore R1 functions incrementally: measurements, calibration, CSV/SD buffering, OLED UI and Web UI.

## v0.7 browser time sync — 2026-09-07

After the owner swapped/reworked the USB–UART controllers, the connected board completed automatic UART upload with verified flash hashes and RTS reset. This establishes a successful test, not the root cause or long-term reliability of both boards.

HWTEST v0.7 adds explicit browser-sourced UTC synchronization over UART. The browser sent 2026-09-07T05:03:47Z; firmware verified calendar readback and OSF=0/EOSC=0. Subsequent serial checks showed the correct UTC date, tick PASS and all four I²C addresses with zero errors. A malformed TIME command was rejected. See [instructions](rtc-sync.md) and [serial evidence](rtc-sync-v0.7-serial.txt). Battery retention and precision clock accuracy remain untested.
