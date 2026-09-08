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

**In progress.** Startup canary: 322 rows / 84,417 bytes, verified clean in both
readers; actual cadence 49.999572 Hz, no missing/invalid/gap rows. Complete-file
SHA-256: `5e966c1ebe3bb712720c8df8ef5192609dd6b747b9028d3a8a4b7bd471314302`.
The five-second polling window produced about 6.42 seconds between first/last
stored samples, including command/publication latency; durations are measured
from the file rather than assumed from the PC timer. Seven host guard tests
pass, covering ambiguous control replies, ownership, external configuration,
unexpected boot, lost samples, cancellation and corrupt-file rejection.

Do not interpret the plan or a successful canary as completion of the full
night test. Append measured results after the runner finishes.
