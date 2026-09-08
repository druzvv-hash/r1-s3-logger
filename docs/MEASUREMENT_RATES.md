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
