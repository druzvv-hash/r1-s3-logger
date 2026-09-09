# R1S3 CSV v2: ecosystem and coarse RTC provenance

Schema 2 adds a frozen `ecosystem` metadata object to the
[CSV v1 byte and measurement contract](FILE_FORMAT.md). The sample columns,
quality bits, monotonic sample clock, calibration snapshot, sign-split energy
integration, checkpoint CRC32, END SHA256 and rotation rules are unchanged.
Both the reference reader and the production viewer accept v1 and v2; an older
v1-only reader must reject v2 rather than guess its interpretation.

This format records who requested a recording and which coarse RTC correction
preceded it. It does **not** assert precise BLE synchronization, a measured clock
offset/drift model, simultaneous group START, or a shared sample clock.

## Version and self-contained parts

The first line is exactly `# R1S3_LOG schema=2` plus LF. META `schema` must be
integer `2`, and all v1 top-level metadata fields remain required. One additional
required field, `ecosystem`, has the exact keys below; its version is integer
`1`. Unknown keys/versions, missing fields, a header/META version mismatch or
reordered/additional native sample columns are rejected.

Every rotated part repeats the complete frozen META, including ecosystem and
RTC correction evidence. `session_id`, recording/group identities, starting UTC
anchor and correction evidence stay fixed across rotation. `part` and
`previous_part_sha256` change according to v1. A part can be inspected alone;
joining its integration interval to a previous part still requires SHA linkage.
Later reconnects or clock changes cannot rewrite an active recording's origin.

## Ecosystem metadata

| Field | Type and meaning |
|---|---|
| `version` | Integer `1`, the ecosystem metadata version inside CSV schema 2. |
| `device_id` | Recording device identity, uppercase six-octet colon-separated MAC form; all-zero forbidden. |
| `boot_id` | Recording device boot identity: nonzero 16-character lowercase hexadecimal string. |
| `recording_id` | Device control-session identity: nonzero 16-character lowercase hexadecimal string. Distinct from the human-readable file `session_id`. |
| `group_id` | Nonzero 16-character lowercase hexadecimal string for a coordinator-requested group, or `null` for a local recording. |
| `coordinator_id` | R3 identity in the same MAC representation, required with `group_id`; otherwise `null`. |
| `coordinator_boot_id` | R3 boot identity, required with `group_id`; otherwise `null`. |
| `rtc_correction` | Last successful R3-derived RTC correction captured at recording start, or `null`. Exact structure below. |

A local recording can carry R3 clock correction evidence without belonging to
any remote-control group. Conversely, a group identity alone proves neither
clock correction nor a successful recording on every selected device. Device,
boot and session identities are provenance, not credentials or authentication
proof in an exported file. No BLE keys, PINs or local access tokens are stored.

## UTC interpretation and correction evidence

`time.utc_anchor` and row timestamps retain v1's fixed-anchor-plus-monotonic-delta
calculation. In schema 2, a known calendar anchor may have
`time.uncertainty_us: null`: UTC exists but its uncertainty has not been qualified.
The viewer reports this explicitly. `null` must never be interpreted as zero
error, microsecond accuracy, a precise time lock, or an unknown calendar value.

The device writer emits `time.source: "DS3231"` for a local RTC anchor without
recorded R3 correction, and `"DS3231/R3"` when the RTC has recorded R3 correction
evidence. The latter describes provenance; it does not prove that R3 is currently
connected or the downstream clock has no accumulated drift. Current schema 2
writer output uses unknown uncertainty for both cases. Schema 1 retains its
existing explicit uncertainty behavior.

Unknown calendar time remains `utc_anchor: null`, source `"unknown"`, empty row
timestamps and quality bit 3 set, and requires `allow_unknown_utc=true`.
Historical correction evidence may remain present even when the current calendar
anchor is unavailable; it must not make that anchor valid.

When non-null, `rtc_correction` has exactly these fields:

| Field | Type and meaning |
|---|---|
| `authority_id`, `authority_boot_id` | R3 identity and boot in the representations above. |
| `clock_revision` | Unsigned 32-bit integer identifying the R3 clock revision. |
| `request_id` | Nonzero 16-character lowercase hexadecimal string identifying the correction request. |
| `unix_s` | R3 UTC seconds supplied for the correction; integer `946684800 <= value < 4102444799`. |
| `received_local_us` | Downstream monotonic receive time, encoded as a canonical decimal u64 **string**. |
| `applied_local_us` | Downstream monotonic application time, same representation; receive-to-apply delay must be within `0..1000000` us. |
| `source_capture_us` | R3 monotonic capture time as a canonical decimal u64 string, or `null` if unavailable. It belongs to the R3 boot's clock domain. |
| `source_read_age_ms` | Unsigned integer `0..1500`: age of the source RTC observation reported by the correction exchange. |
| `roundtrip_us` | Unsigned integer `0..1000000`: observed request/response roundtrip. |
| `uncertainty_us` | Must be `null` for this coarse correction path. |

Decimal u64 strings have no sign, whitespace or leading zeros except the single
string `"0"`; the maximum is `"18446744073709551615"`. Strings preserve values
above JavaScript's exact integer range. Local receive/application timestamps
may be subtracted because they belong to one downstream boot. Source capture
time must not be subtracted from them as if both devices shared a clock.

The acceptance age limits bound this correction workflow; they are not a
measured accuracy or transport-symmetry guarantee. Both uncertainty fields must
remain `null` when correction evidence is present. A known UTC source of
`"DS3231/R3"` requires that evidence, and known UTC with correction evidence
requires that source label. Missing/malformed identities, expired ages or
inconsistent provenance are errors, even if the file's CRC and SHA are valid.

## Validation

[Host serializer tests](../tests/recording_format_host.cpp) produce actual C++
writer files for local, remotely started, locally started after correction,
unknown-calendar and rotated sessions. The
[roundtrip tests](../tests/test_recording_format.py) open these files with the
reference reader and production viewer and check unchanged sample timing,
complete repeated evidence, part SHA linkage and integrity failures.
[Contract tests](../tests/test_contracts.py) also construct deliberately invalid
metadata with otherwise valid byte checksums: both readers must reject wrong
versions, identities, source/uncertainty claims and expired correction evidence.
The existing v1 golden corpus is retained unchanged.

Precise S2 clock mappings, raw synchronization observations and discontinuity
records require their own qualified extension; this static provenance object
does not implement those records. See [ecosystem time](ECOSYSTEM_TIME_SYNC.md).
