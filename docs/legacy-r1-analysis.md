# Legacy R1 and viewer recovery review

Reviewed 2026-09-07. The requested `Desktop/Logger/_Analysis` path does not exist on this workstation; the matching directory is `Desktop/Logger_Analysis`. Source files and archives were read without modification. No legacy firmware was built or flashed, and no complete viewer application was run. Only the isolated CSV parser functions were executed against short excerpts of existing logs.

## Best R1 recovery candidate

`Projects/bekup/main21_12_3STAB.cpp` is the strongest recovered OLED/INA226 R1 baseline candidate. It is 43,678 bytes, SHA-256 prefix `1d0edfc54f64`. Identical bytes appear in:

- `Projects/Temp/main_R1.cpp`.
- `Projects/bekup/esp_clamp_logger.7z`, member `esp_clamp_logger/src/main.cpp`.
- The same two loose-file paths inside the top-level `Projects.7z` archive.

Its modification timestamp is 2025-12-21 19:19:44. The duplicate archived copy and matching CSV schema are stronger evidence than the STAB filename alone. No definitive hardware acceptance record or binary-to-source identification was found; treat it as a recovery candidate, not a newly validated release.

| Candidate | Size / SHA-256 prefix | Interpretation |
|---|---|---|
| `esp_clamp_logger_R1/mainbase_old.cpp` | 26,132 / `25b397a7a63b` | Earlier December 4 baseline |
| `esp_clamp_logger_R1/mainbase.cpp` | 26,166 / `dbb257d8d28e` | Small revision of earlier baseline |
| `esp_clamp_logger_R1/src/main.cpp` | 30,013 / `320243f068ed` | December 9 project source; older than STAB |
| `Projects/bekup/main20_12.cpp` | 35,716 / `8cc37861c621` | December 20 evolution |
| `Projects/bekup/21_12_1.cpp` | 36,526 / `5ba12bcf74b7` | December 21 intermediate |
| `Projects/bekup/main21_12.cpp` | 32,563 / `6f694f5d8ead` | Separate intermediate |
| `Projects/bekup/main21_12_2.cpp` | 37,104 / `1fe5dafea5dc` | Later intermediate |
| `Projects/bekup/main21_12_3STAB.cpp` | 43,678 / `1d0edfc54f64` | Main OLED R1 recovery candidate |
| `esp_clamp_logger_r1_1/main_tft_espi.cpp` | 28,331 / `9062edac6888` | January 1 timestamp; separate TFT/INA226 branch |

The TFT branch uses ST7789 240×240 in its INI, with TFT_eSPI and ESP32dev. Its later timestamp does not make it the appropriate OLED baseline. Folder timestamps largely reflect copying in February and should not rank releases.

`Projects/esp_clamp_logger/src/main.cpp` is now a small TFT layout demonstration, not the archived R1 logger. The archive with the similar project name is more useful for recovery.

## What STAB already implements

- ESP32dev/Arduino, INA226 at 0x40, SSD1306 128×64, DS3231, SD CS=5, default Wire/SPI pins, battery voltage through ADC GPIO34.
- Current from signed INA226 shunt voltage; configured shunt default 50 micro-ohms and historical current gain. Voltage uses a separate ADC divider, gain and offset, rather than INA226 bus voltage in the measurement path.
- Requested sampling rate 1–500 Hz, default 50 Hz; microsecond scheduler. OLED/WebSocket updates are limited to 5 Hz.
- STOPPED/RUNNING state, explicit START/STOP/RESET. STOP writes buffered data and closes the file; RESET also clears energy totals.
- Power and separate positive/negative energy totals, `Wh_net = Whc - Whd`.
- 8192-byte RAM CSV buffer, periodic RAM-to-SD write approximately once per second.
- HTTP UI, WebSocket on port 81, `/data`, `/start`, `/stop`, `/reset`, `/filter`, `/rate`, `/api/getTime`, `/api/setTime`, `/api/getConfig`, `/api/setConfig`.
- Log listing/download endpoints with compatibility aliases.
- Calibration settings in Preferences/NVS namespace `r1cfg`; configuration edits require STOP. These are not external 24C32 EEPROM settings.

Historical calibration values describe the old bench, not the new INA228/shunt hardware. Do not copy them as validated R1-S3 calibration.

## Data contract worth preserving

```text
timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd
```

Current, voltage, power and energy are A, V, W and Wh. `ms_from_start` is elapsed session time. STAB emits `# rate_hz=...` and `# interval_us=...` after the header. Live JSON includes canonical names plus legacy aliases `t_ms`, `I`, `U`, `P`, `Wh`; HTTP also reports requested rate and interval.

Old timestamp strings have no timezone marker. The old `/api/setTime` handler shifts Unix time by the browser timezone offset before storing the local calendar in RTC/system time. New R1-S3 stores UTC. Export metadata must distinguish old local-time logs from new UTC logs; do not silently reinterpret old strings as UTC.

## Firmware issues to address during porting

1. **Filename collision deletes data.** Filenames contain time only to the minute. `openLogFile()` calls `SD.remove()` when that filename exists. Two STARTs in one minute can discard the earlier recording. Use unique session names and never overwrite automatically.
2. **SD short writes are unchecked.** Buffer writes discard the buffer without checking the returned byte count. Periodic writes are not a power-loss durability guarantee; file flush occurs on header/STOP. Define failure handling and durability policy.
3. **I²C failure can appear as zero current.** INA read helpers return zero on a short read and do not propagate bus errors. Preserve validity/error flags in the new driver.
4. **Requested rate is not fresh sensor rate.** The INA226 configuration requests 16-sample averaging with 1.1 ms shunt and bus conversions. Repeated software reads at up to 500 Hz do not establish independent conversions at 500 Hz. Derive INA228 acquisition timing from its actual configuration and readiness.
5. **Timing/energy assumptions need revision.** Scheduling increments by the nominal interval and energy uses nominal dt. Blocking SD/HTTP activity and late catch-up reads can distort timing. Record actual sample timestamps, gaps and actual integration intervals.
6. **Time can be changed while recording.** The old time endpoint has no RUN-state guard; the startup path may also restore build time after RTC lostPower. Keep the explicit browser synchronization behavior and define recording-time policy.
7. **Configuration is not a hardware-independent specification.** GPIO34 voltage ADC, SSD1306, default SPI/I²C, NVS layout and INA226 register scaling must be replaced/adapted for the current board.
8. **Network controls need deliberate scope.** The old code has a fixed AP credential, state-changing GET endpoints and permissive CORS. Credentials were not copied into this report or the new project.

These are source-review findings, not a claim that every issue manifested in historical use.

## Viewer families

### Plotly R5 with plugins — preferred recovery candidate

`Viewer/Plugins/viewer_ultimate_Plugins_R5.html` (58,266 bytes; SHA prefix `0304076793a9`) uses Plotly 2.32.0 from a CDN. It contains CSV plots, A/B time and C/D value markers, range statistics, starter-event detection, live WebSocket data, ESP log listing/download, and CSV session plugins.

`CsvPluginAPI` provides selected/full data and marker information; `registerCsvPlugin` loads analysis modules. Supplied modules include `battery_en.js` and `starter_cycles_advanced.js`. Older `registerPlugin` modules are a different interface; the small `metrics.js` is only a registration/logging stub. Battery/EN calculations are heuristics, not a verified standards test or calibrated battery rating.

Plotly R5 reads the canonical eight-column R1 schema by column name. However, isolated parser tests on the first lines of existing files found:

- `Logs/2025_12_03_08_09.csv`: correct first sample, 132 ms and 0.358 A.
- `Logs/2025_12_21_17_42.csv`: two metadata lines become fabricated zero-valued samples and nonsensical dates. Comments must be skipped before parsing.
- Invalid/missing numeric values are silently replaced by zero. Short/malformed rows need validation.
- `new Date(timestamp)` uses runtime-local interpretation for zone-less strings. An explicit legacy/local versus UTC policy is necessary.
- Plot decimation keeps every Nth point, which can miss short peaks; use min/max envelopes where peak preservation matters.
- The live fallback expression using `??` does not catch NaN when `ms_from_start` is missing. Validate timestamps explicitly.

This is the best feature donor, not a ready-to-release viewer unchanged. CDN dependence means it is not fully self-contained offline.

### Chart.js R5 Live — distinct older interface

`Viewer/Prototype/R5/viewer_ultimate_R5_live_controls_r4.html` (25,079 bytes; SHA prefix `d181bca6fa3a`) is identical to `Logs/Viewer/viewer_ultimate_R5_live_controls_r4.html`. It uses an unpinned Chart.js CDN dependency and a positional CSV parser expecting elapsed milliseconds in column 1.

Actual isolated parser results:

- Eight-column R1 CSV: treats the year `2025` as 2025 ms and elapsed milliseconds as current (e.g. 132 A), shifting the remaining columns.
- Metadata-bearing CSV: throws `Cannot read properties of undefined (reading 'replace')`.

Live mode accepts the legacy aliases emitted by STAB, but CSV compatibility must be fixed before use. Do not choose this file solely because its name ends in R5/live/r4.

### R4 copies and later binary viewers

`Viewer/viewer_ultimate_R4_3.html` and `viewer_ultimate_R4_2_3_6.html` are byte-identical (SHA prefix `00bb116b0cef`): the version names do not imply different code.

`Projects/lily_viewer_uplot_skeleton` and dated January viewer trees use Vite/TypeScript/uPlot and LYLI BIN v2 (HeaderV2/TLV/Block64), with envelope previews and optional block CRC checks. They belong to the later ADS-based R2 line, not the original CSV R1. Their rendering/data-source ideas may be useful later; their file parser is not a drop-in replacement for R1 CSV.

## Existing logs and evidence limits

The top-level `Logs` directory contains 84 CSV files. Header inventory: 44 canonical eight-column files, 25 older Pss_Wh files, five short six-column headers, one short eight-column header, eight files beginning directly with data and one beginning with metadata. Three files contain metadata in their first few lines.

Selected elapsed-time checks, excluding comment lines:

| Log | Parsed rows | Elapsed-step min / median / max | Observation |
|---|---:|---|---|
| `2025_12_21_17_42.csv` | 663 | 5 / 111 / 151 ms | Metadata requests 9 Hz; initial timing varies |
| `2025_12_21_17_33.csv` | 1720 | 3 / 4 / 193 ms | Nonuniform sampling; requested rate alone is insufficient |
| `2025_12_03_08_09.csv` | 896612 | -39740268 / 100 / 40092 ms | 27 nonpositive deltas; split/reset handling is needed |

The last file's timestamp resets may reflect concatenation or sessions; the cause was not established. These logs support the existence of recordings, not exact identification of the firmware binary or proof of measurement accuracy. Raw logs were not copied to the public repository.

## Scope and continuation

Focused inspection covered the R1/R1_1, Projects, Lily, Viewer, Logs/Viewer and R2_next trees, excluding generated dependencies/build trees. Ten loose INA226 source files were located. 201 ZIP archives in those trees were searched for bounded C++/INO source entries; two contained an older 25,003-byte R1 source. Three targeted 7z archives were inspected without extracting into the source folders. Large STM32/vendor trees, unrelated sniffer projects, every archive/binary, and the PDF snapshot were not exhaustively reviewed.

Next: finish INA228 functional bring-up; implement validated measurements; preserve a documented CSV/live contract; port logger state, buffering and energy logic with the issues above corrected; then recover the Plotly viewer parser and plugins in a separate explicit task. Keep original copies intact.
