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
