# Rate and noise experiments

The normal profile still offers 10/50/100 Hz. Experimental results do not promote
a higher rate or a different ADC preset automatically. The owner requested a
measured speed/noise comparison before choosing supported compromises.

`esp32-s3-benchmark` is a separate build, labelled `0.21-bench` in the panel and
recording metadata. It accepts experimental requested rates from 10 to 1000 Hz;
normal configuration validation remains unchanged. EEPROM writes are blocked at
both command and storage levels in the benchmark build. The UI displays a warning.

Through the existing revision-checked command queue, `BENCH Hz CT AVG I2C_Hz seconds`
starts one recording with equal shunt/bus/temperature CT codes, selected averaging
and either 100 or 400 kHz I2C. Duration is 5–600 seconds. The hardware owner stops
the recording and restores the previous volatile profile and I2C clock after
finalization, without depending on the browser or PC timer. Reboot still loads
the previously saved EEPROM profile. Other settings/calibration are preserved.

`tools/rate_bench.py --hardware --label <unique-label> --cases <cases>` drives an
explicit sequence through the local USB bridge; cases are semicolon-separated
`Hz:CT:AVG:I2C_Hz:seconds`. It requires idle benchmark firmware and writes private
snapshots/results to ignored `data/rate-tests/`. A reboot or failed restore stops
the sequence. Normal firmware does not accept BENCH.

Benchmark CSV files retain the native integrity/raw/config metadata contract,
but rates outside the released registry require an explicit diagnostic reader
override. They are not new supported production presets. A normal viewer rejects
an unsupported configuration instead of silently assuming its meaning.

TI documents the trade-off between conversion time, averaging and noise in
sections 7.3.4.2 and 8.1.3 of the [INA228 datasheet](https://www.ti.com/lit/ds/symlink/ina228.pdf).
The present default uses three sequential 1052 us conversions without averaging.
Bench dispersion includes source ripple, wiring and measurement noise; it is not
an independent ADC-noise or calibration measurement. Comparisons must report
actual cadence, gaps/invalid samples, file integrity, UI/OLED availability and
the load conditions as well as observed dispersion.

## Initial evidence

On 2026-09-08 an initial v0.20 100 Hz run rebooted without owner intervention;
the old bridge had not retained a reset trace. It is not counted as stable.
A second 300-second run, with the owner disconnected from the panel, completed
30,031 rows and 6,262,019 bytes with zero missed/invalid samples and FIFO overflow.
FIFO high-water was 12, maximum write 66.460 ms and maximum sync 105.373 ms.
At that stage only device counters were available; full-file validation is below. The first reboot's
cause is unresolved. The updated bridge retains a bounded private UART diagnostic
log, and v0.21 reports `esp_reset_reason()` for subsequent failures.

## Completed measurements — 2026-09-08

The following ceilings apply to this firmware and this bench, not to the INA228
silicon's theoretical limit. The released UI still offers 10/50/100 Hz. No faster
preset has been promoted or saved to EEPROM.

| Mode | Verified recording | Control/display consequence |
|---|---|---|
| Default ADC, 100 kHz I2C, 100 Hz | 300 s, 30,031 rows, 99.999995 Hz, no missing/invalid rows | Normal state and OLED updates |
| Default ADC, 100 kHz I2C, 125 Hz | 20 s, 2,473 rows, no missing rows | State nearly frozen; not a usable general preset |
| CT=150 us/channel, 400 kHz I2C, 200 Hz | 120 s, 23,959 rows, 199.999983 Hz, no missing/invalid rows | State and OLED active; USB live preview sometimes lags |
| Same 200 Hz profile, direct Wi-Fi | 30 s, 5,957 rows, 200.005776 Hz, no missing/invalid rows | 28/28 observed live updates fresh; median 59.87 FPS; OLED +46 frames |
| CT=50 us/channel, 400 kHz I2C, 330 Hz | 90 s, 29,615 rows, 330.030638 Hz, no missing/invalid rows | No OLED progress; state frozen for about 88 s; diagnostic recording only |
| CT=50 us/channel, 400 kHz I2C, 350 Hz | 15 s, delivered 333.626 Hz, 242 missing sequence numbers | Requested rate is not sustained |

The timed duration includes arming/finalization; delivered rate is calculated from
the first and last verified sample timestamps. Integer microsecond periods explain
small nominal-rate differences such as 330.03 Hz. All cases use averaging=1;
CT codes 0/2/3/5 mean 50/150/280/1052 us per channel. All three channels remain
enabled with the original range, shunt, gains, offsets and polarity.

The 200 Hz USB browser run added six to the device's lifetime missed-period counter
near completion. **The complete recording has zero sequence gaps and zero GAP or
INVALID rows.** The lifetime counter also includes acquisition outside the file's
recording interval; it must not be substituted for per-file integrity/cadence checks.
USB preview was fresh in 44/117 observed RUNNING snapshots despite about 59.9 FPS
animation. A separate direct-Wi-Fi test was therefore necessary; it had fresh preview
in every observed RUNNING snapshot and no lifetime missed-period increase. Browser
tests used Chrome on the PC at a 390 x 844 viewport, not a physical Android device.

The 330 Hz test's FIFO high-water was only 59 samples with no overflow, despite a
174.949 ms maximum SD write. At 200 Hz/120 s it was 18 samples, maximum write
75.747 ms and sync 80.611 ms. The tested rate ceiling is primarily in the present
trigger/poll/read scheduling and shared-I2C work, not exhaustion of the PSRAM FIFO.
The owner loop calls `delay(1)` and only publishes state with >1800 us slack,
updates an OLED chunk with >2600 us, and polls RTC with >4500 us. Raising the
requested rate can therefore starve state/OLED/RTC work before the recorder loses
samples. Separate cores alone do not eliminate this shared-owner constraint.

### Observed dispersion, not an accuracy calibration

The load was approximately 3.26 V and 3.09 A during these recordings. It was not
re-measured against an independent reference during this sweep. Standard deviation
includes supply/load ripple, wiring, drift and ADC noise.

| Window | Current standard deviation | Voltage standard deviation |
|---|---:|---:|
| 100 Hz, CT=1052 us, initial 20 s | 15.20 mA | 1.69 mV |
| 100 Hz, CT=50 us, 20 s | 67.75 mA | 4.53 mV |
| 200 Hz, CT=150 us, 120 s | 44.50 mA | 3.96 mV |
| 330 Hz, CT=50 us, 90 s | 69.21 mA | 4.75 mV |

Long-record read-completion intervals also have jitter: 100 Hz/300 s ranged
7.959–12.030 ms (p99 11.012); 200 Hz/120 s ranged 2.908–7.107 ms (p99 6.076);
330 Hz/90 s ranged 2.392–4.461 ms (p99 4.004). They are timestamped measurements,
not a claim of uniform sub-millisecond sampling or simultaneous channel conversion.

### File integrity and the earlier reboot

All 31 downloaded experiment artifacts were parsed by both the contract decoder and production
viewer adapter. Thirty completed files pass metadata/block CRC, final SHA-256,
raw/calibrated value, time and integration checks with no unverified tail. This
includes overload cases whose marked sequence gaps and incomplete totals are
intentional evidence of a failed requested cadence, not successful rate tests.

The initial reboot left
`r1s3_2026-09-08_12-38-26Z_199455ff_d06bba0e_0000.part`: 2,885,599 bytes, 13,808
checkpoint-verified rows, no unverified/partial trailing row and no END record.
Its persisted span is about 138.07 s at 100 Hz. Both readers correctly classify it
as interrupted. It remains on SD and its copy is retained on the PC. Samples still
in RAM at the interruption cannot be recovered from this file. The owner confirmed
no reset or power intervention. The cause remains unresolved; there was no further
unexpected reboot during the subsequent experimental sweep or direct-Wi-Fi test.

Experimental-rate files require `tools/analyze_rate_record.py --experimental-rate`;
this relaxes only the diagnostic rate registry to 10..1000 Hz, not integrity or
sample validation. The ordinary viewer still rejects unpromoted rates. The release
reader accepts the 100 Hz baseline and interrupted recording without an override.
Original recordings and private reports are under ignored `data/rate-tests/`.

### Complete sweep

Missing sequence numbers below come from full downloaded files. OLED progress and
state age come from device snapshots and include boundary work; a single frame in
a whole test is not evidence of a continuously usable display.

| Requested Hz | CT code | I2C kHz | Timed s | Actual Hz | Missing seq | OLED frames | Max stale state s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 5 | 100 | 20 | 100.000 | 0 | 15 | 0.0 |
| 125 | 5 | 100 | 20 | 125.000 | 0 | 1 | 18.1 |
| 150 | 5 | 100 | 20 | 133.242 | 332 | 0 | 18.1 |
| 200 | 5 | 100 | 20 | 133.175 | 1322 | 1 | 19.2 |
| 250 | 5 | 100 | 20 | 133.191 | 2310 | 0 | 18.2 |
| 100 | 0 | 100 | 20 | 100.000 | 0 | 31 | 0.0 |
| 150 | 0 | 100 | 20 | 150.008 | 0 | 1 | 0.0 |
| 200 | 0 | 100 | 20 | 200.000 | 0 | 1 | 18.1 |
| 250 | 0 | 100 | 20 | 219.787 | 597 | 0 | 18.1 |
| 400 | 0 | 100 | 20 | 219.539 | 3566 | 0 | 18.1 |
| 200 | 0 | 400 | 20 | 200.010 | 0 | 32 | 0.0 |
| 250 | 0 | 400 | 20 | 250.000 | 0 | 0 | 0.0 |
| 300 | 0 | 400 | 20 | 300.032 | 0 | 0 | 8.5 |
| 400 | 0 | 400 | 20 | 333.535 | 1313 | 1 | 18.1 |
| 500 | 0 | 400 | 20 | 333.619 | 3286 | 0 | 18.1 |
| 800 | 0 | 400 | 20 | 334.008 | 9202 | 0 | 19.3 |
| 1000 | 0 | 400 | 20 | 333.991 | 13155 | 1 | 19.3 |
| 320 | 0 | 400 | 15 | 320.001 | 0 | 0 | 13.2 |
| 330 | 0 | 400 | 15 | 330.033 | 0 | 1 | 13.2 |
| 350 | 0 | 400 | 15 | 333.626 | 242 | 0 | 13.3 |
| 225 | 0 | 400 | 20 | 225.029 | 0 | 2 | 0.0 |
| 150 | 5 | 400 | 20 | 150.015 | 0 | 0 | 2.4 |
| 200 | 5 | 400 | 20 | 166.691 | 659 | 1 | 19.2 |
| 200 | 3 | 400 | 20 | 200.000 | 0 | 3 | 0.0 |
| 100 | 5 | 100 | 20 | 100.000 | 0 | 15 | 0.0 |
| 330 | 0 | 400 | 90 | 330.031 | 0 | 0 | 88.1 |
| 200 | 2 | 400 | 20 | 200.000 | 0 | 31 | 0.0 |
| 200 | 2 | 400 | 120 | 200.000 | 0 | 184 | 0.0 |

### Next decision

Keep the current 100 Hz default-quality mode while selecting the next supported
presets explicitly with the owner. A 200 Hz / 150 us / 400 kHz profile is a useful
candidate with a visible noise trade-off and direct-Wi-Fi preview. The 330 Hz raw
ceiling is not yet suitable for a user-facing preset because state/OLED updates
starve. Before promoting it, separate state publication from acquisition slack,
budget OLED/RTC work and re-test command responsiveness, timing and longer sessions.
Higher-rate normal files also need a coordinated versioned config/viewer contract
update. No claims are made about overnight stability, every SD card, physical
Android acceptance, 400 kHz EEPROM writes or the cause of intermittent USB uploads.

After the sweep, normal v0.21 from clean commit
`0781a4047c34cd411e33868540fb15e0a129398b` was flashed with ROM/no-stub at 38,400 baud
and flash hash verification. The final 100 Hz smoke recording has 628 verified
rows / 134,223 bytes, no gaps or invalid rows, and opens through the unmodified
production reader. The device is READY with the exact original volatile 100 Hz
profile, I2C 100 kHz and saved generation 3. No EEPROM Save or time adjustment was
performed. The original PC Wi-Fi profile was restored after every AP roundtrip.
