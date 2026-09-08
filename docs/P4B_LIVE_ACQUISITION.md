# Selectable acquisition and smooth live display — v0.15

The Overview tab changes the **actual INA228 cadence** to 10, 50 or 100 Hz.
Apply takes effect in RAM after validated INA register readback. EEPROM persistence
still requires the separate Save button. No settings schema, defaults or calibration
coefficients were changed.

The browser independently offers 30/60 FPS and a 10/30 second viewport. The curve
contains original calibrated samples, not interpolated extra measurements. A delayed
viewport (300 ms) scrolls between packets; it never invents samples beyond the tail.
The displayed FPS is measured rendering cadence, subject to screen refresh rate,
browser load and background throttling. See
[requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame).

## Hardware owner

Core 1 starts a triggered shunt/bus/temperature conversion on an absolute monotonic
schedule, then returns to the scheduler. After the configured conversion duration,
it checks CNVRF and reads a fresh result. The timestamp is the end of the readback,
not an asserted simultaneous sampling instant for the three ADC channels.
Writing ADC_CONFIG clears stale conversion-ready state; reading DIAG_ALRT checks it.
See the [INA228 datasheet](https://www.ti.com/lit/ds/symlink/ina228.pdf).

Late periods are skipped and counted, never replayed as a catch-up burst. The
two-second measured-rate window counts completed attempts; separate valid, invalid
and missed counters distinguish conversion errors from scheduling gaps. Raw ADC
rails and malformed data are invalid, not zero current.

Runtime configuration requires conversion time plus a 4000 µs bus/scheduler budget
to fit the requested period. ADC timeout remains independently bounded; a timed-out
conversion produces an invalid record, and elapsed schedule slots are counted.
This budget is specific to the present 100 kHz bus and must be revalidated after
changing sensor channels, traffic or the task layout.

Wire has one owner. The SH1106 framebuffer is frozen, then sent in independently
addressed 8-byte pieces only when there is time before the next conversion.
Frame generation still runs on core 1; moving the local menu/render state to core 0
remains part of the wider UI work. OLED frame rate is bus-limited and is **not 60 FPS**.
The configured display rate is an upper bound; completed frames and maximum chunk
duration are reported. RTC reads are quiet and admitted only with sufficient slack.

Explicit tests, configuration mutations and legacy UART commands execute during a
counted maintenance pause, between conversions. Acquisition restarts with a gap
marker. This stage does not promise uninterrupted acquisition during EEPROM backup,
SD diagnostics or settings saves; those commands must be gated when recording is added.

## Transport and memory

- Core 0 runs separate HTTP and UART tasks. Sending a long UART reply does not
  occupy the acquisition loop.
- Both command transports share a submission gate, bounded queue, request IDs and
  deadlines. Only core 1 executes hardware/configuration commands.
- State snapshots publish up to twice per second; browsers request them about once
  per second. Configuration is not retransmitted with every sample packet.
- A separate 2048-record PSRAM history supplies live preview. Up to 48 records are
  copied per request under a bounded cross-core critical section; lookup uses binary
  search. Allocation/JSON formatting/transmission happen outside the lock.
- Each consumer has its own cursor. History overwrite, sequence gaps, invalid
  samples and configuration changes break the plotted line.
- Browser history is bounded to 6000 points. Pausing the chart does not stop INA228.
- The recording SPSC FIFO and 8 KiB SD block remain reserved for P5. This preview
  history does not claim to be a lossless file recorder.

### Live API

GET /api/live?after=123 or UART PANEL request-id LIVE 123 returns:

    {"boot":"...","cursor":171,"oldest":1,"newest":171,
     "lost":false,"preview_drops":0,
     "samples":[[124,12345678,4.906,3.995,0,7], ...]}

Each row is [sequence, monotonic_us, volts, amps, quality, config_revision].
Quality bits: 1 invalid, 2 gap/maintenance, 4 shunt saturation (also invalid).
Invalid numeric placeholders must not be displayed or integrated.
after=0 starts with the latest batch. A boot change resets the browser cursor.
The loopback bridge also requires its existing per-run token.
live_hz controls the batch-delivery target, not ADC or rendering cadence.

## Remaining work

This implements the cadence/live portion of P4b. Production FIFO-to-SD recording,
session totals, backpressure acceptance, file download, encoder input and local menus
remain open. Phone-to-AP acceptance and long-duration timing under simultaneous SD
writes require separate physical tests. USB test captures are private under ignored
data/device-panel; publish only aggregate acceptance evidence.

## Bench acceptance — 2026-09-08

Each rate was observed for about 12 seconds after settling, through COM5/115200
with OLED enabled and live batches requested every 200 ms. This measures the
delivered sample timestamps as well as the firmware cadence counters.

| Requested Hz | Firmware Hz | Delivered Hz | Invalid / missed / preview lost |
|---:|---:|---:|---|
| 10 | 10.000 | 10.0000 | 0 / 0 / 0 |
| 50 | 49.999 | 49.9998 | 0 / 0 / 0 |
| 100 | 100.000 | 100.0164 | 0 / 0 / 0 |

Across these short windows, maximum start lateness was 2.305 ms, INA readback
1.971 ms, OLED chunk 1.614 ms; no I2C errors. Individual read-completion intervals
at 100 Hz ranged 7.956–12.044 ms, so the average rate is not a zero-jitter guarantee.
OLED completed 29 / 19 / 10 frames respectively during the rate windows.

Chrome tested the real Apply path, contrast change/restore, 100 Hz live display
and return to 50 Hz. The 60 FPS mode measured 59.52 FPS in the final browser run,
with zero invalid/missed/preview-lost samples. Displayed gap markers correctly
include the explicit maintenance pauses for Apply; they are not silently connected.
Desktop/mobile layouts and the 30 FPS mode also passed. Full before/after EEPROM
images matched (generation 3, CRC32 EBDAE9A1); no Save was issued.

42 host tests pass, including absolute-deadline skip/wrap cases and live cursor
bounds, in addition to EEPROM/FIFO/format tests. Normal and service builds compile;
only normal firmware is uploaded. UART upload required retries after mid-write
disconnects during development, followed by verified successful writes. That
intermittent transport problem is separate from the successful acquisition windows.
The final normal image uploaded at a one-off 57600 baud with all flash hashes
verified; the project upload default is still 115200 baud. Final normal static RAM
is 62,424 bytes, flash 924,637 bytes (dynamic task stacks/pools are additional).

Subsequent headless runs observed Chrome's own callback rate falling to about
30 Hz; rendering followed that limit while acquisition stayed at 100 Hz. The
browser test compares rendered FPS to the callbacks actually provided, capped
at the chosen target, and restores the original measurement rate even on failure.
Physical history tests also passed ring overwrite/lost indication, latest-tail
selection, independent cursor replay, empty future cursors and maintenance gap flags.
