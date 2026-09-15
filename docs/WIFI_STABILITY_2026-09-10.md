# Wi-Fi panel recovery — 2026-09-10

PANEL v0.25 reduces internal-memory pressure in the networking tasks and sends
the embedded page in 1 KiB writes. Measurement settings, EEPROM layout, file
formats, GPIO and saved BLE enrollment are unchanged.

## Failure reproduced on v0.24

The owner reported Android association followed by disconnection, and occasional
page loads with no readings on both phone and PC. A direct PC AP connection
returned a valid native `transport=wifi` snapshot with strong signal, but Chrome
timed out loading `/` after 8 seconds. A subsequent state request timed out.
Further AP connection attempts did not complete within 17 seconds.

UART subsequently returned fresh samples from the same boot. The whole logger
had not restarted. Approximately 17–22 KiB of internal heap remained. Temporarily
stopping disconnected-peer BLE retries through UART did not recover this already
failed AP state; BLE was restored, without changing saved enrollment.

Low internal-memory headroom is a plausible contributor. No failed-allocation
trace was captured, so it is not established as the sole cause. A restart was
also required by the firmware update. Two successful AP visits on one new boot
provide evidence beyond a single post-reset page load, not long-term proof.

## Changes

| Task | Previous stack | v0.25 stack |
|---|---:|---:|
| HTTP panel | 24 KiB | 16 KiB |
| HTTP file download | 24 KiB | 16 KiB |
| Snapshot serializer | 24 KiB | 12 KiB |

This releases 28 KiB of internal RAM. UART and hardware-owner stacks are unchanged;
PSRAM FIFO and SD staging sizes are unchanged. The page is sent in 1 KiB writes,
yielding between writes. A short write closes the connection, with Content-Length
allowing the browser to detect a truncated page.

`network_diag` now exposes AP join/leave counters, HTTP-loop age, internal free
heap and largest block, and minimum free task-stack space. These fields are
diagnostics, not a promise of network availability or measurement accuracy.

## Validation

- PlatformIO `esp32-s3` build and UART upload passed, with flash hash verification.
- Six panel API tests and four download tests passed.
- Two separate real Wi-Fi AP visits used the same ESP boot, with BLE enabled and
  retrying the saved, unavailable R3. Both loaded the native page, reloaded it,
  displayed advancing samples in two concurrent Chrome pages, listed the SD root,
  and downloaded the complete existing 39-byte `r1s3_test_0000.txt`.
- Time to first online state was 1.273 s and 0.247 s; page reload was 88 ms and
  93 ms. No page JavaScript errors were recorded. The second run recorded one
  `ERR_NETWORK_CHANGED` on `/api/live`; polling recovered and both pages stayed
  online in the sampled observations. It was not a zero-request-error run.
- Internal free heap was about 39–45 KiB under the observed browser workload and
  47.7 KiB after disconnection. Final minimum free stack values were HTTP 5,528 B,
  download 5,944 B, serializer 5,484 B, and UART 12,208 B.
- At the final check: 18,509 valid samples, zero missed/invalid samples and I2C
  errors; READY at 50 Hz, unchanged configuration bytes and saved generation 3.
- PC home Wi-Fi was restored and temporary test profiles removed after each visit.

Both browser pages used **one physical PC Wi-Fi station**. This does not establish
two-station operation, physical Android stability, active R3 BLE coexistence,
large-file downloads, high-rate recording under Wi-Fi load, or overnight stability.
The AP still permits two stations. The owner's phone retest is pending.

Flashed binary SHA-256:
`823af923e60d8e6c0643e021eb95e6e4ae19e452db6a0893982b1016bb927d16`.
Private raw captures are retained in ignored `data/ecosystem-control/` directories;
they include configuration/connection material and must not be published.
