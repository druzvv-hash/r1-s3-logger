# Measurement rates: 1–300 Hz

PANEL v0.22 accepts every **integer** from 1 through 300 Hz. The overview provides
1, 5, 10, 25, 50, 100, 150, 200, 250 and 300 Hz buttons and a number field.
Select a preset or type a number, inspect the displayed ADC mode, then choose
**Apply frequency** (or Enter). Selection alone sends no command. Rates cannot
change during a recording. Stop and wait for the CSV to close first.

## Speed and noise

The overview applies these explicit profiles; conversion time applies separately
to shunt voltage, bus voltage and die temperature. No averaging is enabled.

| Requested rate | Conversion time per channel | I2C clock | Profile |
| --- | --- | --- | --- |
| 1–100 Hz | 1052 µs | 100 kHz | Normal |
| 101–200 Hz | 150 µs | 400 kHz | Fast |
| 201–300 Hz | 50 µs | 400 kHz | Maximum speed |

The panel displays the profile and explains increased noise before application.
The previous [benchmark](RATE_BENCHMARK.md) contains measured examples of the
tradeoff. Sampling frequency and chart frame rate (30/60 FPS) are independent;
animation does not create ADC samples. USB at 115200 baud can limit preview
delivery. Wi-Fi polls extra batches (up to a 10 Hz delivery target) while a queue
is waiting. If USB falls over 0.75 seconds behind (at least one 48-point batch),
the preview requests a recent window and marks the skipped section as a gap.
It does not silently replay increasingly old data. The SD file retains all raw
samples independently of these bounded preview windows.

Shunt resistance, polarity, gains, offsets, range and calibration provenance are
preserved. In particular, a high rate does not silently select the narrow shunt
range. Advanced settings still allow explicit conversion/averaging choices, but
firmware rejects combinations without room for conversion plus the bus and
scheduling budget. The bus clock follows the requested rate in production.

## Persistence and file interpretation

Apply affects runtime only. **Save to EEPROM** is a separate, explicit action.
There is no implicit SAVE at boot, on rate selection or during acceptance tests.
The next boot uses the last explicitly saved configuration.

Quick profiles raise `max_gap_us` to at least `ceil(2000000 / Hz)`; at 1 Hz this is
2,000,000 µs, preventing ordinary one-second sample intervals from being excluded
from energy integration. A larger existing gap threshold is preserved. Advanced
settings may deliberately choose a different integration gap limit.

Config v1.1 retains the same 28 TLV fields. New readers accept v1.0. A profile
with 10/50/100 Hz and a gap limit up to 1,000,000 µs remains byte-compatible v1.0;
other frequencies or a larger gap limit use minor version 1 in JSON/EEPROM.
Older firmware protects a committed v1.1 slot from overwriting. It must not be
used to edit new profiles. See [configuration contract](CONFIG_SCHEMA.md).

R1S3 CSV v1 remains self-contained with exact applied coefficients, conversion
settings, requested frequency and raw samples. The updated reader accepts the
expanded range and older R1/R1-S3 recordings. Old viewers with a fixed rate enum
need this reader update to open new rates. Sample timestamps remain measured
read times; the microsecond scheduler period is integer-quantized, so the measured
average can differ slightly from the requested integer frequency.

## Scheduling

Core 1 owns acquisition, I2C and SD work. Core 0 formats panel JSON from a bounded
snapshot copied by the owner; it never reads the mutable settings or calls Wire.
Optional OLED/RTC work can use ADC conversion wait time if the complete operation
fits before the next service deadline. The loop sleeps a tick when time permits
and checks short deadlines without adding a mandatory full tick to every phase.
PSRAM FIFO and block SD writes remain in place. No recorded sample is replaced
with display-filtered data.

## Verification

Host tests cover all 300 integer profiles, shared JS/Python TLV bytes, C++ timing
bounds and slot readback, unchanged v1.0 fixture bytes, forward protection,
invalid/fractional input, JSON import/export, and EEPROM failure injection.
Browser tests cover presets, manual 137 Hz, 1 Hz and 300 Hz, preservation of
unapplied input while polling, the recording lock, no implicit SAVE and mobile
layout. Hardware results are recorded below after the actual runs.

Reproduce a bounded production sweep through the running USB panel:

```text
python tools/test_rate_range.py --hardware --label my-rate-test --seconds 10
```

It creates new recordings, leaves them on SD and restores the exact starting
runtime configuration on normal completion. Private evidence goes under
`data/production-rates/`. Download the resulting files and run
`tools/analyze_rate_record.py` to verify their integrity with both readers.

## Hardware acceptance — 2026-09-08

Measurements used the connected bench load (roughly 3.26 V / 3.09 A), nominal 150 µΩ shunt and existing coefficients. Acquisition firmware was built clean from `d52defec1bcc0f23bfe114e185d7e43f83e8ff10`. No calibration, RTC write or EEPROM SAVE was performed.

All 15 files were downloaded over native Wi-Fi: **60,759 rows, 12,674,362 bytes**. Both the strict native reader and production streaming viewer verified CRC/checkpoints/SHA, raw-to-engineering values, timestamps and integration. Every file closed cleanly, with zero missing sequences, invalid rows or gap rows.

| Requested Hz | Verified rows | Measured Hz | OLED frames during test |
| --- | --- | --- | --- |
| 1 | 9 | 1.000006 | 26 |
| 5 | 45 | 4.999993 | 26 |
| 10 | 91 | 9.999922 | 26 |
| 25 | 225 | 24.999972 | 23 |
| 37 | 336 | 37.000049 | 24 |
| 50 | 452 | 49.999867 | 24 |
| 100 | 900 | 99.999956 | 16 |
| 137 | 1,223 | 137.005115 | 52 |
| 150 | 1,342 | 150.014230 | 52 |
| 200 | 1,797 | 200.000245 | 47 |
| 250 | 2,231 | 249.996805 | 51 |
| 299 | 2,661 | 299.042121 | 37 |
| 300 | 4,810 | 300.029591 | 61 |
| 300 | 36,405 | 300.029897 | 424 |

The 1 Hz file integrates normally: final energy `0.022424171 Wh`, gap threshold 2,000,000 µs. The long 300 Hz run covers about 121 seconds of samples: FIFO high-water 42 entries, maximum SD write 117.261 ms, no overflow. Owner state was fresh in all 109 sampled snapshots and OLED advanced 424 frames. Read-time intervals were 2513–4174 µs (p99 3447 µs); this is measured scheduling jitter, not a uniform timestamp claim.

A direct Wi-Fi mobile-browser run before the preview delivery adjustment recorded 8,232 verified rows at 300.029161 Hz with zero lost/invalid samples and 94 OLED frames. Its graph rendered about 59.88 FPS but only 16/25 observations were fresh, with up to 3.99 seconds of lag. This exposed the 48-point / 5-packet-per-second delivery ceiling; acquisition was unaffected.

The subsequent preview adjustment (`ab1e7d0`) was tested through the USB bridge during the long run: all 76 observations at RUNNING/300 Hz were fresh, median 59.83 FPS, no browser errors. USB deliberately marks skipped preview windows; all ADC samples remain in the verified file. Direct Wi-Fi acceptance of the revised embedded panel remains pending final upload.

Deployment: v0.22 acquisition/settings from `d52defe` were flashed with verified hashes after one interrupted UART write. The final `ab1e7d0` build includes the revised embedded preview; two later attempts received no ROM bytes on COM5 and did not start writing Flash. Physical UART reconnection was requested. The runtime baseline was restored after every completed test (100 Hz, exact config payload, generation 3); current state after the failed reset attempts has not yet been re-verified.

These bounded tests support this implementation on the present bench setup. They do not close the earlier unexplained reset, intermittent USB-UART issue, long-duration endurance or full-range metrology work.
