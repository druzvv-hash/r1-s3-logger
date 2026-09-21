# r1-s3-logger — work reports

Append dated entries with scope, changes, validation, limitations, deployment and next steps. Do not include credentials or claim unperformed tests.

## 2026-09-21 — reporting established

Created this project-specific report at the owner's request. Existing notes and
history remain authoritative; this entry does not claim a retrospective code or
hardware audit. No firmware was deployed and no project functionality changed
as part of this reporting setup.

## 2026-09-21 — Control Center clock priority and local time UI

Request: make the R1 clock configurable with R3 Control Center priority and manual
fallback; consult existing ideas and maintain independent project reports.

Changes:
- Added Overview date/time controls: explicit browser clock or local calendar
  entry, timezone display and conversion to UTC. Invalid dates and spring DST
  gaps are rejected; repeated autumn times use the browser's earlier occurrence.
- Fresh authenticated valid R3 UTC (under 5 seconds old) prevents manual RTC
  writes in both UI and firmware, including legacy serial commands. CANBox is
  not treated as R3 time authority. Disconnect/invalid/stale R3 allows fallback.
- Existing recording guard and RTC readback remain. Only the already validated
  ecosystem owner path bypasses the local-clock priority guard; it still cannot
  change time while recording. Manual changes invalidate old R3 provenance,
  allowing existing automatic synchronization to resume when R3 returns.
- Accepted 9-digit Unix timestamps for the supported year-2000 RTC range.
- Version: 0.32-time-dev; no EEPROM schema or recording format change.
- Read R1 engineering/time plans and sibling R3 NOTES.md. Added R1 NOTES.md links,
  owner time instructions and shared C:/Projects/AGENTS.md continuity rules.
- Created independent WORK_REPORT.md files in seven active Git repositories;
  archive/snapshot directories were excluded. Other repositories received only
  their reporting file, not functional changes.

Validation:
- Production PlatformIO build PASS: RAM 87,556 bytes; Flash 1,202,421 bytes.
- RTC priority host test PASS: executes actual admission functions against mocked
  hardware; freshness boundary, authentication, CANBox exclusion, recording lock,
  epoch bounds and absence of write/provenance side effects on rejected commands.
- Time browser fixture PASS: local-to-UTC, DST gap, no implicit write, authority
  and recording locks, mobile width. General panel and BLE browser fixtures PASS.
- Nine panel/API/bundle host tests and two BLE trust/protocol tests PASS.
- Updated the old BLE fixture assembly to include INA/chart modules and use the
  stable tab selector; it previously failed before exercising any BLE controls.
- git diff --check PASS.

Deployment: built locally, not uploaded to a board; no physical RTC/radio test,
commit or GitHub push in this work session. Next: deploy to an identified idle R1
and test manual set/readback, R3 reconnect priority and power-cycle RTC retention.

## 2026-09-21 — requested deployment of time controls

Identified R1-S3 on native USB COM9 by MAC 90:e5:b1:cd:55:74 and PANEL
0.31-canbox-dev response. Recorder was READY with saved settings generation 5.
Built/uploaded esp32-s3-usb 0.32-time-dev successfully; flash hash verified.
Native build: RAM 87,356 bytes, Flash 1,187,985 bytes.

Three post-boot STATE responses confirmed 0.32-time-dev, READY, advancing samples
and RTC, ADC OK, TICK OK and zero I2C errors. Full configuration and EEPROM
generation matched pre-upload state. No TIME or EEPROM Save command was sent.
R3 time authority was unavailable during this check; physical R3 priority and
manual time write/readback remain separate acceptance tests. No Git commit/push.

## 2026-09-21 — shared LAN Wi-Fi, TTGO-style connection

Request: access R1 while phone/PC stays on the home network; provision known Wi-Fi
profiles. Read TTGO README/main.cpp and R3 NOTES.md. The inspected notes did not
contain home credentials; used the owner's saved Windows WLAN profiles instead.

Implemented AP+STA, three NVS profile blobs, 20-second nonblocking profile retry,
mDNS r1-s3-7455.local, LAN status/links and primary-network UI configuration.
Network writes run on the network task, with recording/download checks at both
queue admission and execution. Existing AP remains available. Fixed SD download
redirect to use the incoming interface's local IP instead of always the AP IP.
No OTA or captive portal was added. TTGO functional code was not modified.

Provisioned TP-Link_CC06, dlink_DWR-932_4280 and iPhone. Secret bootstrap header is
Git-ignored; credentials are absent from public docs and station status. NVS is
separate from measurement settings. Private seeded firmware must not be published.

Validation/deployment:
- LAN browser fixture and existing panel browser checks PASS; nine host panel/API
  checks PASS. Verified mobile layout and removed obsolete AP-only UI text.
- Built/flashed final 0.33-lan-dev via native USB COM9; image hash verified.
  RAM 89,796 bytes; Flash 1,219,625 bytes.
- R1 joined TP-Link_CC06 while PC stayed on the same network. Both
  http://192.168.0.149/ and http://r1-s3-7455.local/ worked.
- Real Chrome page showed advancing samples on one boot, zero I2C errors and no
  page errors over a bounded 15-second observation. SD directory listing passed.
- Downloaded an existing 735,865-byte CSV through the LAN redirect on port 81;
  Content-Length matched. SHA-256:
  c4dd33c702b56b1967f739f6ec1ece9b6a8744d2e9ed12facf5f52aca564bf9d.
  This is a transport check, not renewed measurement-file validation.
- After the final cosmetic reflash, automatic reconnect worked, READY returned,
  measurement configuration and saved generation 5 matched baseline, and the
  HTTP-served page matched the generated asset byte-for-byte.

Limits: alternate hotspots, router-loss recovery, profile changes through the
physical UI, phone acceptance and long-term BLE/Wi-Fi coexistence are not yet
qualified. RSSI varied roughly -71 to -82 dBm. No measurement settings, RTC or
recordings were changed; no Git commit/push was performed.

## 2026-09-21 — requested Git synchronization

Set RTC from PC using the visible UI button; UI confirmed RTC UTC written and verified. R3 time was unavailable, recorder idle. Audited the five outgoing CANBox commits and current time/LAN work for known WLAN secrets; ignored bootstrap/data remain excluded. Committing and pushing to the existing origin/main as requested. Previous build and targeted tests are recorded above.
