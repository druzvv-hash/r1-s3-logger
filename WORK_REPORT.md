# r1-s3-logger — work reports

## 2026-09-23 — R3 primary CANBox integration verified

R3 now controls R1 and CANBox together and provides coarse UTC. R1 firmware
unchanged. Group START/STOP, saved R1 fallback and return to R3 passed;
25/25 post-return fresh/time samples, not precision acceptance. Canonical report:
../lily-logger-r3/docs/CANBOX_CONTROL.md. Existing averaging owner edits preserved.

## 2026-09-23 — CAN Live update deployed

Shared CAN assets deployed by OTA alongside existing0.37 owner changes.
88 tests/build PASS; real UI122722/0 live-ring losses, not hardware losslessness.
R1↔R3 unchanged; CANBox UTC invalid/service adapter missing.
See [deployment report](docs/CAN_LIVE_FIXES_2026-09-23.md).

## 2026-09-22 — shared CAN workspace

Added CAN tab, embedded `/can`, PC bridge route and generated common assets from
../GLL CANBox/workspace. BLE remains service/control/time only. Browser directly
uses CANBox USB/Wi-Fi; no CAN payload relay through R1. Version 0.36-can-live-dev.
Preserved OTA, timezone and linked-recording implementation.

HOST TESTED: build and 88 Python tests PASS (PlatformIO Python with pyserial).
BENCH TESTED: native COM9 flash/hash to verified active app1 0x490000; subsequent
STATE 0.36/READY/generation 6. Real R1-hosted `/can` + CANBox Wi-Fi: rejected wrong
token, 60 s live/status without stale UI, clean disconnect. Concurrent R1 BLE:
12/12 connected/fresh/clock synced; fallback mode enabled. Zero CAN frames seen.
No physical TX, loaded traffic or new analog accuracy qualification. No R3 flash.
Canonical protocol, LED wiring and limits: sibling docs/CAN_WORKSPACE.md and
CAN_WORKSPACE.uk.md. Evidence stays private in CANBox/local; secrets not committed.

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

## 2026-09-21 — unified local operator time requirement

Reviewed the reported two-hour discrepancy and current time/display code.
The R1 live clock explicitly renders UTC, whereas RTC input and directory dates
use browser local time. Existing display_utc_offset_min is not used for these
views; recording session names explicitly use UTC Z. The ecosystem contract
currently synchronizes UTC, without a shared operator timezone.
Recorded the owner requirement in NOTES.md: one shared local display convention
from the Control Center, persistent fallback, recording-time timezone provenance,
and compatible canonical timestamps. No firmware, RTC, recording or remote
repository was changed in this requirement review. Implementation and hardware
validation across R1, R3, CANBox and viewer remain outstanding.

## 2026-09-21 — R1 local operator time implemented

Deployed 0.34-local-time-dev on R1 native USB COM9. UI live clock and manual
calendar now use saved display_utc_offset_min rather than mixing UTC and browser
local time. PC time button applies/saves its current offset when different, then
sets RTC; existing priority/recording locks remain. OLED header now shows local
HH:MM:SS. New recording names include local calendar and explicit numeric offset;
random identity suffixes remain. Directory parser accepts both new offset names
and legacy UTC names; new names preserve their original local date after an
offset change. Existing CSV canonical UTC and config snapshot remain compatible;
recorded config already carries display_utc_offset_min. Other devices/viewer
were not modified.

Validation: nine serializer/contract/viewer roundtrip tests PASS, including
positive/negative offset, leap-day rollover and unknown time. Nine panel tests
PASS; browser fixture passed local conversion, legacy/new filename recognition,
priority/recording locks and mobile layout. Production build/upload PASS with
hash verification (RAM 89,796; Flash 1,220,093 bytes). Actual visible UI PC-time
button saved generation 6 and offset +120; full config comparison showed ONLY
that field changed. UI displayed 18:08:30 local; RTC was within one second of PC
in a sequential HTTP comparison, TICK OK, zero I2C errors. OLED time rendering
compiled/deployed but not visually observed. No new physical SD recording was
created; filename serialization was host-tested. Browser fixture ran in Prague;
no cross-timezone physical browser test claimed.

Limit: fixed saved offset, not automatic DST; update from PC at seasonal change.
Historical UTC-named files have no filename offset and use current R1 display
offset. Canonical CSV times remain UTC; viewer display work is deferred as asked.

## 2026-09-21 — browser OTA delivered

Read TTGO src/main.cpp as reference; no TTGO edits. Added authenticated /update
page with progress, same-origin/header validation, bounded exact image length,
S3 header check and standard Update verification before slot activation. R1
owner pauses acquisition only after excluding active/linked recording and taking
the SD request gate; releases on failure. Added Wi-Fi panel link and OTA guide.
USB bootstrap deployed 0.35-ota-dev, RAM 90,012 bytes, Flash 1,235,577 bytes.

Validation: nine panel host tests PASS; production build and USB upload/hash PASS.
Physical HTTP bench: missing authentication 401; foreign Origin, invalid header,
and truncated image rejected without reboot; owner resumed. Real Wi-Fi firmware
upload succeeded, verified app0 -> app1 and new boot ID, READY. Full configuration
and EEPROM generation preserved. Additional actual file OPEN lease blocked OTA;
lease closed afterward. A short test recording also blocked OTA while continuing
RUNNING, then STOP finalized it and returned READY. That SD file is a guard test,
not measurement qualification. An initial exhausted directory-list test did not
hold a lease (expected auto-close); the subsequent file OPEN exercised the guard.

Limits: browser form itself not manually uploaded in this bench; matching HTTP
multipart endpoint was exercised. Power loss, unhealthy-image rollback and hostile
LAN isolation are not qualified. See docs/OTA.md for authentication boundary and
firmware selection. No ArduinoOTA IDE protocol added. Existing trusted-LAN model
retained; credentials/images remain outside Git.

## 2026-09-21 — external-memory audit and bootstrap

### Request / Context
Establish durable project context without copying chat transcripts. Reviewed
existing entry documents, relevant reports, repository status and recent commits.

### Changes
Added/linked bootstrap and concise evidence-aware project memory. Existing
technical history, owner notes and unsuccessful approaches retained.

### Validation
Documentation-only audit: local reference existence and Git change scope checked.
No new build, host runtime, browser, bench, hardware acceptance or vehicle test.
Previously reported evidence remains attributed to its original source/scope.

### Result / Limitations
A new task can enter via AGENTS -> NOTES -> relevant WORK_REPORT/docs. This is
not a full code re-audit; contradictory old dates/version banners require the
linked newer report and current code. Private raw evidence may be local-only.

### Failed / rejected approaches
Rejected copying entire histories or turning backup/snapshot folders into active
projects. See NOTES for project-specific negative knowledge.

### Deployment / Next
Documentation only; no device changes. Workspace audit at
C:/Projects/PROJECT_MEMORY.md records repository classification and commit status.
Maintain checkpoints after substantial work; resolve the open tasks in NOTES.
