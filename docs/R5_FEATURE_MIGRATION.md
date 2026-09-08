# R5 feature preservation — owner correction, 2026-09-07

The P2 release implemented a new file-reading/analysis foundation but omitted much of the useful R5 workflow. It is **not a replacement for the established R5 viewer**. The owner explicitly wants prior engineering work preserved. Do not proceed straight to P3 while treating the minimal interface as the completed viewer migration.

Primary feature donor: `Logger_Analysis/Viewer/Plugins/viewer_ultimate_Plugins_R5.html` (58,266 bytes, SHA256 recorded in tests/fixtures/sources.json), plus `plugins/battery_en.js` and `plugins/starter_cycles_advanced.js`. Read-only source review reconfirmed the features below. The Chart.js R5 Live branch is a separate donor, not an interchangeable revision. Source presence is not new end-to-end feature validation.

## Feature matrix and order

| R5 capability / source evidence | Current P2 state | Preservation work and acceptance |
|---|---|---|
| Dense CSV graph workspace with selectable I/U/P/Wh/Whc/Whd series (HTML 471–533) | Two separate plots, one selectable second channel | P2.1a: restore an analysis-first workspace and multi-series controls; label axes/units; toggling series must not alter input data |
| A/B vertical time markers, C/D horizontal value markers; click/Shift-click (HTML 485–486, handlers near 1075) | Range fields/drag zoom only | P2.1a: persistent labelled markers, exact values, delta time/value and selected interval; distinguish zoom from marker placement |
| Wheel zoom, pan, real-time tooltip/ticks (HTML 489–504) | Drag zoom, segment-relative ticks | P2.1a: wheel/pan/reset and sample tooltip with exact source time/value/quality; never invent UTC for old logs |
| Metrics over selection/full session via CsvPluginAPI (HTML 1699–1728) | Basic sample stats and charge/energy | P2.1b: selection-aware panels retain recorded/recomputed distinction; use full-resolution valid samples; compare hand-calculated fixtures |
| Built-in starter detector with threshold, pre/post windows and minimum duration (HTML 559–611 and detector implementation) | Absent | P2.1b: port working detector, configurable polarity, gap/invalid-data exclusion and insufficient-baseline status; test multiple/partial events |
| Advanced starter cycles: idle voltage, minimum voltage, peak current, duration, voltage drop, resistance estimate and aggregates | Absent | P2.1b: port `starter_cycles_advanced.js` calculations with explicit validity, matched-window inputs and documented assumptions |
| Battery sag/EN analysis (`battery_en.js`) | Absent | P2.1b: preserve measured inputs/useful voltage-drop analysis; any historical EN estimate stays explicitly heuristic, not a certified rating |
| Session plugin list, load/run/log, getData/getSelectionInfo (HTML 536–545,1699–1790) | Absent | P2.1c: versioned extension interface; adapt existing two real analysis modules, test selection semantics; bounded/chunked access must not silently return preview samples as full data |
| Live WebSocket, series selection, connect/disconnect (HTML 405–418,635–640) | Absent | P6 dependency: preserve viewer workflow and define live API now; connect when firmware API is implemented, without presenting a fake working endpoint |
| ESP log listing, open/download (HTML 438,1592–1596) | Local files only | P6 dependency: preserve workflow and map to the actual R1-S3 log API when available |

`plugins/metrics.js` (109 bytes) and `plugins/start_detector.js` (123 bytes) only register/log initialization. They are not the working metric/detector implementation. `registerPlugin/init` and `registerCsvPlugin/run` are different old interfaces; no blanket compatibility claim.

## Keep improvements without losing R5 usability

Retain P2 validated R1/native adapters, exact timestamps, corruption checks, disk-backed full-resolution analysis and extrema previews. Preserve R5 interaction/design as the reference for the analysis workspace instead of starting another reduced dashboard. Fix the known R5 metadata-as-zero, invalid-as-zero and every-Nth-point decimation issues during porting. Bundle dependencies locally if a charting library is introduced; do not restore a required CDN.

The Python/browser split and need for start.cmd are product tradeoffs introduced by P2, not requirements inherited from R5. File-direct opening must explain the launcher instead of failing with `Failed to fetch`. Do not claim standalone HTML compatibility. Reassess browser-only packaging against large-file/checksum needs after the interactive workflow is recovered.

## Completion gate

P2.1a–c precede P3. Demonstrate R5-style marker/selection/series workflows on representative old and native files; verify starter/metric results using controlled event fixtures and preserve ambiguous/invalid statuses. Publish an updated feature matrix distinguishing implemented, hardware/API-dependent and deferred items. Live/device-log integration remains P6, binary readers P8. Updating this document does not implement the omitted features.

## 2026-09-08 — P2.1a implementation

Implemented selectable simultaneous series as synchronized individual-axis panels; persistent sample-snapped A/B and channel-specific C/D; signed deltas; independent full-resolution A/B statistics; wheel zoom, explicit drag-zoom/pan modes, reset and exact original-row hover. Separate axes intentionally prevent comparing A/V/W on an unlabeled shared scale. This is not a literal Plotly overlay port. Sample lookup uses indexed predecessor/successor reads and exposes invalid rows rather than inventing good values in gaps. New files/segments clear markers; changing viewport/series preserves them.

Validation: 30 host tests, existing Chrome import/mapping/corruption/mobile smoke, and dedicated real-pointer R5 interaction acceptance. Tested old eight-column and native sign-crossing fixtures. No new large-file throughput claim; viewport scans still use the P2 disk-backed path. P2.1b starter/battery analysis and P2.1c plugin recovery are still pending; P3 remains gated on them. No firmware or device changes.
