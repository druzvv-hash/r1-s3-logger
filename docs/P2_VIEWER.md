# P2 completed: offline viewer core, 2026-09-07

Delivered [viewer](../viewer/README.md): local Python service plus bundled HTML/CSS/JavaScript, two Canvas graphs, range/segment selection, extrema-preserving preview, full-resolution statistics/integration and JSON diagnostic report. Windows launcher: `viewer/start.cmd`. No firmware upload or EEPROM changes in this stage.

## Implementation decision

The plan's TypeScript core was a proposal. P2 instead reuses the tested P1 Python semantic validator and adds a streaming adapter plus disk-backed SQLite index. This avoids two independent interpretations of native CRC/time/calibration at the first viewer milestone. The browser contains only presentation/control and receives bounded previews. No third-party runtime packages, renderer CDN or npm build are needed. Distribution is an offline source ZIP requiring Python 3.10+, not a standalone HTML/EXE. A later browser-only distribution would need a separately tested port and incremental hash/storage implementation.

## Verification evidence

| Check | Result |
|---|---|
| Host suite | 29 tests passed: original 16 contract tests + 13 viewer tests |
| Native golden parity | Same verified values/counts, interruption/tail status and rejection as P1 reference |
| Legacy cases | BOM/CRLF, comments, reordered/extra/quoted multiline fields, null/NaN, explicit decimal-comma/semicolon, short/headerless confirmation, resets/repeated headers, missing rows and timezone choice |
| Peak preview | Single 99 A point among 2000 samples retained in 50 bins; stats maximum remains 99 A |
| Exact time | u64 microseconds beyond JavaScript safe integer retained as strings; relative millisecond difference preserved |
| HTTP boundary | Per-run token required; valid upload/window succeeds; ambiguous layout returns preview/422 |
| Browser | Actual Chrome smoke test: file input, range/reset, mobile layout, short mapping confirmation and corrupt-file rejection; no JavaScript exceptions |
| Visual inspection | Desktop and 390-pixel mobile renders inspected; axis tick count reduced on narrow screens; six statistics cards fit responsive layout |
| Private archive | 84 CSV files under recovered Logs inspected read-only: 45 canonical R1, 25 Pss, 14 needing confirmed mapping; 2,870,946 rows imported across the 70 recognized files |

Archive count is higher by one canonical file than the earlier header-only inventory because metadata-first input is now recognized. These are import/structural checks, not proof of the original logger's measurement accuracy or unresolved Pss energy semantics. Private filenames/data were not published.

## Streaming measurement on this workstation

`python tools/benchmark_viewer.py --rows 350000` generated a temporary synthetic native file with valid metadata, checkpoints and END, larger than the P1 oracle's 16 MiB limit:

- Input 20,933,349 bytes, 350,000 rows; all verified clean.
- Import 55.547 s **with Python tracemalloc instrumentation active**.
- Full-range two-channel statistics/envelope scan 4.112 s, 1000 output bins.
- Peak traced Python allocations 465,709 bytes; this excludes SQLite/native allocations and browser memory, and is not total process RSS.
- Temporary database 136,921,088 bytes. Disk cost is substantial; capacity documentation does not assume index size equals CSV size.

The architecture bounds parser blocks, diagnostic examples, SQLite cache and output bins. Supported input cap is 1 GiB / 10 million rows; this is an enforced ceiling, **not a tested 1 GiB performance guarantee**. Source files stay untouched; temporary database is deleted at normal shutdown. No performance claim for mobile hardware or other disks.

## Exact support boundary / next stage

P2 core supports verified R1 headers and native R1S3 v1. Pss remains separate/unverified, short/headerless files need user-confirmed mapping, unknown/binary versions are rejected explicitly. No cross-part stitching, plugins/C-D markers, legacy export or full-resolution export yet. Range integration uses only adjacent valid samples wholly inside the selection; uncovered edges/gaps are reported, never extrapolated. Local wall-clock conversion uses an explicit fixed offset, not automatic DST.

Native corrupt files fail rather than returning a misleading partial clean result; interrupted files expose only checksum-verified rows to analysis. Legacy has no checksum and cannot prove freshness from nominal timing metadata. Recorded totals and recomputed totals are displayed separately.

The P2 data-core gate is met for this support matrix, but the owner correctly identified missing R5 workflows. **P2.1 R5 feature recovery precedes P3**; see [feature matrix](R5_FEATURE_MIGRATION.md). This minimal UI is not the completed R5 replacement. Existing bring-up calibration/ALERT/acquisition timing gates remain open.
