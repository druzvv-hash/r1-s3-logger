# R1S3 CSV v1 contract

P1 specification and executable host reference, implemented by the [v0.18 SD recorder](P5_RECORDING.md). [Golden files and expected results](../tests/fixtures/manifest.json), [reference encoder/decoder](../tools/contracts.py), [configuration](CONFIG_SCHEMA.md). Examples contain synthetic data only.

## Byte grammar

UTF-8 without BOM, LF only, decimal dot, comma delimiter. One physical line per record. CSV uses standard double-quote escaping, no embedded CR/LF. Floating values must be finite; write sufficient precision to meet `abs_error <= max(1e-9, abs(expected)*1e-8)`. Integers are decimal, never exponent notation. Empty means unavailable, not zero. JSON control records use unique keys, finite numbers, no NaN/Infinity; canonical writer sorts keys and omits insignificant whitespace. CRC uses actual stored bytes, not reserialized JSON.

Order:

1. Exact `# R1S3_LOG schema=1` plus LF.
2. `# META ` plus a single JSON object plus LF, maximum 16384 bytes including prefix/LF.
3. `# META_CRC32 ` plus eight uppercase hex digits plus LF; IEEE CRC32 over **the entire preceding META line**, prefix and LF included. Variant/test vector in CONFIG_SCHEMA.md. This protects metadata even when END is absent.
4. Exact header below, plus LF.
5. 1..1024 sample rows, then CHECKPOINT; repeat. Normal writer target is 256 rows/block, final block may be shorter. Sample line <=4096 bytes, control line <=1024 bytes.
6. END after the last checkpoint, then EOF. A zero-row clean session can have END directly after the header.

```text
timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd,seq,t_us,vshunt_raw,vbus_raw,temp_raw,quality,Ah_net,Ahc,Ahd
```

Native v1 has exactly these columns; reordered/extra native columns require a versioned extension. Legacy readers use a different, header-based contract. Unknown versions are rejected as unsupported rather than parsed positionally.

## Self-contained metadata

All top-level fields below are required. The synthetic golden META is a complete concrete example. Do not include credentials, local paths or private device access tokens.

| Field | Contract |
|---|---|
| `schema` | integer 1 |
| `session_id` | nonempty unique session string, shared across rotation parts |
| `part`, `previous_part_sha256` | nonnegative part index; null for first, preceding complete-file SHA256 otherwise |
| `writer` | name, version, commit strings and boolean dirty; exact firmware provenance, synthetic marker only for fixtures |
| `hardware` | board, sensor=`INA228`, sensor_address, manufacturer_id, device_id, topology and shunt_nameplate |
| `config` | complete applied registry values, not draft values; interpretation does not require EEPROM |
| `config_generation`, `config_sha256` | positive generation and SHA256 of exact config TLV payload defined in CONFIG_SCHEMA.md |
| `acquisition` | requested_hz, measured_hz (null until measured), adc_config actual/readback register, timestamp_note describing sequential channels; settings are frozen for the file |
| `time` | utc_anchor (ISO UTC with six fractional digits, or null), anchor_t_us (u64), uncertainty_us (nonnegative or null), source, sample_point=`conversion-ready-observed` |
| `raw` | vshunt=`signed20`, vbus=`unsigned20`, temp=`signed16`; vshunt_uV_lsb according to applied adc_range, vbus_V_lsb=0.0001953125, temp_C_lsb=0.0078125 |
| `units` | exact named map in golden file: A,V,W,Wh,Ah,us,ms; raw counts are dimensionless |
| `integration` | exact `trapezoid-sign-split-no-gap-v1` |
| `description` | public session description, may be empty |

Raw counts are decoded numbers: remove four reserved low bits from INA228 VSHUNT/VBUS registers before sign extension/scaling; temperature uses signed16. Formulas and shunt polarity are in CONFIG_SCHEMA.md. INA228 conversion/register definitions were checked against the [TI datasheet, register maps](https://www.ti.com/lit/ds/symlink/ina228.pdf). Raw and engineering values coexist; a reader checks consistency and must not calibrate engineering values again.

## Time, validity and integration

`seq` is a u64 measurement-opportunity sequence, increasing strictly. It can skip when opportunities are lost; it never restarts within a session. `t_us` is a u64 session-relative monotonic observation time, increasing strictly, not RTC-derived. `ms_from_start=floor(t_us/1000)`. Rotation keeps session-relative times, sequence and cumulative totals. Samples are timestamped when ready is observed; sequential ADC channels are not simultaneous.

When UTC is valid, timestamp is `YYYY-MM-DDTHH:MM:SS.ffffffZ` calculated from the META anchor and exact monotonic delta. RTC anchor uncertainty remains explicit; formatting microseconds does not imply RTC microsecond accuracy. Unknown UTC: empty timestamp, null anchor/uncertainty, source=`unknown`, quality bit3 on every row. START with unknown UTC requires `allow_unknown_utc=true`. Time/config changes require a new session.

| Quality bit | Meaning |
|---:|---|
| 0 / 1 | Invalid measurement: I_A/U_V/P_W empty; available raw evidence may remain |
| 1 / 2 | Gap before this row: lost sequence or elapsed time above max_gap_us; no integration across it |
| 2 / 4 | ADC saturated; also set INVALID |
| 3 / 8 | UTC unknown |
| 4 / 16 | Cumulative totals incomplete, sticky until next session |

Unknown bits are unsupported. Raw rails are invalid/saturated even if numeric scaling fits. A failed measurement can have an explicit invalid row; opportunities with no stored row are represented by a sequence jump/GAP. Both make totals incomplete. Invalid raw values can be empty; a valid row requires all raw and engineering fields. Zero is allowed only when actually measured/calculated.

Totals start at zero at the first sample of a session. For adjacent valid rows with no GAP, integrate actual elapsed seconds: `(a+b)/2 * dt / 3600`, using power for Wh, current for Ah. If endpoints have opposite signs, split at linear zero crossing `abs(a)/(abs(a)+abs(b))`. Accumulate positive and absolute-negative areas separately. Whc/Whd and Ahc/Ahd are nonnegative; net is positive minus negative. INVALID intervals and gaps leave totals unchanged; no extrapolation before first/after last sample. First row after rotation carries previously accumulated totals; no integration between files until part linkage is verified. Totals remain present even when incomplete. Covered/missing duration can be reconstructed from row quality and timing; unknown pre-first/post-last losses cannot be claimed measured. P2 exposes recorded and recomputed totals separately.

## Integrity and interrupted files

`# CHECKPOINT {"start":...,"end":...,"rows":...,"first_seq":...,"last_seq":...,"crc32":"XXXXXXXX"}` plus LF. `start` is absolute zero-based byte offset of the first sample row of this block, `end` is exclusive offset immediately after its last LF. These bounds exclude the checkpoint itself. CRC covers exact sample bytes `[start,end)`. Blocks partition all rows; no uncounted rows, overlap or empty blocks. Sequence endpoints and row count must match decoded rows.

`# END {"rows":N,"sha256":"...","clean":true,"reason":"stop"}` plus LF. `rows` counts all rows in this part, including invalid rows. SHA256 covers **every byte before `# END `**, including magic, metadata, checksums, header, samples and checkpoints. Reason is `stop` or `rotation`. No bytes follow END. Session totals are available in the last sample; no duplicated final-total interpretation is needed.

No END means interrupted, not clean. Return checkpoint-verified rows separately from any complete but unverified trailing rows; discard incomplete last row from numeric data and report its presence. A malformed complete row, mismatching checkpoint or bad END is corruption, never a clean partial success. The P1 reference fails explicitly on corruption; P2 may offer a separately labelled valid-prefix recovery report without changing the source file. CRC/SHA detect corruption, not malicious authenticity or guaranteed SD/FAT power-loss durability.

## Future ecosystem synchronization

[R3 / R1-S3 / CAN synchronization](ECOSYSTEM_TIME_SYNC.md) requires a separately
versioned extension for clock mappings, raw beacon/exchange evidence, uncertainty
and discontinuities. Schema 1 has no such records; its frozen time anchor and
exact byte grammar remain unchanged. Do not mark existing files synchronized
merely because BLE was connected. New writers and readers must ship together
with golden fixtures and retain v1 compatibility.

## Reference scope and verification

`python tools/contracts.py tests/fixtures/native-sign-crossing.csv` reports four verified rows and clean=true. `python -m unittest discover -s tests -v` checks signed conversion, zero crossing, invalid/gap behavior, raw/value consistency, config bytes, CRC, torn slot fallback and file interruption/corruption. `python tools/make_contract_fixtures.py` regenerates the synthetic corpus deterministically.

Reference decoder deliberately limits whole files to 16 MiB. The production P2 reader must stream/chunk and retain min/max previews with full-resolution analysis. This reference is the interchange oracle, not a claim that an unchanged old viewer supports native v1. The current device writer and current viewer both implement this contract.
