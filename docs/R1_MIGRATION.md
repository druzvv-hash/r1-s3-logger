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

### 2026-09-07 — P1 completed: byte contracts and synthetic compatibility corpus

Added CONFIG_SCHEMA.md, FILE_FORMAT.md, VIEWER_COMPATIBILITY.md and a 28-field typed registry. Defined explicit little-endian TLVs, two 1536-byte slots, CRC32 coverage, generation/commit rules and bounded validation. Added a host codec without device I/O. A torn-header test exposed incorrect unknown-version precedence; integrity/commit validation now precedes schema detection so a torn candidate retains the older valid slot.

Native CSV v1 includes the applied snapshot, raw and calibrated values, monotonic time/optional UTC, quality/gaps and sign-split integration. Plan revision 1.1 adds a META CRC for interrupted-file interpretation; END covers the complete preceding byte stream with SHA256 and uses final-row totals. The small reference decoder checks units/scales, raw/value consistency, integration, UTC anchors, checkpoint bounds/count/CRC and END integrity. It separates verified rows from unverified/partial tails; corruption fails explicitly.

Six native CSV cases, seven legacy CSV layouts/edge cases and config JSON/slot-hex golden files are synthetic public fixtures with hashes/expectations; eight donor source hashes preserve provenance without publishing donor code or private recordings. Git attributes preserve exact fixture bytes, including intentional legacy BOM/CRLF. Sixteen host tests passed, including every byte-prefix interruption of a candidate 1536-byte slot and bit corruption across header/used payload/footer. These are host format checks, not physical EEPROM power-cut tests. Both firmware build results and P0 bench evidence remain separate.

Verified R1 eight-column mapping is ready for P2. Pss_Wh semantics and short/headerless mapping remain explicitly unresolved rather than guessed; LYLI/R3 binary support remains P8. Current firmware does not yet save the new config schema or record native CSV. Next: P2 offline viewer core. [Ukrainian summary](uk/P0_P1_RESULTS.md).

### 2026-09-07 — P2 completed: offline viewer core

Added a local-only Python/SQLite viewer with bundled browser UI, exact P1 native validation, streaming checkpoints/digest, R1 named/Pss adapters and explicit short/headerless mapping. Disk-backed full-resolution rows feed bounded min/max previews and range statistics with actual-dt sign-split charge/energy; recorded Wh_net is separate. Invalid/gap rows never become zero or get bridged. Added per-run request token and local interface binding. No firmware/EEPROM changes.

Twenty-nine host tests passed; Chrome smoke/desktop/mobile visual checks passed. Read-only private archive run: 45 canonical + 25 Pss CSV imported, 14 layouts require confirmation, 2,870,946 rows total. Native synthetic 350,000-row/20,933,349-byte file verified with streaming reader; detailed timing/allocation/disk results in P2_VIEWER.md. Portable source ZIP requires Python 3.10+ and no additional runtime dependencies.

Plan v1.2 records Python/SQLite instead of the proposed TypeScript core to reuse verified contract semantics; standalone HTML, plugins/C-D markers, cross-part stitching, legacy export and binary adapters remain outside P2. Current support matrix is explicit. Next stage P3: actual firmware config lifecycle/transactional EEPROM persistence. See [viewer guide](../viewer/README.md), [P2 evidence](P2_VIEWER.md), [Ukrainian notes](uk/P2_VIEWER.md).

### 2026-09-07 — owner correction: preserve R5 features before P3

Owner pointed out that R5 already contained substantial useful work missing from the new interface. Re-read the primary R5 UI, marker/plugin APIs and battery/advanced-starter modules. Added R5_FEATURE_MIGRATION.md with concrete source evidence and P2.1a–c recovery/acceptance work; live/device-log portions retain P6 dependencies. P2 is the data-reading foundation, not a full R5 replacement. Plan revised to 1.3; P3 follows R5 recovery.

Screenshot also showed direct file:// opening of viewer/index.html, which cannot use this version's local service API. Added an explicit launcher explanation and disabled direct-file import rather than allowing Failed to fetch. This change does not yet implement the missing R5 features or standalone HTML operation.

### 2026-09-08 — P2.1a: restore R5 graph interactions

Viewer 0.2 restores selectable simultaneous channels on synchronized axes, persistent A/B and C/D markers, signed differences, independent full-resolution A/B statistics, wheel/drag zoom, pan and original-row tooltips. Added an indexed sample endpoint preserving source timestamps, line/quality and invalid samples. Existing importer/checksum behavior remains covered by tests. Thirty host tests and Chrome smoke plus dedicated pointer-gesture acceptance pass; desktop/mobile screenshots reviewed. Source ZIP updated to 0.2. Starter/battery analysis and plugins remain P2.1b/c, before P3.

### 2026-09-08 — owner redirects work to logger; P3 configuration deployed

Owner deferred remaining viewer features until real logger recordings exist. Plan 1.4 now proceeds P3 -> P4 -> P5, then resumes R5 analysis/plugins. CONFIG v0.12 adds generated 28-field C++ settings, exact P1 TLV/CRC storage, explicit draft/apply/save, INA register readback/rollback, applied engineering coefficients and display preferences. Added JSON import/export service tool and private backup-before-save helper. Boot never saves settings.

33 host tests pass, including executing firmware C++ with write-byte cuts/read failures, slot protection, ambiguity/future schemas and INA rollback faults. Normal and service builds pass; only normal uploaded on COM5. Physical A generation 1 -> B generation 2 (contrast only) -> A generation 3 (defaults restored) passed with preserved previous slot/reserve. Reboot restored generation 3 without changing EEPROM (CRC32 EBDAE9A1). Fresh pre-deployment backup matches P0 CRC32 8C31ED44. No physical mid-write power-cut or reference calibration performed. See P3_SETTINGS.md for commands, evidence and limitations. Production cadence/recording remain P4/P5.

### 2026-09-08 — device UI and explicit core separation requested

Owner requested actual device controls with the late R1 Fnirsi-style UI and UI/acquisition-storage separation by CPU core. Re-inspected STAB embedded HTML and the explicitly named FNIRSI viewer prototype without modifying donors. Added DEVICE_UI_AND_TASKS.md and plan 1.5: P4a device control/task ownership before production acquisition/P5 file controls. Core 0 hosts physical inputs/local menus/UI/web/frame rendering; core 1 hosts a prioritized acquisition owner and separate lower-priority SD writer. Shared I2C requires bounded OLED chunks; full 1024-byte/100 kHz transfer exceeds the 50 Hz sample period. Owner confirmed standalone buttons/encoder in addition to browser control, and microSD recording. Exact controls/GPIO remain pending; no unconfirmed input GPIO or old credentials assigned. Added local menu/edit/start/stop behavior and shared local/web state rules. No firmware/UI implementation or upload in this design clarification.

### 2026-09-08 — encoder selection and PSRAM/block-buffer foundation

Owner has no encoder yet and requested a no-hardware code stub, explicit use of PSRAM and reuse of the best FIFO/block-write ideas. Selected Bourns PEC11R-4220F-S0024 plus a 6 mm D-shaft knob; no GPIO assigned. Re-inspected R1 STAB, Jan21 S3 ring/output buffer, T2CAN PSRAM FIFO and R3 checked write/sync paths; exact hashes and decisions are in BUFFERING_AND_REUSE.md.

CONFIG v0.13 source adds semantic input actions with a no-GPIO stub, a 32-byte sample SPSC ring with atomic publication/overflow diagnostics, checked block-output staging and explicit PSRAM/internal-DMA allocations. Ordinary startup reserves the applied FIFO budget and an 8 KiB staging buffer. The diagnostic acquisition loop is unchanged; production tasks, UI and CSV/SD sink remain pending. No schema or EEPROM defaults changed.

35 host tests pass, including 400,000 concurrent FIFO transfers, counter wrap, backpressure, all 512 short-write boundaries and pool-allocation failures. Normal and service builds pass; normal static RAM 29,380 bytes, flash 423,837 bytes (heap buffers are additional). COM5 is enumerated but read-only status failed to open with Windows error 31, device not functioning. No upload was attempted after that failure; deployed v0.12 remains the last confirmed firmware. No new EEPROM writes, SD files, physical PSRAM stress or timing claims in this stage.

### 2026-09-08 — P4a test panel deployed

Owner rebooted the ESP and reported the previous upload succeeded, then requested
a usable UI for bench tests. COM5 responded with saved generation 3. PANEL v0.14 adds
the Fnirsi-style device panel: real U/I/P/temperature, bounded U/I graph, diagnostics,
UTC command and the complete P3 configuration lifecycle with JSON profiles.

Core 0 serves a bundled offline Wi-Fi AP interface; core 1 owns the diagnostic
hardware and executes queued commands. A loopback USB bridge provides the same UI
without changing the PC's network. Boot/revision checks reject stale commands.
Snapshot heartbeat/invalid samples prevent frozen or missing data from looking live.
The AP gets a newly generated NVS credential at first startup; no measurement profile
or EEPROM default changed. Encoder remains a no-GPIO stub.

Normal firmware uploaded and verified twice during development; only the final normal
build is left on the board. Normal static RAM 64,488 bytes, flash 917,573 bytes;
service compilation also passes, but is not deployed. Forty host tests and Chrome
fixture/live desktop/mobile acceptance pass. USB browser Apply changed only contrast
and restored it without Save. Physical INA/I2C/SD/EEPROM/RTC command tests passed;
wrong-boot Save was rejected. Before/after complete EEPROM reads are identical,
generation 3 / CRC32 EBDAE9A1. A representative live point was 3.608398 V / 0.454167 A;
this is transport evidence, not a new accuracy or calibration claim.

AP startup is reported by the ESP; phone-to-AP operation remains for owner verification.
Diagnostic conversions are still approximately 1 Hz; production acquisition, chunked
OLED scheduling, local menus and P5 session recording remain open. The offline viewer
was not changed. See [test panel](P4A_TEST_PANEL.md) and [owner guide](uk/TEST_PANEL.md).

### 2026-09-08 — P4b selectable cadence and 60 FPS preview

PANEL v0.15 replaces the approximately 1 Hz diagnostic loop with a timed
10/50/100 Hz triggered acquisition state machine. Core 1 remains the sole I2C owner;
SH1106 output is chunked and automatic RTC reads are quiet. Core 0 has independent
UART and HTTP tasks, with serialized owner commands and bounded PSRAM preview batches.
The recording FIFO/block staging remain reserved; P5 SD sessions are not connected.

Overview now offers actual measurement-frequency Apply, 30/60 FPS display and
10/30 second windows. Browser animation is separate from acquisition; no synthetic
samples are inserted. Configuration/schema/calibration and EEPROM defaults are unchanged.
Explicit tests/Apply/backup pause acquisition and mark a gap; ordinary live polling does not.

Bench windows at 10/50/100 Hz produced approximately 10.000/50.000/100.016 Hz from
delivered timestamps, zero invalid samples, zero missed periods and zero preview losses.
The real browser ran at 59.52 FPS with 100 Hz acquisition, then restored 50 Hz.
42 host tests and Chrome fixture/live responsive acceptance passed.
Before/after complete EEPROM images match generation 3 / CRC32 EBDAE9A1.
Normal firmware is deployed; service build only compiled. Mid-write UART disconnects
required upload retries; long-term transport reliability remains open.
See [implementation and measured limits](P4B_LIVE_ACQUISITION.md).

### 2026-09-08 — SD files available through the device panel

Owner requested file retrieval through the UI so recordings can be checked without
removing microSD. PANEL v0.16 adds folder pagination and original-name attachments
over the USB bridge and native AP. The storage task owns runtime read/mount/close on
core 1 at lower priority than acquisition. Core 0 handles transports, including a
separate port-81 download server so native downloads do not occupy the main UI server.
USB blocks carry checked session/size/offset/CRC32; incomplete transfers fail through
the HTTP content-length contract. No card writes, deletion or formatting were added.

Physical USB enumeration returned 163 root entries. Downloaded r1s3_test_0000.txt
and r1s3_test_0001.txt (39 bytes each), plus eeprom_before_0000.bin (4096 bytes), twice
each with identical bytes. The TXT contains the expected HWTEST v0.2 write/read line.
Chrome desktop/mobile acceptance used the actual download button and verified the
filename and bytes. Concurrent repeated 2048-byte SD reads at 100 Hz produced no
invalid samples or missed periods. Wrong-session, out-of-bounds and expired-session
requests were rejected; an abandoned directory released the card after 30 seconds.
Restored 50 Hz. EEPROM images before/after match generation 3 / CRC32 EBDAE9A1.

46 host tests and browser fixture/regression checks pass. Normal/service builds pass;
only normal is deployed. UART upload still needed a retry at 57600 baud. Native Wi-Fi
download code is built but phone-to-AP transfer remains unverified; the physical
acceptance above is USB. Large recordings/card-removal testing remain future checks.
Downloaded data and EEPROM copies stay in ignored/private directories.

The final directory page limit is six entries to keep long FAT filenames and hex
paths inside the bounded response. Production session recording remains P5. Its SD
writer must extend this owner and exclude file downloads before starting a recording;
the new recording admission hook is preparatory, not a complete recorder lock.
See [file-transfer contract](SD_DOWNLOADS.md) and [owner notes](uk/SD_FILES.md).

### 2026-09-08 — 3 A / 3 V load acceptance and panel scheduling fix

Owner connected a nominal 3 A / 3 V load and requested real tests. v0.16 acquisition
remained healthy, but optional OLED work could starve panel-state publication for
seconds at 100 Hz. PANEL v0.17 moves due publication before optional RTC/OLED work,
retaining acquisition priority and the slack guard. Normal/service builds pass;
normal v0.17 uploaded with verified hashes after one retry at 57600 baud.

Final 10/50/100 Hz windows captured 99/500/3000 consecutive samples over
10/10/30 seconds, with no invalid/missed samples, I2C errors or preview losses.
The 100 Hz means were 2.99877 V / 2.99953 A / 8.99489 W. A further 60-second phase
completed 40 identical 4096-byte USB downloads while counters advanced by 6069
valid samples, without missed periods, I2C errors or reboot. State age averaged
432 ms, maximum 708 ms. The real browser subsequently rendered at 59.67 FPS with
50 Hz acquisition. Original configuration restored, generation 3; no Save issued.

An initial full-Live archive plus repeated downloads exceeded shared UART delivery
capacity; this does not establish an acquisition failure. Final concurrent checks
use hardware counters, sampled tails and complete-file hashes. PSRAM FIFO-to-SD
session recording remains P5. Load setpoints are owner-reported, not independent
reference readings; no calibration was changed. See [complete acceptance and
limitations](LOAD_TEST_2026-09-08.md) and [owner notes](uk/LOAD_TEST_2026-09-08.md).

### 2026-09-08 — P5 session recording, verified files and rotation

Owner continued from load acceptance to Start/Stop and actual microSD sessions.
PANEL v0.18 connects the priority-3 core 1 acquisition producer to the existing
32-byte PSRAM SPSC FIFO. The same priority-1 SD owner handles serialization,
8 KiB checked writes, timed checkpoint/sync, finalization and rotation. Core 0
retains UI/transports; settings/diagnostics/time and downloads reject during a
recording without pausing acquisition. The encoder remains a no-GPIO stub.

Files carry frozen configuration/TLV hash, generation, actual INA identity/ADC,
UTC uncertainty, firmware provenance, raw samples, gap/invalid flags, sign-split
Wh/Ah, CRC checkpoints and SHA END. Unique .part files become .csv only after
checked sync/close/rename; rotation links complete-file hashes and preserves totals.
Stopped queue resizing retains old pools on allocation failure. Errors preserve
partial files and diagnostics rather than silently overwriting/retrying data.

Physical browser Start/Stop/download at 50 Hz produced 537 verified rows. A 100 Hz
run produced 5878 rows across two rotation files (1,235,957 bytes), with no missed,
invalid or gap rows. FIFO high-water 35/2048 absorbed a 94.627 ms maximum write;
maximum sync was 64.901 ms. Full-file downloads, checksums, viewer import and the
rotation-boundary integral passed. Desktop rendering averaged 59.90 FPS.

The initial 10 Hz profile exposed its too-short 40 ms gap threshold. Quick rate
changes now raise the threshold to at least two periods when necessary, and START
refuses a threshold no longer than one period. Mobile 10 Hz recording with 200 ms
gap allowance produced 68 rows and positive energy. Original 50 Hz configuration
and saved generation 3 restored, with no Save or calibration/clock changes.

51 host tests and normal/service builds pass. Short-write/sync failures and
interrupted-file recovery are tested on host; physical power cuts, card full/removal
and long-duration operation remain open. See [P5 behavior and acceptance](P5_RECORDING.md)
and [owner controls](uk/RECORDING.md). Remaining R5 viewer features and local menus
continue according to the staged plan; there are now real logger files to use.

### 2026-09-08 — Readable recording dates and owner's first session review

PANEL v0.19 replaces the Unix-seconds filename prefix with the RTC UTC date and
time (`YYYY-MM-DD_HH-MM-SSZ`), retaining random uniqueness and part numbering.
The file list shows browser-local start times for both naming generations;
existing SD files and their metadata/checksums remain unchanged.

Downloaded the owner's latest completed session
`r1s3_1788864937_4ee24d5b_9ebc8459_0000.csv` in full (615,956 bytes).
Its anchor is 2026-09-08 10:55:37 UTC / 12:55:37 Prague. Both contract decoder and
production viewer report verified clean: 2763 rows, zero unverified rows, sequence
losses or quality flags. First-to-last duration is 55.239999 s at 50.0000009 Hz;
intervals range from 18.995 to 21.004 ms (median 20 ms). Initial 15 s are near
3.00 A / 3.02 V; later values change up to 4.79375 A / 6.146484375 V and include
near-zero intervals. Net energy is 0.149848712757469 Wh; net charge is
0.042256051443865815 Ah. Current minimum is -0.04375 A; no automatic zero correction
or reference-accuracy claim is made. Local evidence is in ignored
`data/recording-tests/user-latest/` (CSV, analysis JSON and dated-list screenshots).

Five serializer/reader tests and browser filename/date checks pass, including UTC,
leap day, dates after 2038, unknown time and old names. Actual desktop/mobile file
lists display the owner's start as 12:55:37 Prague without changing the SD name.
The owner's file also opens in the real viewer browser with both plots rendered.
Normal build and deployed v0.19 smoke pass: 204 rows / 53,260 bytes in
`r1s3_2026-09-08_11-24-46Z_caf53f56_c7124bb8_0000.csv`, complete download and verified
viewer import. Filename and metadata UTC anchors agree; panel and file versions
both report 0.19 from clean commit `18209d9ea69ebc7556a473d875021421eec19728`.
The board is READY at the original 50 Hz, exact applied configuration and generation
3 unchanged. USB flashing remains intermittent (connection and mid-write failures);
the successful final write used extended reset timing and 38,400 baud with flash
hash verification. No permanent transport fix is claimed.

### 2026-09-08 — P6a direct Wi-Fi control and native download acceptance

PANEL v0.20 adds a Wi-Fi tab with connection instructions, explicit USB/native
transport labels and a cached associated-station count. Core 0 samples the count;
acquisition/SD ownership, saved configuration, calibration and clock are unchanged.
Six panel host tests, browser fixture/regression checks and the normal build pass.
Clean firmware commit `a7777f1ac1f2e44fe20fd8e89182a54b6ae8645b` is deployed.

With the USB bridge stopped, the PC joined the physical ESP AP and ran Chrome
at a 390 x 844 viewport. Native HTTP reported `wifi` and one associated client.
Browser Start, closing the browser for ten seconds, reopening and Stop passed;
512 rows were added during the closed-browser interval without a boot/session change.
The completed file is
`r1s3_2026-09-08_12-24-04Z_49c39e42_ce9d31b8_0000.csv`: 541 rows, 139,320 bytes,
10.800001 s, 50 Hz, intervals 19.831–20.150 ms (median 20 ms). No missed/invalid
samples, sequence losses, quality flags or FIFO overflows; FIFO high-water was 2.
Contract CRC/SHA/raw-value/integration checks and production viewer import pass,
with no unverified tail. Full-file SHA-256 is
`42c9f60d724044c6e3a2a3de90ca1753cda01eea4aba1253829eeecd2b89d0fb`.

The browser downloaded that file through native port 81 with the correct name and
length. A second download of the owner's previously verified 615,956-byte recording
matched its local SHA-256; state replied after 207 ms while the transfer completed
after 2.72 s. The original PC Wi-Fi profile was restored and the temporary profile
removed. USB panel restarted; device READY at 50 Hz, exact configuration/AP password
and saved generation 3 unchanged. Private reports/screenshots/CSV remain under
ignored `data/wifi-tests/`.

This validates the actual PC-to-AP radio path, not physical Android or power-only
supply operation. Android reconnect/download, Wi-Fi-off operation, local controls
and P7 long-duration/fault tests remain open. USB upload required retries and a
confirmed ROM DOWNLOAD response before the final hash-verified 38,400-baud write;
no permanent USB repair is claimed. See [P6 evidence](P6_WIFI.md) and
[owner connection steps](uk/WIFI.md).

### 2026-09-08 — SD explorer and measured rate/noise limits

PANEL v0.21 adds a bounded scrolling SD table with sticky columns, search, sorting,
file-type filters, breadcrumbs and automatic reading of every directory page.
Cancellation, navigation, download and START release the active directory cursor.
The browser fixture passes with 601 entries, hostile-looking literal filenames,
desktop/mobile layouts and downloads. Physical Chrome acceptance reads all 164
root entries, scrolls/searches the complete list and downloads the expected 39-byte
`r1s3_test_0000.txt`. No existing card files were removed or renamed.

An explicitly selected benchmark build varies frequency, ADC conversion time and
I2C speed, independently stops timed tests and restores the preceding volatile
profile. EEPROM writes are disabled in that build; normal validation still offers
10/50/100 Hz. A bounded private UART diagnostic log and reset-reason reporting were
added. Normal and benchmark builds, six panel host tests, four settings firmware
tests and browser regression/Explorer fixtures pass.

The full sweep covers requested 100–1000 Hz, CT codes 0/2/3/5 and 100/400 kHz I2C.
All 31 experiment artifacts (43,779,187 bytes, 209,623 checkpoint-verified rows)
were downloaded through native Wi-Fi and passed both readers' integrity/semantic
checks. Overload cases retain correctly marked sequence gaps. The initial unexpected
100 Hz reboot, which the owner confirms was not manual, left an interrupted PART
with 13,808 verified rows. Its cause is unresolved; the subsequent sweep did not
reproduce it. The artifact remains on SD and PC.

The unchanged ADC/100 kHz profile passed a subsequent 300-second 100 Hz file with
30,031 rows and no sequence loss. Fast ADC/400 kHz reached a verified 330.031 Hz
for 90 seconds (29,615 rows), but state/OLED publication starved; 350 Hz already
lost sequences. A 200 Hz / 150 us-per-channel / 400 kHz candidate passed 120 seconds
and 23,959 rows without in-file gaps. USB live preview sometimes lagged even with
60 FPS animation. A separate direct-Wi-Fi browser test produced 5,957 clean rows,
fresh preview in all 28 observed RUNNING snapshots, about 59.87 FPS and 46 OLED
frames, without lost periods or a reboot. Faster ADC increases observed dispersion;
no faster production preset or calibration change was silently adopted.

Normal v0.21 is deployed from clean commit
`0781a4047c34cd411e33868540fb15e0a129398b`. Its post-upload smoke file
`r1s3_2026-09-08_13-51-24Z_aca2c445_8a382472_0000.csv` has 628 rows, 134,223 bytes,
99.999234 Hz and no sequence gaps/invalid rows; CRC/SHA/raw/integration checks and
ordinary viewer import pass. File metadata confirms the clean firmware commit.
The logger is READY at the exact owner's original volatile 100 Hz configuration,
I2C 100 kHz, saved generation 3 unchanged. No Save or clock adjustment was issued.
The original PC Wi-Fi network is restored; the USB panel is running again.

UART uploading remains intermittent. Both completed v0.21 writes used ROM/no-stub
at 38,400 baud with flash hash verification; the final one required a separately
confirmed DOWNLOAD entry after automatic connection failures. No permanent USB
repair or long-duration stability claim is made. See the
[complete results and next preset decision](RATE_BENCHMARK.md) and
[owner notes](uk/RATE_TESTS_2026-09-08.md). P7 endurance/fault work remains open.

### 2026-09-08 — integer 1–300 Hz range and responsive high-rate UI

Owner selected 1–300 Hz with presets 1/5/10/25/50/100/150/200/250/300 and arbitrary
integer entry. PANEL v0.22 implements the shared field bounds in firmware,
EEPROM/JSON tools, device panel and the existing native CSV reader. ADC profiles
are visible before Apply: 1052 µs/channel through 100 Hz, 150 µs through 200 Hz,
50 µs above 200 Hz; averaging off, I2C 400 kHz above 100 Hz. Shunt, gains, offsets,
polarity and range are preserved. Apply never saves automatically.

Config v1.1 uses the same 28 TLVs; old-compatible values keep byte-identical v1.0
encoding, extended values advertise minor 1 for rollback write protection. The
gap limit can reach two seconds for 1 Hz integration. Existing custom integration
limits remain readable; quick profiles raise the limit to at least two periods.

Core 0 now formats state JSON from a bounded owner snapshot. Core 1 uses safe
conversion-wait intervals for chunked OLED/RTC work and avoids a mandatory tick
between every acquisition phase. PSRAM FIFO/block SD recording are unchanged.
High-rate Wi-Fi preview catches up with additional batches. USB resynchronizes
to recent preview windows when bandwidth is insufficient and marks those gaps;
it never discards the recorded raw samples.

Host suite: 54 tests pass, including all 300 integer profiles, C++/Python/JS
encoding, persistence failure injection, legacy fixtures and extended JSON
versions. Browser fixtures pass preset/manual input, 137/1/300 Hz application,
validation, polling draft preservation, recording lock and mobile layout. Normal
and benchmark builds pass; only normal firmware was installed for acceptance.

Hardware: 15 CSV files / 60,759 rows / 12,674,362 bytes pass both independent
reader paths, including integrity, raw values and integration. Every requested
preset plus 37/137/299 Hz produced no lost/invalid rows. A 121-second 300 Hz file
has 36,405 rows, 300.029897 Hz, no FIFO overflow, maximum queue 42, 424 OLED frames
and fresh owner state in all 109 observations. During the long run, the revised
USB preview was fresh in all 76 RUNNING observations, about 59.83 FPS.

The first native Wi-Fi 300 Hz browser run exposed preview lag despite a clean
8,232-row file; delivery was adjusted afterward. Acquisition firmware `d52defe`
was flashed with hash verification. The final embedded panel build `ab1e7d0`
awaits physical UART reconnection: COM5 remained present but two ROM-entry
attempts received no bytes and made no Flash writes. Completed tests restored
the exact initial volatile 100 Hz profile and left EEPROM generation 3 unchanged;
state after the later reset attempts needs re-verification. See
[measurement-rate implementation and results](MEASUREMENT_RATES.md) and
[owner instructions](uk/MEASUREMENT_RATES.md). Prior USB instability and P7
endurance work remain open.
