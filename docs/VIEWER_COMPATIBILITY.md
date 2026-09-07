# Viewer compatibility contract and implementation gates

Status: P1 inventory/mapping and synthetic acceptance corpus. New offline viewer is P2; no claim that old HTML viewers already support the new format. Source hashes: [sources.json](../tests/fixtures/sources.json). Public synthetic files and expected outcomes: [manifest.json](../tests/fixtures/manifest.json). Owner recordings are unchanged and not published.

## Detection and mapping

First identify magic for native R1S3, LYLI or RFL2. Otherwise inspect CSV headers after optional UTF8 BOM, blank lines and `#` metadata lines. Comments before or after a header never become samples. Native checksums use exact bytes and have stricter LF rules; legacy CSV accepts CRLF. Duplicate columns, ambiguous delimiters/decimal conventions and unknown layouts require an explicit mapping, never guesses based on filename.

| Family / observed header | Known interpretation | P1/P2 disposition |
|---|---|---|
| `timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd` | R1 STAB writer: relative milliseconds, A,V,W, signed net and separate positive/negative Wh | Verified source mapping; P2 adapter required. Existing values already scaled/calibrated; no new coefficients applied |
| `timestamp,ms_from_start,I_A,U_V,P_W,Pss_Wh` | Named time/I/U/P fields retained; exact Pss_Wh accumulator semantics not matched to writer | Detect distinct family; preserve original Pss_Wh channel and label meaning unresolved; do not alias to Wh_net |
| `timestamp,ms,I,U,P,Wh` | Observed layout, short names alone do not prove units/time or net-energy semantics | Require confirmed saved mapping or matching writer; preserve original names |
| `timestamp,ms,I,U,P,Wh,Whc,Whd` | Observed variant, not automatically the STAB writer | Same explicit mapping gate |
| Headerless rows | Multiple possible orders/units | Require user-selected mapping and preview |
| R1S3 CSV schema1 | [Exact native contract](FILE_FORMAT.md) | Host reference and golden tests implemented; P2 UI adapter pending |
| LYLI BIN v2 | Multiple block/TLV/checksum variants | P8 pending; matching writer and real de-identified binary fixture required |
| R3 RFL2/END2 FILELOG | DATA/TCHK and timing/config interpretation differ from LYLI | P8 pending; do not count timing records as ADC samples |

Inventory previously found 44 canonical eight-column, 25 Pss, five short-six, one short-eight, plus headerless/metadata-first files. Counts describe inspected archive candidates, not independently verified sessions or support coverage. R1 STAB match is `Projects/bekup/main21_12_3STAB.cpp`. The source is a donor, not a release certification.

Legacy `timestamp` is preserved as text; absent timezone must remain unknown. Relative milliseconds are authoritative where the matched writer proves them. Reset/nonmonotonic time starts a new segment, never globally sort rows to hide it. Missing/NaN/infinite/malformed numeric cells yield unavailable values and a diagnostic, not zero. Keep file line/byte provenance. Short rows cannot silently shift columns. Reordered/extra known legacy columns use names; unknown extras remain separately labelled. Quoted fields use CSV rules, no naive split on comma. Decimal comma with semicolon requires explicit detection/confirmation, never global comma replacement.

## Shared normalized model

Session contains source family/version, original metadata and provenance, channel registry with IDs/units, segments, optional exact raw integers, engineering values or null, u64 monotonic times, optional UTC/time uncertainty, row quality, integrity state, config snapshot and separate recorded/recomputed totals. Rendering and plugins use this model, not file-specific column offsets. JavaScript must retain u64 using BigInt/string representation until converting a bounded relative plot window.

Min/max envelopes are for previews only. Statistics, integration and marker ranges use valid full-resolution samples. Do not bridge gaps or join concatenated sessions without explicit meaning. No fabricated channel when a legacy format lacks voltage/current. Raw counts and reference formulas enable verification of native readings, not double calibration.

## P2 acceptance work

Port the native reference behavior and implement the verified R1 header adapter first. Run every synthetic fixture with exact expected counts, signs, nulls and integrity states. Add reordered/extra columns, quoting, semicolon/decimal-comma confirmation, malformed rows, resets and UTC choices. These P2 cases are listed requirements, not already passing UI tests. Test real archived files locally without publishing private content. Any unresolved short/Pss semantics must remain visible in the support matrix.

Retain useful Plotly R5 marker/range/plugin concepts, but replace metadata-as-zero parsing and every-Nth-point decimation. Deliver pinned bundled dependencies for offline use. A legacy export is a separate, explicitly lossy eight-column file for verified old-viewer profiles; native originals retain raw evidence, metadata and quality. An unchanged positional old viewer is not a compatibility acceptance target.

## Binary evidence gates for P8

The recovered 23_01_26 reader/type files disagree about TLV labels/length comments. Its Block64 rotate/XOR checksum is not IEEE CRC32; fixed-metadata variants include extra values in checksum coverage. R3 has different record framing and timing records. For each supported binary variant require exact writer hash, header/TLV bounds, byte/checksum vectors and known decoded sample counts/times. Until then, report recognized-but-unsupported rather than interpreting all files called v2 alike.
