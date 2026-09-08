# Overnight UART and SD endurance — 2026-09-08/09

The owner authorized an unattended night test with the logger powered, bench
supply OFF and its measurement wiring still connected. This tests transport,
acquisition and recording stability near zero input, not loaded accuracy or the
cause of the earlier intermittent fault. Firmware v0.22 remains unchanged.

## Bounded run

Started at **2026-09-08 20:27 Europe/Prague**, with a ten-hour budget ending near
**2026-09-09 06:27 Europe/Prague**. Cleanup may extend the finish slightly.

1. Make, close, download and validate a five-second 50 Hz canary recording.
2. Record approximately 20 minutes each at 50, 100 and 300 Hz. After each STOP,
   download that entire finalized file through UART with per-block CRC32 checks.
3. Validate native metadata/configuration, checkpoint CRCs, final SHA-256,
   raw/calibrated values, integration, quality and cadence with the production
   streaming viewer decoder. Files no larger than 16 MiB also use the independent
   whole-file reference reader. Retain originals and validation reports.
4. Use the remaining budget for 300 Hz acquisition with continuous LIVE polling
   and health snapshots. Downloads also leave acquisition running.
5. Close any owned transfer/recording and restore the exact initial volatile
   configuration: 50 Hz, EEPROM generation 3. Keep the panel available.

UART at 115200 with hexadecimal file replies is deliberately slow. The run has
a hard time budget: an unfinished transfer is retained as `.download`, reported
as incomplete, and must never count as a verified file. Existing SD files are
not overwritten or deleted. Twenty-minute sessions fit the initial rotation
policy; the runner refuses a smaller incompatible rotation setting.

## Evidence and stopping

The runner shares one serialized UART connection with the local panel. During
testing the panel permits live/state reads; configuration and SD file controls
are reserved by the test. Windows UART error masks, request failures, boot ID,
advancing uptime/sample counters, FIFO occupancy/overflows, SD write/sync maxima,
I2C errors, internal/PSRAM free memory and OLED progress are captured. Preview
drops are distinct from acquisition loss. Logs are bounded and private.

Unexpected reset, acquisition/I2C loss, UART error flags, storage/validation
failure, low memory or unrecoverable transport failure stops the test and
triggers best-effort cleanup. State-changing commands are never automatically
replayed after an ambiguous response. Cleanup does not overwrite an externally
changed configuration or stop an identified unrelated recording. If communication
is lost, cleanup is reported as unconfirmed; the tool cannot guarantee an SD
STOP without a working command path. No automatic hardware reset hides failures.

The PC is temporarily kept awake by the test thread; its permanent power plan
is not changed. Keep the PC powered and running. Firmware, EEPROM and RTC are
not written. A thread heartbeat checks progress every 30 minutes and reports
failure or completion, without repeating unchanged status messages.

Private artifacts: `data/overnight-2026-09-08_20-27-07/`. `status.json` contains
safe progress, `events.jsonl` bounded observations, `uart-errors.json` error
flags, and `baseline.json`/`restored.json` private full configuration. Do not
publish raw state/session files. The status PID identifies the actual Python
worker (Windows may also have a Python launcher parent).

Orderly cancellation: create a file named `STOP` inside that exact run directory,
or POST to the current panel's authenticated `/api/overnight-stop` endpoint.
Allow cleanup to finish before manually using SD/configuration controls. This
runner is a local process; the scheduled heartbeat supervises it independently.

## Outcome

**Interrupted by a reproduced UART fault; the ten-hour plan did not complete.**
The worker ended at **2026-09-08 22:33:29 Europe/Prague**, after **7,579.4 s
(2 h 6 min 19 s)** including its initial cleanup attempt. The first transfer
failure occurred two seconds earlier. No second overnight run was started.

Startup canary: 322 rows / 84,417 bytes, verified clean in both
readers; actual cadence 49.999572 Hz, no missing/invalid/gap rows. Complete-file
SHA-256: `5e966c1ebe3bb712720c8df8ef5192609dd6b747b9028d3a8a4b7bd471314302`.
The five-second polling window produced about 6.42 seconds between first/last
stored samples, including command/publication latency; durations are measured
from the file rather than assumed from the PC timer. Seven host guard tests
pass, covering ambiguous control replies, ownership, external configuration,
unexpected boot, lost samples, cancellation and corrupt-file rejection.

### Recording and transfer results

| Stage | Device recording | PC verification |
| --- | --- | --- |
| Canary, 50 Hz | 322 rows / 84,417 bytes | Complete; both readers verified clean |
| 50 Hz, 20-minute target | 60,098 rows / 15,517,430 bytes | Complete; both readers verified clean; no missing/invalid/gap rows |
| 100 Hz, 20-minute target | 120,122 rows / 30,981,634 bytes; device finalized `.csv` and returned READY | Transfer interrupted; only 1,153,024 bytes retained on PC; full file remains unverified |
| 300 Hz recording and remaining soak | Not reached | Not tested in this overnight run |

The verified 50 Hz file has 1,201.939998 s between first and last sample,
50.000000083 Hz actual cadence and 19,084–20,874 us sample intervals. Its
complete-file SHA-256 was independently recomputed after the failure:
`887c0fe32cfb6d67103430274b3c5c8bf0828e86dae7604d0cf30535931e871b`.
The device reports 1,201.465 s for the finalized 100 Hz session; its complete
file cadence/quality cannot be established from the interrupted download.

The partial 100 Hz PC copy passes 4,407 checkpoint-verified rows, followed by
76 complete but unverified rows and a partial line. It is correctly classified
as interrupted. Integrity of the remaining bytes on SD is untested; the
incomplete transfer does not establish corruption of the SD source file.

### Failure and health evidence

Before the worker finished, it counted **35,356 successful requests** and two
failed operations: a FILES reply with an invalid JSON control character, then
a cleanup CLOSE that could not obtain the UART lock within two seconds. Windows
reported **two `CE_FRAME` (`0x0008`) notifications** at 22:33:26.694 and
22:33:26.697 local time. They are error notifications, not counts of damaged
bytes or proof of two separate physical incidents. No other UART mask was
recorded during the run. Subsequent panel requests also saw temporary lock
timeouts and a LIVE timeout; these occurred after the worker's final counters.

Across **1,356 health snapshots**, the boot ID remained `135af910`. Missed
samples, invalid samples, I2C errors and FIFO overflows all remained zero.
Maximum FIFO occupancy was 6 samples at 50 Hz and 14 at 100 Hz, within the
2,048-sample PSRAM queue. Maximum SD write/sync times were 106.364/78.851 ms
at 50 Hz and 132.234/117.983 ms at 100 Hz. Free internal heap ranged from
93,000 to 103,756 bytes, and free PSRAM from 16,555,807 to 16,591,247 bytes.
Chip temperature was 24.617–25.125 C. No memory-reserve guard triggered; this
bounded observation is not a proof of indefinite leak-free operation.

The recurrence occurred with the bench supply OFF, so the earlier powered load
is not required for this failure. The error still does not identify a specific
component, joint, signal-integrity issue or driver as its cause. No firmware,
EEPROM, RTC or hardware reset operation was used to recover this run.

### Cleanup and final state

The runner's first cleanup stopped at the busy UART lock before restoration,
leaving `needs_attention` and the initial evidence intact. The heartbeat then
queried the **existing panel/serial owner**, verified the same boot and READY,
and confirmed the expired transfer was closed. It compared the applied 100 Hz
profile with the exact test-generated profile before restoring the baseline.
By **22:37:44 local time**, two fresh states confirmed **READY, 50 Hz, SAVED,
EEPROM generation 3**, the original configuration bytes and advancing samples.
No additional STOP was needed because the 100 Hz recording had already closed.
The panel remains running and temporary sleep inhibition has been released.

Private evidence is retained under the original run directory, including
`failure-evidence/`, `supervisor-audit.json`, `supervisor-recovery.json` and
`supervisor-restored.json`. The original worker status is deliberately not
rewritten to imply that its cleanup succeeded. The follow-up check is stopped
after this final report. Before another unattended run, cleanup should prevent
panel polling from taking the UART lock ahead of bounded recovery operations;
this host-side cleanup limitation is separate from the recorded framing fault.
