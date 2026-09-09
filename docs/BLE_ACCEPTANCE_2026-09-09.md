# BLE S1 bench acceptance — 2026-09-09

**The short physical link, recording and file-integrity bench passed. Expanded
radio qualification remains pending, and the 300 Hz current spread needs
investigation.** This is not clock synchronization or measurement accuracy
qualification. [BLE controls and contract](BLE_LINK.md) ·
[Ukrainian results](uk/BLE_ACCEPTANCE_2026-09-09.md).

## Tested builds and scope

| Device | Deployed source | Firmware binary SHA-256 |
|---|---|---|
| R1-S3 PANEL v0.23 | Clean `f5508afba14599fa4e6488a828da64039d3eaa62` | `28e6e27f69af23b20b20c6fd032828421a0f07160b126deaab1ec8166aa05419` |
| R3 ESP32-S3 Control Center | `0e4925e` **plus preserved pre-existing working-tree changes** | `3e2526b454309dd2fd7eb10248cfa38eb116b6fc83a52bb5ec5c76f52e0941f7` |

The R3 commit alone does not reproduce the tested image; its prior local work
was retained. No STM32 firmware was replaced for this BLE test. The tested R1
client uses one central connection, NimBLE host pools in PSRAM and an
allocation-free receiver; task stacks, controller and DMA stay internal.

R1's Wi-Fi AP was enabled throughout the captured run, but **`ap_clients` was
zero**. The real browser reached the logger through its **USB bridge**. This
tests BLE with AP enabled and real UI polling; it does not establish operation
with an active over-the-air Wi-Fi UI client or native AP file download.

## Physical connection results

- A final discovery check on the optimized R1 build progressed from SCANNING
  to READY and found one R3. Explicit selection then re-established an
  authenticated fresh connection at MTU 128 in a new segment. The scan did
  not silently select or connect to a peer.
- The correct volatile PIN established authenticated encrypted communication;
  the negotiated ATT MTU was 128 and complete coarse beacons reached R1.
- A deliberately wrong PIN was rejected by R3. It did not produce an
  authenticated receiving connection. No actual PIN is retained in this report.
- During the 300 Hz SD run, R3 BLE was explicitly disabled and then enabled.
  R1 lost freshness, retried, authenticated, subscribed and received new beacons
  in a new connection segment while the recording continued.
- Both devices kept their boot identity during that off/on test; it was a link
  interruption, not a device reboot. Source reboot/new-PIN recovery was not
  exercised by this run.
- Accepted-link missing, malformed, duplicate and out-of-order counters and
  notification-queue drops stayed zero. A disconnected interval starts a new
  segment: zero missing packets within segments does **not** mean the outage
  delivered every R3 beacon.
- Status continued to report `synchronized: false`, `coarse: true` and unknown
  uncertainty. Receiving a fresh UTC-valid packet did not discipline either
  clock or modify the native sample timestamps.

R3's console status after BLE operation also reported the existing UART path
active: RTC valid, PORF 0 and zero RTC read failures; metronome sequence 1,413,
UART beacons sent 1,413 with zero send failures. Its **source-reported CM4**
diagnostics showed 1,411 accepted observations, zero failures and `fresh` state.
This supports retention of the existing UART service; it is not an independent
STM32 capture audit, a new STM32 flash, or an ADC-load qualification. Evidence:
private `data/ble-s1/r3-time-after-ble.json`.

## Recording runs

These figures come from finalized owner snapshots and match the validated file
row counts. Durations are recorder-reported elapsed seconds, which include
session boundary overhead; dividing row count by this duration is not an ADC
frequency measurement.

| Requested rate | Recorder duration | Recorded rows | Accepted beacons during run | Missed samples | Invalid samples | FIFO overflows |
|---:|---:|---:|---:|---:|---:|---:|
| 50 Hz | 21.305 s | 1,053 | 22 | 0 | 0 | 0 |
| 150 Hz | 22.792 s | 3,367 | 24 | 0 | 0 | 0 |
| 300 Hz | 22.635 s | 6,681 | 16 | 0 | 0 | 0 |

The 300 Hz run includes the intentional BLE interruption. Every run reached
READY with an empty recording error and a finalized `.csv` path. Across the
141 owner snapshots spanning 99.981 seconds, there was one R1 boot, zero I2C
errors and zero missed/invalid samples or FIFO overflows. The following are
observed diagnostics, not guaranteed worst-case bounds:

| Diagnostic | Observed value |
|---|---:|
| Minimum sampled free internal heap | 23,264 bytes |
| Minimum sampled free PSRAM | 16,554,099 bytes |
| BLE worker stack high-water free minimum | 5,908 bytes |
| Maximum sample start lateness | 1,258 µs |
| Maximum INA read duration | 2,088 µs |
| Maximum recording FIFO occupancy | 26 samples |
| Maximum reported SD block write | 67,298 µs |
| Maximum reported SD sync | 32,004 µs |

The test used volatile rate changes and restored the original 50 Hz profile,
with SAVED settings and EEPROM generation 3. No Save or RTC time-setting
command was issued. This exercise does not validate analog calibration or noise.

## Real browser load

A separate read-only Chrome session kept normal status/live polling active for
100.798 seconds while the recordings and radio interruption ran. It collected
99 state snapshots, saw all three rates and RUNNING/STOPPING/READY, and observed
CONNECTED → RETRY/CONNECTING/PAIRING → CONNECTED.

There were no JavaScript errors or offline UI snapshots. Fresh BLE evidence was
present in 89 of 99 browser snapshots; the others include the intentional
outage/reconnection. Accepted packets rose from 17 to 106 during this browser
window. A 390-pixel mobile layout fit without horizontal overflow. The final
browser state was 50 Hz, READY, authenticated, fresh and MTU 128. The browser
issued no device commands; controller actions came from the separate test runner.

## Download and file validation

The first runner retained the active `.part` path captured before STOP and tried
to download that old name after the recorder finalized and renamed it to `.csv`.
The firmware's READY snapshot already held the correct final path. The runner
was corrected to resolve final paths from explicit READY snapshots, and resumed
verification against those files. This was a test-harness path-selection error,
not evidence that the recorder failed to close or name its files.

All three finalized files were subsequently downloaded and passed both the
reference contract reader and the streaming viewer reader: **11,101 verified
rows / 2,423,076 bytes**, clean integrity, no partial tail, and zero unverified,
missing-sequence, invalid or gap rows. Frequencies below use the CSV's native
monotonic sample timestamps, rather than recorder elapsed time.

| Requested rate | Downloaded bytes | Actual sample frequency | Sample interval median / p99 / maximum |
|---:|---:|---:|---:|
| 50 Hz | 265,834 | 50.000038 Hz | 19,999 / 20,105 / 20,633 µs |
| 150 Hz | 673,665 | 150.014781 Hz | 6,666 / 6,788 / 7,448 µs |
| 300 Hz | 1,483,577 | 300.029356 Hz | 3,334 / 3,441 / 4,143 µs |

Final snapshot after downloads: READY at the original 50 Hz, complete initial
configuration restored, SAVED/generation 3 unchanged, one R1 boot, no missed or
invalid samples and no I2C/FIFO errors. R1 had accepted 585 BLE observations with
zero missing/malformed/duplicate/reordered/queue-drop counts in its connection
segments. R3 reported one authenticated subscriber at MTU 128, zero notification
enqueue errors and zero observation-queue drops. Its rejection counter includes
the intentional failed-authentication exercise and must not be described as zero.

## Measurement-quality observation — unresolved

Integrity of the recording does not establish quality of its measured values.
At the near-zero recorded bus voltage, the 300 Hz current varied much more than
at 50/150 Hz:

| Profile | Mean recorded bus voltage | Mean current | Current standard deviation | Current minimum / maximum |
|---:|---:|---:|---:|---:|
| 50 Hz | 0.002762 V | 0.020319 A | 0.011180 A | −0.089583 / 0.141667 A |
| 150 Hz | 0.002412 V | 0.139224 A | 0.018317 A | 0.079167 / 0.195833 A |
| 300 Hz | 0.000680 V | 0.146621 A | **0.813849 A** | **−1.702083 / 2.481250 A** |

These are whole-file descriptive statistics, not calibrated zero-input noise
measurements. Rate profiles change ADC settings; the 300 Hz run also included
the BLE interruption. The measurements alone cannot isolate ADC noise, input
conditions, grounding, radio activity or an implementation defect. Further
controlled comparisons are required. **Do not treat the clean 300 Hz transport
and file result as production measurement-quality approval.**

A follow-up comparison kept the same 300 Hz ADC configuration and collected
deduplicated LIVE preview samples for ten seconds per phase, after two seconds
of settling. This was subsampled UI data, not a continuous SD recording:

| BLE services | Preview samples | Mean current | Current standard deviation |
|---|---:|---:|---:|
| Connected, before | 912 | 0.547193 A | 0.936115 A |
| Disabled on both R1 and R3 | 864 | 0.509276 A | 0.919469 A |
| Connected again | 912 | 0.544179 A | 0.908217 A |

The large spread persisted with both BLE services disabled. This comparison
does not establish BLE as its cause, nor does it prove radio has no influence.
Input wiring, grounding and ADC-profile behavior still need controlled checks.
The original 50 Hz configuration and authenticated fresh BLE connection were
restored afterward. Private evidence: `data/ble-s1/noise-control.json`.

## Limits and evidence

This short bench run does not qualify poor reception, multi-client use, either
device reboot, source UTC invalidation/clock steps, prolonged holdover, exhaustive
allocation failure, a loaded STM32 sensor pipeline, CAN integration, or measured
clock accuracy. Protocol rejection tests on a host do not replace deliberate
on-air malformed/identity/version/low-MTU tests. Long-term UART stability remains
an independent issue.

The S1 path still leaves DS3231, EEPROM schema and CSV v1 unchanged. BLE clock
observations remain RAM diagnostics; these files do not yet contain persistent
synchronization evidence. S2/S3 must add and qualify time mapping and versioned
file records before cross-instrument timing accuracy can be claimed.

Private evidence: `data/ble-acceptance/s1-final/snapshots.json`,
`recordings.json`, `verified-recordings.json`, and
`data/ble-tests/live-browser-report.json` with desktop/mobile content screenshots.
Final discovery/reselection: `data/ble-s1/discovery-final.json` and
`data/ble-s1/ready-final.json`.
Raw device identifiers, recording names with IDs, PINs, SSIDs and access tokens
are intentionally omitted from this public report.
