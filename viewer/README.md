# R1 / R1-S3 offline viewer 0.2

P2 offline viewer, Python 3.10+ and a modern browser. **No pip/npm install, CDN, Internet connection or device connection is required.** The interface is Ukrainian; code/contracts/documentation are English.

## Start

Windows: double-click `viewer/start.cmd` (requires the Python `py` launcher), or run from the repository/bundle root:

```text
python viewer/server.py
```

The launcher opens the browser. Choose a CSV file or drag it onto the upload area. Keep the launcher running; Ctrl+C stops it. If port 8766 is occupied, use `python viewer/server.py --port 0` to select an available local port. `--no-browser` prints the URL without opening it.

This is a local Python application with a browser interface, **not a standalone HTML or executable**. It binds only to 127.0.0.1, uses a per-run access token, and rejects cross-origin mutation requests. Recordings travel only from the browser to the same computer. Temporary SQLite data are removed at normal shutdown; after a process crash an OS temporary folder can remain. Source recordings are never edited.

## Supported and intentionally limited

- R1 named eight-column CSV: columns by name, optional reordered/extra fields, BOM/CRLF, comments before/after header.
- R1 Pss CSV: current/voltage/power by names; Pss_Wh remains separately labelled because its accumulator meaning is unverified.
- Short/headerless R1 CSV: explicit user confirmation of milliseconds, A, V, W and net Wh before import. Headerless presets have six/eight columns. Unknown layouts require a matching source/mapping, not automatic guesses.
- R1S3 native CSV v1: metadata/config/units, raw/calibrated consistency, monotonic/UTC time, integration, CRC/checkpoints and SHA256 END checks. Exact u64 values remain integer strings in normalized records. Plot coordinates use bounded segment-relative floating seconds.
- Interrupted native file: only checkpoint-verified rows enter charts/statistics; complete unverified tail count and partial-line status are reported. Corrupt files fail explicitly, rather than displaying misleading data.
- LYLI/R3 binary files are recognized but unsupported until P8's verified adapters.

Legacy timezone is unknown unless a fixed UTC offset is explicitly supplied (minutes). This does not implement automatic DST. Existing timezone-qualified strings retain their own offset when interpreted. Relative time stays authoritative. Wrong-width or invalid-time rows are skipped with a continuity break; missing/nonfinite measurements become null and mark the row invalid. Malformed optional columns become null with a diagnostic. This initial viewer conservatively excludes an invalid measurement row from all channel analysis. Parsed numeric values, original timestamp text, line numbers and byte offsets remain in temporary normalized records; unavailable optional text is not retained as a numeric channel.

Select a segment when time resets or a repeated header starts a new session. The viewer never sorts away resets or bridges them. For legacy gaps, twice `interval_us` metadata is used when present; otherwise the explicit import threshold (default 1000 ms) applies. Legacy files cannot prove fresh cadence or missing samples merely from nominal metadata. Adjust the threshold and re-import when necessary.

## Graphs and analysis

Select any available series with the checkboxes. Each channel has its own labelled value axis; all panels share the same time viewport. The statistics-channel selector is independent of visible series. Wheel zoom is anchored at the cursor; choose drag-zoom or pan in the interaction selector. Double-click or “Увесь сегмент” resets the viewport. Numeric start/end inputs provide reproducible selection.

In marker mode, clicks place A then B at the nearest original samples (subsequent clicks replace the oldest). The panel displays exact original t_us, timestamp text, source line and quality. Delta time is signed B minus A. Full-resolution interval statistics use the sorted A/B bounds, independently of zoom. Shift-click places horizontal C/D levels for a single channel; choosing a different channel starts a new value pair so unlike units are never subtracted. Markers persist through zoom and series changes, and clear on new files/segments. “Масштаб A–B” fits their interval.

Hover reports the nearest actual row, its distance from the cursor, original values, quality and continuity status. It does not interpolate values or silently jump over invalid rows. In a gap the nearest sample can be far from the cursor; its displayed distance is intentional. Preview bins retain min/max extrema; a bin containing invalid data or a gap is isolated instead of joined across it.

Statistics scan all valid full-resolution rows in the selected range, not the preview. Mean is sample-weighted. Charge and energy use actual elapsed time, trapezoidal sign splitting, and no integration across gaps/invalid rows. No extrapolation/interpolation to range edges: uncovered edge intervals are included in “without data / outside samples”. Recorded Wh_net delta is shown separately from recomputed energy. First/last cumulative values of an independently opened rotation part are not proof of cross-part continuity.

Download JSON report contains interpretation metadata, diagnostics and selected-range statistics/preview, **not a full-resolution data export; marker coordinates and A/B statistics are included**. At most 200 diagnostic examples are retained, with total count separately available. Unknown optional text values are not plotted as numbers. An old-viewer CSV export, starter/battery plugins, binary adapters and automatic part joining remain later work; they are not advertised by this release.

## Capacity and verification

Input cap: 1 GiB, 10 million rows and 1000 time segments; disk space must accommodate the source upload plus a temporary database that can be substantially larger than CSV. Import reads bounded lines (64 KiB legacy record, 16 KiB native metadata, <=1024 native rows/checkpoint). SQLite uses a 4 MiB page cache; data live on disk. Plot output is at most 2000 extrema bins per selected channel (up to 32 known distinct channels per request). Import/statistics run in the local service, keeping the browser responsive; large scans may take time. Only one recording is active at a time.

Run `python -m unittest discover -s tests -v`. Optional UI smoke test uses Playwright/Chrome supplied by the developer environment: `node tests/smoke_viewer.cjs <printed URL>` and `node tests/r5_viewer.cjs <printed URL>`. It is not a runtime dependency. `python tools/benchmark_viewer.py --rows 350000` tests streaming native input above the P1 oracle's 16 MiB limit. [P2 results](../docs/P2_VIEWER.md) record measured scope and remaining limits.

Build a portable folder ZIP (Python runtime not included): `python tools/package_viewer.py`. Unzip before launching `viewer/start.cmd`.

## R5 preservation correction

This release is the file-reading foundation, not a feature-complete replacement for R5. P2.1a marker/series/navigation recovery is implemented. P2.1b analysis and P2.1c plugin recovery still precede firmware P3; see [migration matrix](../docs/R5_FEATURE_MIGRATION.md). Direct index.html opening now shows launcher instructions and disables nonworking file import.
