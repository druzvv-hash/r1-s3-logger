# Current memory entry point

## 2026-09-22 — shared CAN workspace

0.36-can-live-dev deployed via native COM9 to verified active app1 at 0x490000;
READY, generation 6. CAN tab and `/can`, preserving 0.35 OTA/timezone. Canonical
assets: ../GLL CANBox/workspace; contract: ../GLL CANBox/docs/CAN_WORKSPACE.md.
BLE service-only; browser traffic directly over CANBox USB/Wi-Fi. 88 tests/build
PASS; real R1-hosted CAN page + CANBox Wi-Fi 60 s, 12/12 concurrent BLE/time
samples PASS while idle. No loaded CAN/TX qualification. Fallback mode enabled.

## Memory checkpoint — 2026-09-21

### Current state and evidence
BENCH TESTED within the bounded 2026-09-21 report: 0.35-ota-dev deployed, browser OTA app0 -> app1; local display offset saved at +120, EEPROM generation 6. Do not assume live IP/COM/firmware remain unchanged.

### Canonical references
- [docs/R1_S3_PLAN.md](docs/R1_S3_PLAN.md)
- [docs/DEVICE_UI_AND_TASKS.md](docs/DEVICE_UI_AND_TASKS.md)
- [docs/FILE_FORMAT_V2.md](docs/FILE_FORMAT_V2.md)
- [docs/UART_DIAGNOSTICS.md](docs/UART_DIAGNOSTICS.md)
- [docs/RATE_BENCHMARK.md](docs/RATE_BENCHMARK.md)
- [docs/OTA.md](docs/OTA.md)
- [docs/R5_FEATURE_MIGRATION.md](docs/R5_FEATURE_MIGRATION.md)

### Negative knowledge / do not repeat
UART/CP210x: cleaning and cable changes did not prove a root cause; keep cause unresolved, see UART_DIAGNOSTICS. Native USB is a separate path; see CANBox stability report for core affinity evidence. Do not equate 300 Hz clean transport with analog accuracy, or a closed directory enumeration with a held SD transfer. Do not replace R5 tools with a reduced viewer and claim feature parity.

### Open work
Automatic timezone/DST and shared display-zone propagation remain IDEA; only R1 fixed local offset is deployed. Extend OTA fault/power-loss qualification, loaded UART isolation and noise/calibration qualification. Encoder remains a stub. Unified viewer work stays in lily-viewer.

### Dependencies
R3 time/control authority, CANBox fallback control, lily-viewer file readers; TTGO is an OTA/network reference only.

Shared time/control contract: [R3 ECOSYSTEM_CONTROL](../lily-logger-r3/docs/ECOSYSTEM_CONTROL.md). Read the sibling notes before changing it. A shared local timezone remains a requirement, not a completed cross-device feature.

---

# R1-S3 ideas and continuity

Read before changes and revisit at scope/milestone changes.

- [Engineering plan](docs/R1_S3_PLAN.md): acquisition, PSRAM buffering, SD block writer, UI and migration.
- [Migration history](docs/R1_MIGRATION.md): historical implementation and validation.
- [Work reports](WORK_REPORT.md): current dated work, tests, deployment and remaining tasks.
- [Ecosystem time](docs/ECOSYSTEM_TIME_SYNC.md): R3 Control Center is the preferred clock; R1 runs autonomously without it.
- R3's sibling `NOTES.md` contains ecosystem ideas and hardware evidence; review relevant entries rather than assuming all features are already implemented in R1.

## 2026-09-21 owner requirements

- Expose manual calendar entry and browser-clock fallback when valid R3 time is absent.
- Preserve authenticated Control Center priority; never move RTC during recording.
- Maintain separate project work reports; preserve existing ideas and notes.

## 2026-09-21 shared Wi-Fi

Use TTGO-style saved station networks and mDNS, keeping the R1 AP as a recovery
path. Credentials belong in private bootstrap/NVS, never notes or Git history.
Review WORK_REPORT.md for actual deployment and LAN validation.

## 2026-09-21 unified operator time

Owner requirement: every device must show the same synchronized local calendar
clock, including device screens, web panels, file lists, recording filenames and
viewer timelines. Operators must not have to mentally convert UTC. R3 Control
Center supplies the preferred clock AND the shared display timezone; standalone
manual/PC setup supplies the fallback. Do not choose each browser's timezone
independently. Keep canonical UTC/sample timing internally for cross-device
alignment and backward compatibility, and store the recording's timezone/offset
so historical display remains stable after travel or daylight-saving changes.
Existing UTC recordings must not be reinterpreted as local timestamps.
This requirement is recorded; cross-device timezone propagation is not yet
implemented. See WORK_REPORT.md.

R1-only implementation: 0.34-local-time-dev uses the existing saved offset for
UI/OLED/new filenames; PC sync refreshes that offset. Automatic DST and shared
R3 timezone distribution remain deferred. See docs/uk/TIME_SETTINGS.md.

R1 0.35 includes browser OTA (/update); see docs/OTA.md and the physical acceptance
in WORK_REPORT.md. Keep OTA idle-only and preserve storage/acquisition ownership.
