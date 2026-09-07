# R1 migration journal

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
