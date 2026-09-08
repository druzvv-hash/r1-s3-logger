# R1-S3 engineering and compatibility plan

Plan version 1.4, 2026-09-08. Status: P0/P1/P2 and P2.1a graph interactions completed. Owner redirected work to logger firmware: P3 settings, then P4 acquisition and P5 recording. Remaining R5 viewer work resumes with real logger files. Owner-facing Ukrainian edition: [plan](uk/R1_S3_PLAN.md). Evidence and execution history: [migration journal](R1_MIGRATION.md).

## 1. Product and scope

Build a dependable single-shunt voltage/current/energy logger, easier to operate than the old R1 and more explicit about data quality. Retain ESP32-S3, INA228, SH1106G 128x64 at 180 degrees, DS3231 UTC, 24C32 and SPI SD. Current shunt is nominal 60 mV / 400 A = 150 microohms; the module's R015 has been removed by the owner. GPIOs remain in `hardware/pinmap.md`.

The preserved v0.10/v0.11 baselines and current CONFIG v0.12 are not yet a recorder. v0.11 removed normal startup SD/EEPROM write tests; v0.12 adds explicit configuration persistence. ID, fresh conversions, basic storage, OLED and RTC work. At one owner-reported point, R1-S3 measured 4.906 V versus XDM1241 4.9035 V and 3.995 A versus the supply's 4.000 A. This is useful evidence, not a full calibration. ALERT, sustained timing, zero drift, power-loss handling and independent current accuracy remain open.

Interpret “self-contained” in both useful senses: this document explains the architecture without old chats, and every native recording carries everything needed to interpret it without the original device, EEPROM or a companion settings file.

First release: reliable R1-S3 recording plus new-viewer support for recovered R1 CSV families. The same viewer architecture must also accept verified LYLI/R2 and R3 FILELOG variants in the later compatibility stage. Do not transplant STM32 dual-core IPC, ADS131M08 rates, FRAM allocation or 8704-byte records into this two-channel INA228 application.

## 2. What to reuse, change or reject

| Donor | Keep | Adapt / reject |
|---|---|---|
| R1 OLED STAB | START/STOP, signed current, voltage/power/energy, buffered SD, simple UI | Replace monolithic globals, INA226/ADC34 scaling, unchecked writes, colliding filenames, nominal-dt integration and zero-on-read-error |
| R3 acquisition/storage | Raw evidence, explicit validity, actual timing, config snapshot, finalization and recovery information | Use bounded ESP32 services; no ADS-specific time reconstruction without evidence that it applies |
| R3 configuration | Wanted/applied distinction, validation, version/CRC, A/B persistence | 24C32 has write delay/endurance constraints unlike FRAM; implement page-safe transactional saves |
| Plotly R5 plugins | A/B and C/D markers, range statistics, event-analysis concepts | Replace CSV parser, zero substitution and every-Nth-point preview; version plugin API |
| LYLI/uPlot viewers | Binary adapters, bounded previews, min/max envelopes | Verify each header/TLV/checksum variant against its writer; do not treat every BIN v2 as identical |

Source evidence: [R1 review](legacy-r1-analysis.md); R3 `README_EN.md`, `r3_config.h/.c`, `ads_fram_cfg.h/.c`, `sd_filelog.h/.c` under the existing `lily-logger-r3` tree (HEAD `cdfa3b9`, with local work, not a newly tested release); recovered `Projects/23_01_26/src/bin/reader.ts`, `src/bin/types.ts`, `src/data/binV2.ts`, `src/data/crc.ts` in `Logger_Analysis`.

New finding: that viewer tree has conflicting TLV labels between its type declarations and active readers; Block64 uses a custom rotate/XOR checksum, with a different checksum input for its fixed-metadata variant. Filename/version labels alone are insufficient. Preserve originals and record full source hashes in the fixture manifest during stage P1.

## 3. Firmware boundaries

Proposed modules, introduced incrementally:

| Module | Responsibility |
|---|---|
| `drivers/ina228` | Register I/O, conversion readiness, raw values and hardware faults |
| `measurement` | Immutable samples, calibration, timestamps, quality and derived values |
| `config` | Typed schema, defaults, validation, editing, applying, import/export |
| `storage/eeprom` | Explicit serialization, A/B persistence and migration |
| `recorder` | State machine, queue, SD writer, sessions, checksums and recovery |
| `time_service` | Monotonic time, RTC validity, UTC anchor and explicit synchronization |
| `ui` / `web` | Display/control from snapshots; never own acquisition or SD writes |
| `diagnostics` | Health, counters, last error and exportable troubleshooting snapshot |

Use one owner for I2C transactions and one owner for the SD filesystem. A bounded producer/consumer queue separates acquisition from potentially slow SD writes. OLED, network and RTC requests have lower priority than measurement. Implementation may use FreeRTOS tasks, but core pinning and task count follow measured timing rather than imitation of R3. An OLED transfer must not silently consume the acquisition budget.

Separate raw recording samples, calibrated values, filtered display/live values and plot preview envelopes. Never replace stored raw samples with a smoothed trace. Baseline target: 50 fresh measurement cycles/s, screen/live 5 updates/s, with validated 10/50/100 Hz profiles as candidates. These are targets, not advertised supported rates. Validate conversion times, averaging, sequential channel timing, I2C traffic and SD latency before enabling each profile. No “500 Hz” merely because the loop reads 500 times/s.

Use conversion-ready events (ALERT after validation, or bounded ready-flag polling). Record acquisition timestamps and sequence numbers. INA228 channels are sequential: describe which point the timestamp represents and channel timing/averaging in metadata; do not promise simultaneous voltage/current sampling. Die temperature may be sampled more slowly only if its timing and validity are explicit.

## 4. Parameters and calibration

Keep board facts, user settings, measured calibration and volatile state distinct. One typed parameter registry should define units, defaults, bounds, serialization IDs, whether STOP is required, and whether a field is public in recording metadata. The web form and import validator use the same contract.

| Group | Initial fields / policy |
|---|---|
| Hardware | Board revision, INA identity, topology, fixed GPIO map; no arbitrary pin editor initially |
| Shunt | `shunt_uohm=150`, nameplate 60 mV/400 A, polarity +1/-1, tolerance/temperature coefficient unknown until supplied |
| Calibration | `i_zero_uV=0`, `i_gain=1`, `u_zero_V=0`, `u_gain=1`, calibration ID/date/reference/method and validity |
| Acquisition | Requested profile/rate, VSHUNT/VBUS/temperature conversion settings, averaging, ADCRANGE, ready timeout, validated actual settings |
| Recording | Format version, flush interval, buffer limit, rotation size, reserve space and time-invalid policy |
| UI/live | Display rate, live rate, display-only filter type/parameters, brightness; units remain explicit |
| Time | RTC stored UTC, display timezone, time validity; no silent build-time initialization |
| Session | Operator description/test object/tags in session metadata; do not write EEPROM for every annotation |
| Runtime only | Counters, instantaneous values, buffer use, active session, monotonic timers; never save per sample |

Define formulas once, in firmware and viewer:

```text
I_A = polarity * (Vshunt_uV - i_zero_uV) / shunt_uohm * i_gain
U_V = (Vbus_V - u_zero_V) * u_gain
P_W = U_V * I_A
Wh_net = Wh_positive - Wh_negative
Ah_net = Ah_positive - Ah_negative
```

Avoid redundant current-offset and voltage-offset knobs with overlapping meanings. Shunt temperature compensation stays disabled until there is a justified model and actual shunt temperature; INA die temperature is not automatically shunt temperature. Reject nonfinite values, nonpositive resistance/gains, unsupported modes and rates beyond the validated budget. Separate service-level wide bounds from normal calibration limits.

Integrate using actual elapsed monotonic time and valid samples. Specify trapezoidal integration and split sign crossings for positive/negative totals. Never integrate through a missing-data gap beyond the agreed maximum or fabricate zero samples. Mark totals incomplete with covered/missing duration. By default record source-side power UBUS*I; if load-side voltage/power is added, give it a distinct channel and formula rather than silently subtracting shunt/lead drops.

Config lifecycle: edit draft -> validate -> apply/read back while stopped -> explicit save -> verify persistence. Keep draft, applied and persisted generations visible; failed save leaves applied values marked unsaved, failed apply retains/restores the previous runtime config. START requires a valid applied config and normally a saved matching generation. Freeze measurement/calibration/time-setting for a running session; changes require STOP/new session. Each file contains the applied snapshot, never a later EEPROM read.

## 5. EEPROM 24C32, 4096 bytes

P1 byte allocation and host size tests are defined in CONFIG_SCHEMA.md; physical transactional writes remain P3:

| Address | Bytes | Purpose |
|---|---:|---|
| `0x0000–0x05FF` | 1536 | Config slot A |
| `0x0600–0x0BFF` | 1536 | Config slot B |
| `0x0C00–0x0FFF` | 1024 | Reserved, not a per-sample/event journal |

Each slot: 32-byte header, up to 1472 bytes explicitly serialized payload, 32-byte commit/footer page. Include magic, schema major/minor, payload length, generation, CRC32 and completion marker. Define endianness and field IDs; do not persist an ABI-dependent C++ struct. Define CRC coverage over identity/version/length/generation and payload; footer must match the same generation/checksum. Unknown major versions must not be silently interpreted or overwritten.

Save to the inactive slot: invalidate its commit page and verify -> write header/payload page by page -> ACK poll and read back -> verify CRC/semantics -> write completion page last -> verify -> update active generation in RAM. Never invalidate the good slot first. Boot chooses newest valid completed generation with defined wrap/tie behavior; recover from the other slot or expose DEFAULTS/CONFIG INVALID. Test interruption at every write phase, including a torn completion page. A/B+CRC detects torn data; it is not a claim of physically atomic EEPROM writes.

Only explicit changed settings trigger writes. No sample counters, energy accumulators, autosave slider writes or periodic wear. Back up the existing 4096 bytes before first schema deployment. Remove startup EEPROM pattern testing before persistent settings land; destructive/service tests must not overlap production slots. Remove automatic SD test files from normal production startup too.

Export/import a versioned human-readable settings JSON with validation and preview. Credentials stay outside public measurement metadata and exported recordings; use separate platform credential storage. EEPROM stores one robust applied profile initially; multiple named profiles can live as SD JSON and be imported when stopped.

## 6. Native recording: self-describing CSV first

Choose a new **R1S3 CSV schema v1** as the initial native format: easy to inspect, compatible with the R1 workload, and testable before adding a new binary container. It contains raw counts as well as engineering values. Binary optimization requires throughput/file-size evidence and a new adapter, not a silent change to the CSV contract.

Structure frozen in P1: FILE_FORMAT.md is the normative byte specification. META_CRC32 was added to protect interpretation when END is absent; final totals are in the last row rather than duplicated in END. The following is only a structural overview:

```text
# R1S3_LOG schema=1
# META {JSON session and interpretation metadata}
# META_CRC32 XXXXXXXX
timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd,seq,t_us,vshunt_raw,vbus_raw,temp_raw,quality,Ah_net,Ahc,Ahd
...rows...
# CHECKPOINT {sequence bounds, row count, byte bounds, CRC32}
...rows...
# END {row count, stop reason, digest, clean close}
```

Preserve the first eight R1 column names and semantics where verified. Additional fields are named, typed and versioned. Keep legacy `Whc/Whd` aliases for positive/negative energy; recording metadata defines the actual polarity convention. Define decoded signed 20-bit VSHUNT counts, unsigned VBUS counts and signed temperature counts plus ADC range/LSBs. Missing/invalid fields are empty/null with quality flags, never zero. A skipped opportunity/event and a valid sensor sample must be distinguishable by record/quality semantics.

Metadata includes schema/writer version, firmware commit and dirty-build marker, session ID, board/sensor/shunt identity, units, raw encoding, calibration formulas and applied coefficients, config generation/hash, acquisition settings/actual cadence, timestamp convention and UTC validity, integration/filter policy, test description and channel meanings. No secrets. A clean file remains fully interpretable on another PC with no EEPROM or sibling file.

`t_us` is 64-bit monotonic elapsed microseconds; retain exact integers in the reader. UTC is an optional session anchor with source/uncertainty, not a sample clock. Unknown RTC time stays explicitly unknown; relative recording can be permitted with a visible warning and unique non-time filename. Clock changes during recording are rejected by the first implementation.

Use UTF-8, decimal dot, specified CSV quoting, byte-order mark handling and canonical line endings for native checksums. P1 must define exact CRC32 variant, byte ranges, checkpoint boundaries, summary-digest scope, limits and test vectors shared by writer/reader. Legacy custom checksums remain in their own adapters.

Record to a unique session `.part` file; never overwrite a prior session. Use checked writes, bounded queue, explicit flush policy (initial candidate 1 second) and measured worst-case latency. Advance queue only for acknowledged written bytes; on unresolved write error stop cleanly into ERROR, retain diagnostic state and the partial file. STOP drains, writes final integrity record and closes before rename. Queue overflow produces explicit loss/error, never silent overwrite or fake samples. Rotation parts share session ID and carry independent metadata and part linkage.

Capacity estimate to validate: 200-300 encoded bytes/row at 50 Hz is 10-15 kB/s, approximately 36-54 MB/hour before metadata. Measure the actual encoded size and provision the queue from worst-case SD stalls, with an explicit memory cap and high-water counters; do not assume PSRAM capacity alone solves latency. Rotate below filesystem limits (initial candidate 1 GiB per part), check reserve space before START and periodically, and predict remaining duration using measured bytes/s. Exact limits become profile fields only after testing.

Absent END/partial last line means interrupted recording. Viewer recovers the last verifiable prefix and labels any readable unverified tail; never rewrites the original. CRC detects corruption but cannot guarantee SD/FAT durability under sudden power loss. Establish an empirical loss window and filesystem recovery limits on the actual card.

## 7. One viewer, versioned readers

Architecture: file detection -> format adapter -> normalized session/channels/segments/quality -> analysis -> rendering/export. A new viewer must read old files; that does **not** imply an unchanged old viewer can read new metadata/columns. Offer a separately labelled legacy CSV export for verified old-viewer profiles, disclosing omitted raw data/quality/metadata.

| Family | Detection and acceptance |
|---|---|
| R1 eight-column CSV | Header names/units; metadata before or after header; preserve engineering values, do not calibrate twice |
| Older short/Pss_Wh CSV | Explicit schema adapters derived from writer and fixtures; unresolved Pss meaning is not guessed |
| Headerless CSV | Require a selected/confirmed known mapping when ambiguous; preview before import |
| R1S3 CSV v1 | Magic/schema, bounded metadata, named fields, quality, raw/calibrated channels, integrity and interruption handling |
| LYLI/R2 BIN v2 | Magic, lengths, schema/TLV and actual writer variant; Block64 versus fixed-meta and their exact checksums |
| R3 FILELOG V2 | RFL2/END2 plus DATA/TCHK, DTBM/TCKS and channel/config interpretation from matched writer; no fixed-size assumption copied from LYLI |
| Unknown future version | Report unsupported schema or readable subset explicitly; never silently use an old positional parser |

Normalized model: source format/version, metadata provenance, arbitrary named channels with units and optional raw values, monotonic time, optional UTC, segments, validity/gaps, checksum state, calibration snapshot and recorded versus recomputed totals. This accommodates R3 multi-channel data without changing R1-S3 hardware. Never invent absent current, voltage, raw samples or timezone.

Compatibility corpus: at least one verified specimen per discovered layout plus edge fixtures for BOM, CRLF, comments, quoting, delimiter/decimal variants, reordered/extra columns, blanks, NaN, malformed/truncated rows, resets/concatenated sessions, missing timezone, negative current and damaged checksums. Ambiguous legacy local timestamps require timezone choice or relative-only viewing. Split nonmonotonic sessions; do not join or globally sort away a reset.

Use background/chunked parsing and multiresolution min/max envelopes for large files. Statistics/integration run on valid full-resolution samples, not preview points. Cursor zoom can fetch exact samples. Preserve short peaks. Keep manual markers, ranges, energy/charge and event analysis; port plugins through a versioned API. Battery/starter estimates remain labelled heuristics until separately validated.

Default viewer technology proposal: TypeScript parser/core with a thin UI, using existing Plotly features as donors. Select rendering library in P2 using actual file sizes/marker/peak requirements rather than the newest filename. Deliver an offline build with bundled pinned dependencies and licenses, no CDN requirement. Assess a single-HTML distribution as a packaging requirement; it must still parse using bounded memory. Local-file viewing requires neither device connection nor network service.

## 8. Ordered execution and gates

| Stage | Deliverables | Exit criteria |
|---|---|---|
| P0 — preserve bench baseline | Tag known HWTEST build, hardware wiring note, manual diagnostic build; remove invasive startup tests from production path | Baseline reproducible, EEPROM backup saved, no writes on ordinary boot, ALERT and timing limitations explicit |
| P1 — freeze contracts and fixtures | `CONFIG_SCHEMA.md`, `FILE_FORMAT.md`, `VIEWER_COMPATIBILITY.md`, format/source fixture manifest; native v1 golden files and reference decoder | Exact formulas/units/time/CRC/serialization and legacy mappings testable; native file interpreted without device context |
| P2 — viewer core first | Standalone adapters for R1 families and native v1, normalized model, basic offline plotting/diagnostics | Every R1 fixture maps correct channels/times; comments never become samples; malformed data never becomes zero; ambiguity shown |
| P3 — config and EEPROM | Typed registry, draft/apply/save states, A/B store, import/export and schema upgrades | Roundtrip, bounds, unknown version, corruption and interrupted-save tests; older good slot retained; no writes when unchanged |
| P4 — acquisition and calibration | Production INA driver, measured timing, queue, raw/valid sample contract, offset/gain workflow | Fresh cadence measured under OLED/network load; +/- current and voltage points compared; gap handling and applied settings verified |
| P5 — recorder and self-contained file | Session state machine, checked SD buffering, monotonic energy/charge, metadata/checkpoints/finalization/rotation | Writer->viewer golden roundtrip, unique START names, valid recovery of interrupted files, explicit short-write/full-card/queue faults |
| P6 — device UI and live control | OLED measurement/status screens, minimal Web UI, settings and session controls, versioned live API | READY/RUN/STOPPING/ERROR visible; controls obey state gates; disconnecting browser cannot stop acquisition; offline logs remain usable |
| P7 — operational acceptance | Sustained sessions and interruption tests; validated rate presets; release guide | 1 h baseline-rate run and shorter highest-rate run with audited gaps; restart/SD-full tests; viewer agrees with independently calculated totals |
| P8 — extended legacy binary support | LYLI variants, then R3 FILELOG adapter and advanced plugins | Matched writer/fixture checksums and sample counts, TCHK not plotted as ADC, channel/time provenance correct; publish exact support matrix |

P1/P2 intentionally precede the new recorder: compatibility is a design constraint, not cleanup after files exist. R1-S3 v1 release requires P0–P7 and explicit supported-R1 matrix; overall cross-family viewer work is not declared complete until P8's selected real variants pass. Missing representative binary files are a recorded dependency, not implied support.

State model: BOOT -> READY or DEGRADED/ERROR; READY -> RECORDING -> STOPPING -> READY. Display may continue in degraded mode, but START is gated by INA/config/SD readiness. RTC-invalid behavior follows explicit policy. START/STOP are idempotent; network mutations use explicit commands/POST and session/config revisions rather than state-changing GETs.

## 9. How we follow the plan

- Work on one stage at a time; mark implementation, host tests, hardware tests and owner observations separately.
- Each stage gets a short dated journal entry, evidence links and commit; source archives and raw owner photos/logs remain untouched.
- Do not import whole legacy trees. Port a bounded module only after its data contract and donor behavior are understood.
- Create synthetic or owner-approved de-identified public fixtures; do not publish unrelated recordings, credentials or private notes.
- New requirements go through an explicit plan revision with reason and affected gates. Do not silently change units, sign, time, checksum or file schema.
- Maintain English technical documents/code and Ukrainian owner notes. This plan is the roadmap; `R1_MIGRATION.md` records what actually happened.
- **P0–P2 complete**: see P0_BASELINE.md, CONFIG_SCHEMA.md, FILE_FORMAT.md and VIEWER_COMPATIBILITY.md. P2 uses a local Python/SQLite core to reuse P1 semantics, with bundled browser UI; the TypeScript-only core remains an alternative, not the delivered runtime. See P2_VIEWER.md. Owner correction: the minimal P2 UI does not replace R5. P2.1a graph recovery is implemented. Owner decision on 2026-09-08: **P3 -> P4 -> P5 now**, then resume P2.1b/c with real logger recordings; see [feature matrix](R5_FEATURE_MIGRATION.md). Live/device-log integration retains its P6 firmware dependency. See P3_SETTINGS.md for current firmware implementation and bench evidence. Short/Pss legacy semantics and binary adapters retain explicit evidence gates.
