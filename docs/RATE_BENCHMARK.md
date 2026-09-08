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
These are device counters pending complete-file validation. The first reboot's
cause is unresolved. The updated bridge retains a bounded private UART diagnostic
log, and v0.21 reports `esp_reset_reason()` for subsequent failures.

Further measurements and the final supported-rate decision are recorded separately.
