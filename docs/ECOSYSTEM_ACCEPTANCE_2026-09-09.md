# ECO1 two-board acceptance — 2026-09-09

## Scope and deployed firmware

One physical R3 ESP32-S3/RV3028 and one R1-S3 ESP32-S3/INA228/DS3231 were tested. Both ESP firmwares were uploaded with flash verification. STM32 firmware was not changed. This is bounded functional acceptance, not qualification of three physical nodes, precision synchronization or analog accuracy.

| Artifact | SHA-256 |
|---|---|
| Final R1-S3 PANEL 0.24 firmware.bin | `2c7d1570149a0532253663199215785aecfd368b97bef1aff15d091383e00fb6` |
| R3 CC firmware.bin | `b5d5d78bc5c764f57ebd28fb6939a2e26328d7f134922852c527a164cf0f0150` |
| Shared ECO1 protocol header | `9613de0f61bca75623a24f5ab522d57447d06e33790f177e95fb4e35a38990b0` |

R1 uses 87,212 bytes static RAM and 1,179,093 bytes program space; R3 uses 138,056 and 1,422,389 bytes respectively. R1's first pass used firmware hash `9551b01e56c72675bc963e9f22b2b4583dd73cd8fdf214ba3b5f529719e412ae`; the final build additionally preserves rejected-command receipts and cache-overflow rejection. Boot recovery, 300 Hz remote control, revocation/re-enrollment and rapid local Stop were checked on the final build.

The deployed R3 build includes the existing working-tree CC recording-profile changes present before this task. Those changes and the existing STM32 edits are preserved separately; they are not silently included in the ecosystem commit. R1 source baseline was `a78d18a2e72c0c7cc19f3ddc055a381d1ec5c807`, R3 baseline `1ad3b0863643b4490f592573f22358e4d4caa13a`.

## Physical results

- **Permission separation:** temporary authenticated connection did not enroll the node. `BLE SAVE 0` established time-only trust, corrected the downstream RTC, and kept remote START disabled. Both actual R3 UI and direct HTTP denied START. `BLE SAVE 1` enabled explicit remote control.
- **Real coordinator UI:** the browser loaded `/ecosystem` directly from R3 over its Wi-Fi AP. Selecting the single node and clicking START/STOP produced actual recording, stopping and closed states. No browser page errors were observed. Each command had a session/group identity; queued acceptance was not treated as file closure.
- **Admission guards:** the live HTTP service rejected a missing custom header (403), a stale target boot (409), a wrong Stop session (409), and a selection containing a nonexistent second node (409). The failed selected-set preflight did not start the valid first node.
- **R3 restart during recording:** R1 kept the same boot and recording file, reacquired the saved bond after the R3 ESP reset, and continued sampling. The new source boot made `rtc_synced` false during recording; the I2C owner applied a fresh correction only after closure. No dropped/invalid samples or buffer overflow were reported.
- **R1 restart with authority absent:** after the final upload/restart, R3 BLE was disabled. R1 restored its saved policy and remained independently ready using DS3231, with valid samples. Enabling R3 BLE caused automatic authenticated connection and RTC correction, without a new PIN or Save.
- **Revocation:** R3's targeted forget removed the enrolled node and disconnected it. R1 could not restore the revoked authenticated connection while the enrollment window was closed. Explicit R1 Forget, a new R3 enrollment window and fresh pairing restored an unsaved connection; Save with remote permission restored the usable association.
- **Rapid local Start/Stop:** an immediate Stop completed its own new file successfully (15 verified rows). The serial status snapshot did not resolve the brief STARTING phase, so this is not claimed as physical observation of the STARTING latch; that boundary is covered by source review/host checks.
- **Runtime settings:** the 300 Hz profile was temporary. The exact original runtime config was restored to 50 Hz, with EEPROM generation 3 unchanged and no settings SAVE. Saved BLE policy/bonds use their separate NVS storage.

## Downloaded file evidence

Every file below was downloaded from the R1 UI download endpoint and passed both the reference contract reader and the production viewer: complete clean ending, matching integrity, identical verified row counts, no partial lines, missing sequences, invalid rows or gap rows. All are CSV schema 2 with monotonic samples and frozen provenance. The counters reported zero recording overflow.

| Case | Rows | Bytes | Measured rate |
|---|---:|---:|---:|
| R3 UI remote Start/Stop, 50 Hz | 549 | 126,286 | 49.999494 Hz |
| Local recording across R3 reset, 50 Hz | 722 | 131,422 | 50.000062 Hz |
| Final firmware R3 UI Start/Stop, 300 Hz | 3,304 | 726,180 | 300.030875 Hz |
| Final firmware immediate local Stop, 50 Hz | 15 | 5,806 | 49.998571 Hz |

Whole-file SHA-256 values, in table order:

1. `5513026fd82567100ef15b2273ab4861b02f710d048b2be44d4dd2a79708be45`
2. `dcd3fac2333e1683d547df99e87d5b05d9e84ae04d82be9802d5d91aa88ab77a`
3. `042f101499616c79c4ccb8bca5442c09ba4341b719b6129161b9d0f31b81b5ea`
4. `118b37688f1d13b1ba21c680ccc74c6f1941c8da3d39dfeab5ae7b09a3f27b67`

The 300 Hz record lasted 11.347 seconds including closure accounting. Its FIFO high water was 24 samples with an 8,192-byte SD block and 65,536-byte PSRAM queue. Sampling continuity is not an analog-quality result: the faster ADC profile showed appreciably more noise/offset at the bench. No new calibration or accuracy claim is made.

Remote files carry non-null group/coordinator identifiers. Locally started files carry null group/coordinator identifiers even when their RTC previously came from R3. UTC and RTC-correction uncertainty remain `null`; source identity/boot/revision and exchange ages are recorded. Existing schema-1 fixtures remain supported by both readers.

## Software verification

- R1: 52 selected Python/portable C++ tests passed, including 11 BLE trust/protocol/receiver tests and actual schema-1/schema-2 serialization plus both readers.
- R1 browser checks: explicit SAVE 0/1, saved ON/FORGET, STARTING Stop availability, privacy and no reload replay passed.
- R3: protocol/coordinator reconciliation tests, 199 HTTP parser assertions, three pinned-NimBLE guard tests, and 30 browser fixture assertions passed.
- Both full ESP32-S3 PlatformIO builds passed. New protocol headers match byte for byte. A separate build exported only the staged R3 CC source, excluding the pre-existing recording-profile edits: PASS (138,056 bytes static RAM; 1,417,385 bytes program space). That isolated artifact was not flashed.

The portable tests cover malformed versions/lengths/flags, boot and connection fences, expiry, conflicting duplicates, immutable rejected receipts, bounded queue/cache overflow, RTC freshness, pending-result reconciliation and invalid selection parsing. They complement, rather than replace, the one-pair physical observations above.

## Remaining qualification

Three simultaneous physical nodes and radio partial failures need additional compatible nodes. The CAN adapter and R3's local STM32 recorder are not selectable implementations yet. Hard power cuts, physical RTC-invalid injection, precise offset/drift estimation, simultaneous sampling, schema-2 physical rotation, long-term timing accuracy and long-duration group-control stress remain separate work. No S2 precise synchronization claim is implied by `rtc_synced`.

Private raw serial/API observations, screenshots and downloaded bench files remain in the local ignored `data/ecosystem-control` evidence folder. Pairing PINs, panel tokens and credentials are excluded from this public report.
