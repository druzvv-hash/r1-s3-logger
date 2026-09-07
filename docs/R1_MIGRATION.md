# R1 migration journal

Roadmap: [R1-S3 engineering plan](R1_S3_PLAN.md), with an [owner-facing Ukrainian edition](uk/R1_S3_PLAN.md). The P0-P8 stages in that plan supersede the preliminary ordering below.

This is the continuing record of the R1-to-R1-S3 migration. Update it with each completed stage, test evidence, decisions and unresolved issues. Main documentation and code are English; personal Ukrainian notes live in `docs/uk/`.

## Baseline and scope

The strongest recovered OLED R1 source candidate is `Projects/bekup/main21_12_3STAB.cpp` in the owner's `Logger_Analysis` archive. It is identical to `Projects/Temp/main_R1.cpp` and the archived `esp_clamp_logger/src/main.cpp` (SHA-256 prefix `1d0edfc54f64`). This establishes source identity, not proof of the last deployed working binary.

The separate TFT branch is not the OLED baseline. See [legacy analysis](legacy-r1-analysis.md) for exact evidence, viewer candidates and limitations. Legacy source has not been copied into the current firmware.

| R1 subsystem | R1-S3 destination / decision |
|---|---|
| ESP32, INA226, separate ADC voltage input | ESP32-S3, INA228; validate voltage sensing topology before replacing the old voltage channel |
| SSD1306 OLED | Confirmed SH1106G 128x64, rotation 180 degrees |
| Preferences calibration | Define versioned 24C32 storage with integrity checking; do not reuse old coefficients |
| DS3231 clock | Store UTC; explicit time-setting command, no automatic build-time reset |
| CSV and buffered SD writer | Preserve useful column semantics; fix overwrite, short-write and timing problems |
| HTTP/WebSocket control | Port after measurement and storage validation |
| Browser viewer | Repair metadata parsing, column mapping, timestamps and peak preservation before acceptance |

Original CSV columns: `timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd`. A documented version/timezone policy and parser fixtures must precede production changes. Historical local timestamps need explicit interpretation.

## Hardware validation status

| Item | Evidence / current limit |
|---|---|
| Flash / PSRAM | 32 MB flash and approximately 16 MB PSRAM detected; stress test pending |
| I2C GPIO8/9 | Repeated ACK at 0x3C, 0x40, 0x50, 0x68 without bus errors |
| SD GPIO10/11/12/13 | 10 MHz write, close, remount and exact readback passed; files checked on PC |
| OLED | Owner confirmed readable image and 180-degree rotation |
| 24C32 | Backup, sample write, restore and full-image comparison passed |
| DS3231 | Browser UTC sync and ticking verified; owner-reported power disconnection followed by correct time and OSF=0 |
| INA228 / GPIO14 | HWTEST v0.8: identity and three fresh ADC samples passed; external comparison and active ALERT pending |
| Upload | Automatic UART uploads succeeded after owner swapped/reworked USB-UART controllers; exact previous fault unproven |

RTC retention evidence on 2026-09-07: set to `05:03:47Z`; after the owner disconnected/reconnected main power, read-only capture showed `05:08:47Z`, `05:08:57Z`, `05:09:07Z`, OSF=0, EOSC=0 and tick PASS. PC comparison was approximately 1.25 seconds later. Outage duration was not measured; long-term drift has not been characterized.

## Migration stages

- [x] Recover and compare legacy R1 and viewer source candidates.
- [x] Establish PlatformIO/Arduino scaffold, fixed GPIO map and bilingual README.
- [x] Test I2C, SD, OLED and EEPROM sample/restore behavior.
- [x] Set RTC explicitly from browser UTC and check retention after disconnection.
- [x] Validate INA228 identity and fresh ADC readings.
- [ ] Compare INA228 voltage readings with a known input and meter.
- [x] Record owner-confirmed shunt nameplate: 60 mV / 400 A = 150 microohms.
- [ ] Confirm sensing wiring, polarity, load conditions and required current range.
- [ ] Test ALERT assertion and clearing on GPIO14.
- [ ] Implement measurement error reporting, fresh-sample timing and calibration.
- [ ] Define EEPROM calibration schema, checksum/version and recovery behavior.
- [ ] Port recording state machine and CSV writer with unique filenames, checked writes and measured elapsed-time integration.
- [ ] Port OLED controls and network interface.
- [ ] Repair viewer compatibility and test historical/new CSV fixtures.
- [ ] Run sustained recording, power interruption and storage-failure tests.

## INA228 v0.8 test contract

Reads manufacturer `0x5449` and device family `0x228` at I2C address `0x40`; any revision nibble is reported. Only after matching identity, temporarily writes ADC_CONFIG `0x7B68`: one triggered conversion of bus voltage, shunt voltage and temperature, 1052 us per channel, averaging 1. Waits up to 1 second for fresh CNVRF, allowing the existing conversion delay. Restores and verifies the original ADC_CONFIG even after conversion/read failure; restoration failure blocks further INA tests until reboot.

CONFIG and shunt calibration are preserved. Signed shunt/temperature decoding has compile-time boundary checks. `ADC OK` means communication and a fresh sample succeeded, not calibrated accuracy. GPIO14 is read passively without enabling an internal pull-up; its level does not prove ALERT operation or correct wiring.

This is not a fully read-only test: reading DIAG_ALRT clears ready/latched flags, and triggered operation interrupts continuous accumulation. Do not use its energy/charge registers as recording data. Current and power are intentionally not calculated until the actual shunt is specified.

Reference: [TI INA228 datasheet](https://www.ti.com/lit/ds/symlink/ina228.pdf), register map and conversion-ready behavior.

## Dated journal

### 2026-09-07 — comparison with owner-reported clamp reading

On HWTEST v0.9 (commit `27a2c40`), the owner reported 0.94 A after zeroing the clamp meter, a 1 A bench-supply current limit, and sense wires connected to IN+ / IN-. Read-only COM5 capture at 05:44:13Z through 05:44:43Z produced four fresh ADC OK samples:

| UTC | VSHUNT (microvolts) | Nominal current (A) | VBUS (V) |
|---|---:|---:|---:|
| 05:44:13 | 27.5000 | +0.1833 | 0.000000 |
| 05:44:23 | 31.5625 | +0.2104 | 0.000000 |
| 05:44:33 | 35.3125 | +0.2354 | 0.000000 |
| 05:44:43 | 19.3750 | +0.1292 | 0.016211 |

At 0.94 A, the nominal 150-microohm shunt would develop 141 microvolts. The observed readings disagree substantially. The clamp reading is owner-reported, not an independently calibrated reference, and was not continuously captured alongside these samples. I2C had zero errors, identity matched and ADC_CONFIG restoration passed. No firmware changes or calibration corrections were made during this capture. Wiring, actual differential voltage and module circuitry must be checked before choosing a gain correction. See [serial evidence](ina228-v0.9-clamp-comparison.txt).

### 2026-09-07 — baseline recovery

Recorded recovered R1 source and viewer compatibility findings in commit `5fe8ccf`. Legacy calibration values are historical evidence only. In particular, viewer variants do not consistently parse the existing eight-column CSV or leading metadata comments.

### 2026-09-07 — INA228 bring-up

HWTEST v0.8 built successfully with compile-time signed decoding checks. Automatic UART upload on COM5 succeeded with verified flash hashes and RTS reset. Three samples at 05:29:16Z, 05:29:26Z and 05:29:36Z returned manufacturer `0x5449`, device `0x2281`, CONFIG `0x0000`, original/restored ADC_CONFIG `0xFB68`, DIAG `0x0003` and `ADC OK`.

Observed VBUS: 0 / 0.007227 / 0 V; VSHUNT: 3.125 / 1.250 / 3.750 microvolts; die temperature: 25.719 / 25.758 / 25.773 degrees C. These are uncalibrated observations with input wiring not yet confirmed, not an offset or accuracy specification. GPIO14 read LOW in all samples with no internal pull-up enabled; check external pull-up/wiring and exercise ALERT before declaring it operational. I2C remained four devices/zero errors; RTC tick checks passed with OSF=0 and EOSC=0.

See [captured serial evidence](ina228-v0.8-serial.txt). Next physical acceptance requires known input voltage and a meter comparison, followed by shunt details and a controlled ALERT test.

For future entries include firmware commit/version, test setup, observed results, evidence link and remaining limits. Never mark a stage passed solely because it compiled or its I2C address acknowledged.

### 2026-09-07 — nominal shunt current (HWTEST v0.9)

Owner reports the shunt is connected and rated 60 mV / 400 A. Nominal resistance is 0.00015 ohm (150 microohms), configured in `firmware/include/shunt_config.h`. Compute signed current directly as VSHUNT_uV / 150, without modifying INA228 SHUNT_CAL or EEPROM. No zero suppression, offset subtraction or old R1 gain is applied. Invalid sample encoding or a shunt ADC rail withholds current output.

The observed ADCRANGE=0 (+/-163.84 mV) covers the 60 mV nameplate drop. The narrow range (+/-40.96 mV) would clip before 400 A, so the test reports a warning if it encounters that range. ADC range is not the shunt's allowable current rating. Actual shunt tolerance, temperature coefficient, input wiring, VBUS connection and load conditions remain unverified. Positive current means positive IN+ minus IN- voltage, not yet an agreed charge/discharge convention.

Compile-time checks cover zero, +1 A and +/-400 A conversion. Build and automatic COM5 upload passed. Two captured fresh samples at 05:37:03Z / 05:37:13Z reported VSHUNT 55.625 / 27.500 microvolts, I_nominal +0.3708 / +0.1833 A, VBUS 0.033594 / 0.030469 V and ADC OK. Load and VBUS wiring have not yet been confirmed, so these values are observations, not verified real current or a zero-offset measurement. No zero correction was applied. I2C had zero errors and RTC ticking passed. See [serial evidence](ina228-v0.9-serial.txt); calibrated-current acceptance remains open.

### 2026-09-07 — module photos and onboard shunt

Inspected the owner's synced photos `MVIMG_20260907_125411.jpg` (front) and `MVIMG_20260907_125421.jpg` (back). The module has Adafruit/STEMMA QT markings and a populated R015 resistor: 15 milliohms, consistent with the [Adafruit INA228 product](https://www.adafruit.com/product/5832). The two outer sensing pins appear connected; the middle VBUS pin appears unused and its rear jumper appears open. Electrical continuity and the entire external circuit are not established by these photos.

The populated onboard shunt loads the external Kelvin/sense wiring. Sense-wire and connector resistance in series with the onboard 15-milliohm resistor can form a divider, plausibly explaining a large low reading. Simple ideal parallel connection of 15 milliohms and 150 microohms alone would change effective resistance by only about 1 percent; it does not explain the observed several-fold discrepancy. Lead/contact resistance must be included in that hypothesis.

Next hardware step: with power removed, remove/isolate R015 for external-shunt-only sensing; leave its pads open, never bridge them. Retain IN+/IN- sensing connections to the external shunt and keep load current in the external power circuit. Repeat measurement against the clamp reading before applying any software gain correction. No hardware change has yet been confirmed.

VBUS is a separate input. Confirm high-side versus low-side wiring before deciding whether to connect it separately or close the VIN+-VBUS jumper. See [Adafruit pinouts](https://learn.adafruit.com/adafruit-ina228-i2c-power-monitor/pinouts). Near-zero VBUS readings do not establish supply failure when this input is unconnected. Photos remain in the owner's photo folder and were not published to this repository.

### 2026-09-07 — external shunt only, after R015 removal

Owner reports R015 removed and a 1 A load applied. Read-only COM5 capture using unchanged HWTEST v0.9 produced:

| RTC UTC | VSHUNT (microvolts) | Nominal current (A) | Die temperature (C) |
|---|---:|---:|---:|
| 11:05:12 | 143.7500 | +0.9583 | 45.625 |
| 11:05:22 | 144.3750 | +0.9625 | 43.812 |
| 11:05:32 | 143.4375 | +0.9563 | 42.102 |

All three samples returned ADC OK, correct identity and verified ADC_CONFIG restoration; I2C errors remained zero. Current is now approximately 0.959 A and materially more stable than the previous 0.129–0.235 A readings. The improvement after removing R015 supports onboard-shunt/sense-lead loading as the previous fault mechanism. Exact lead resistance has not been measured. The load is owner-reported; the earlier 0.94 A clamp value was not recaptured simultaneously, so this is not an accuracy calibration.

Die temperature fell during the capture, consistent with cooling after recent soldering; allow thermal settling before a zero/gain check. VBUS remained 0.081–0.158 V with its connection unconfirmed, and ALERT stayed LOW passively. These two checks remain open. No gain/offset changes or firmware upload were performed. Next: thermally settled zero-current reading with electronics powered, followed by comparison against a simultaneous known current. See [serial evidence](ina228-v0.9-external-shunt-only.txt).

### 2026-09-07 — owner-confirmed zero-load check

After the owner indicated the load was switched off while electronics remained powered, unchanged HWTEST v0.9 reported three fresh ADC OK samples:

| RTC UTC | VSHUNT (microvolts) | Nominal current (A) | Die temperature (C) |
|---|---:|---:|---:|
| 11:07:12 | -3.7500 | -0.0250 | 31.922 |
| 11:07:22 | +1.2500 | +0.0083 | 31.258 |
| 11:07:32 | -0.3125 | -0.0021 | 30.711 |

The readings are near zero and include both signs; the temperature is still falling. Three single-conversion samples during thermal settling do not establish a stable offset, noise specification or calibration coefficient. No zero subtraction, deadband, gain correction or EEPROM write was applied. Manufacturer/device identity and ADC_CONFIG restoration passed; all four I2C addresses responded with zero bus errors. Serial capture was read-only and the port was released. See [serial evidence](ina228-v0.9-zero-current.txt).

Next: confirm whether the external shunt is installed in the positive or negative power lead before wiring VBUS, then compare bus voltage with a meter. A longer thermally settled zero-current sample set remains necessary before deciding on offset calibration.

### 2026-09-07 — low-side wiring and VBUS capture

Owner reported moving the shunt into the negative lead and confirmed completion after instructions to connect IN- and module GND to supply negative, IN+ to the load-side shunt sense contact, and VBUS to supply positive, leaving the VIN+-VBUS jumper open. Actual wiring has not been independently inspected.

Unchanged HWTEST v0.9, read-only COM5 capture:

| RTC UTC | VBUS (V) | VSHUNT (microvolts) | Nominal current (A) | Die temperature (C) |
|---|---:|---:|---:|---:|
| 12:31:12 | 0.301758 | 149.3750 | +0.9958 | 39.070 |
| 12:31:22 | 0.297266 | 149.6875 | +0.9979 | 37.367 |
| 12:31:32 | 0.296875 | 151.8750 | +1.0125 | 35.992 |

All three conversions returned ADC OK, correct identity and verified ADC_CONFIG restoration. I2C errors were zero. Nominal current is approximately 1 A; VBUS is approximately 0.30 V, but actual bench-supply output voltage and simultaneous reference current remain to be reported. Do not mark voltage accuracy as passed without that comparison. ALERT remains LOW and untested; die temperature is still changing. No calibration or firmware modifications were made. See [serial evidence](ina228-v0.9-low-side-vbus.txt).

### 2026-09-07 — OLED live measurements (HWTEST v0.10)

Owner reports actual bench-supply voltage 0.43 V, versus the previous INA228 capture near 0.30 V. Voltage comparison remains unresolved: the measurements were not captured simultaneously at identical terminals. No gain correction was applied.

OLED now displays VBUS in volts and signed nominal current in amperes in double-size text, die temperature above, and alternating SD/EEPROM and RTC/I2C status below. Retains SH1106G 128x64 and rotation 180 degrees. Measurement/display refresh is approximately 1 second; I2C scan and RTC remain at 10 seconds. The ADC test retains its triggered-conversion/restore behavior and serial diagnostics. Invalid reads, identity errors, ADC rails and restore failures invalidate the display snapshot, replacing numeric readings with dashes and an error status. Current remains based on the nominal 150-microohm shunt; no calibration changes.

Build and automatic UART upload passed with verified flash hashes. Post-upload capture contains 11 ADC OK results, nominal current 0.9521–1.0500 A, VBUS 0.294336–0.298047 V and zero I2C errors; RTC tick passed. See [serial evidence](ina228-v0.10-oled-serial.txt). Screen geometry was checked against the 128x64 character grid; physical visual confirmation is pending from the owner. Two-decimal formatting above 1000 A keeps ADC-range values within the screen width; this is formatting, not an approved operating current.

### 2026-09-07 — owner-reported XDM1241 comparison, approximately 4 A

Owner confirmed readable OLED measurements and reported the following operating point on HWTEST v0.10:

| Instrument | Voltage (V) | Current (A) |
|---|---:|---:|
| Bench supply display | 5.37 | 4.000 |
| XDM1241 multimeter | 4.9035 | Not reported |
| R1-S3 display | 4.906 | 3.995 |

R1-S3 minus XDM1241 is +0.0025 V (+0.0510% relative to the meter reading). R1-S3 minus the supply current display is -0.005 A (-0.125%). These are differences at one owner-reported point, not calibrated accuracy specifications; current has not been independently compared with the XDM1241.

The supply voltage display exceeds the meter by 0.4665 V. Measurement locations, lead/contact drops and supply display accuracy must be distinguished before attributing that difference to one cause. The agreement with XDM1241 supports the INA228 voltage reading at this point; no gain/offset correction was introduced. Multi-point and zero-current checks remain pending for calibration acceptance.

### 2026-09-07 — implementation roadmap v1.0

Created `R1_S3_PLAN.md` and `uk/R1_S3_PLAN.md` after reviewing the recovered R1/Plotly analysis, current HWTEST and EEPROM test, R3 configuration/FILELOG architecture, and two LYLI binary reader/type definitions plus their checksum implementation. The plan chooses raw plus engineering-value self-contained CSV first, versioned configuration with A/B EEPROM, explicit runtime/persisted settings, and a shared viewer model with separate format adapters. R1/R1-S3 compatibility precedes the new recorder; LYLI/R3 support follows with matched writer fixtures.

This is a planning/documentation milestone only. No firmware changes, device upload, EEPROM writes or alterations to legacy source were performed. Next implementation stage: P0 baseline preservation and diagnostic separation, then P1 exact schemas and compatibility fixtures. Earlier hardware logs remain historical evidence; calibrated-current accuracy, active ALERT and sustained recording are not marked complete.

### 2026-09-07 — P0 completed: baseline preservation and storage test separation

Tagged known bench commit de37e6d as `hwtest-v0.10`; saved its firmware/ELF/config and hashes privately. BASE v0.11 separates ordinary SD root/EEPROM read checks from the explicit `esp32-s3-service` write-test build. Ordinary ELF contains neither testSd nor testEeprom symbols. Normal/service builds passed; only normal was uploaded, automatically over COM5 with verified flash hashes.

Saved a private 4096-byte EEPROM backup from two matching dump requests, each itself double-read by firmware. CRC32 8C31ED44, SHA256 78c5017e9cac1ce1807b838a3c168c10e8ab1776354b7e68abdaaa1b10cd8545. Post-reset capture repeats the same CRC, SD READ, EEPROM READ, four I2C ACKs/no errors, INA228 ADC OK and RTC tick PASS. No EEPROM settings written or new calibration applied. [P0 details](P0_BASELINE.md), [serial evidence](p0-v0.11-serial.txt). ALERT functionality and sustained timing remain unverified.
