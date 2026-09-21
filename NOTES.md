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
