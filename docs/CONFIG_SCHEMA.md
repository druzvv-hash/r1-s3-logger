# Configuration contract v1.1 (v1.0 compatible)

Status: P1 byte contract, now implemented in CONFIG v0.12 firmware; see [P3 results](P3_SETTINGS.md). Normative field registry: [config-v1.json](../schemas/config-v1.json). Reference codec: [contracts.py](../tools/contracts.py). No EEPROM migration/write is performed by these tools.

## Values and lifecycle

Every registered field is mandatory, public and explicitly saved; IDs are permanent and never reused. Reject unknown JSON keys, missing fields, booleans as numbers, nonfinite numbers, out-of-bound values and wrong types. Registry bounds are service limits, not calibrated operating specifications. Normal calibration UI should initially constrain gains to 0.95–1.05, with an explicit service workflow for wider values. `calibration_utc` is empty or `YYYY-MM-DDTHH:MM:SSZ`; the note identifies reference/method. A valid calibration requires a nonempty ID, date and note.

All edits require STOP in v1, including timezone/display preferences, to keep one unambiguous applied snapshot. Lifecycle is draft -> validation -> hardware apply/readback -> explicit save. Failed apply restores the previous applied config; failed save retains the older persisted generation and displays UNSAVED. Defaults never overwrite invalid/unknown slots automatically. Credentials, GPIOs, sensor identity, session annotations, accumulators and counters are not EEPROM settings.

v1.1 extends `requested_rate_hz` to integer 1–300 and `max_gap_us` to 2,000,000 µs. The TLV layout and all defaults are unchanged. Values within the old bounds (10/50/100 Hz and gap ≤1,000,000 µs) retain minor 0; expanded values use minor 1. New readers accept both; older readers protect committed minor-1 slots from writes.

JSON export envelope (legacy-compatible values): `{"schema":"r1s3-config","major":1,"minor":0,"values":{...}}`. Generation belongs to persistence, not an imported profile. Metadata records the applied values and SHA256 of their exact TLV payload. Import previews differences before apply; no automatic save.

Acquisition values are *requested*, not proof of supported cadence. P4 must validate the profile against conversion duration, averaging, sequential channels, I2C/SD traffic and timeout. Code tables are INA228 CT codes 0..7 = 50,84,150,280,540,1052,2074,4120 microseconds; AVG codes 0..7 = 1,4,16,64,128,256,512,1024. These register meanings are also exercised by current hardware diagnostics; production readback and cadence gates remain P4. An unsupported combination cannot START. The host serializer validates representation, not actual hardware timing. Display filter tau=0 disables filtering; positive tau is a display-only first-order filter using actual elapsed time. Offset timezone is fixed minutes, not automatic DST.

## EEPROM slots and bytes

24C32 address space: A `[0x0000,0x0600)`, B `[0x0600,0x0C00)`, reserve `[0x0C00,0x1000)`. Each slot has a 32-byte header, 1472-byte payload area and 32-byte footer. All integers little endian. Unused payload area is `FF`; it is outside CRC and must not be interpreted. No compiler struct serialization.

| Header offset | Type | Meaning |
|---:|---|---|
| 0 | 4 bytes | ASCII `R1CF` |
| 4,6 | u16,u16 | major=1, minor=0 or 1 as above |
| 8,10 | u16,u16 | header length=32, reserved=0 |
| 12 | u64 | generation, 1..2^64-1 |
| 20 | u32 | payload bytes, <=1472 |
| 24 | u32 | CRC32 |
| 28 | u32 | reserved=0 |

CRC32 is IEEE/ISO-HDLC: reflected polynomial `EDB88320`, initial `FFFFFFFF`, final XOR `FFFFFFFF`, check `123456789 -> CBF43926`. Coverage: exact 32 header bytes with bytes24..27 zero, followed by the used payload. Padding and footer excluded.

Footer at slot offset1504: `RCMT` bytes0..3, generation u64 at4, CRC u32 at12, payload length u32 at16, twelve zero bytes at20. All fields must match the checked header. A torn footer is not a committed slot.

Payload is ascending unique TLVs: ID u16, type u8, reserved u8=0, value length u16, reserved u16=0, then value bytes. No alignment/padding between TLVs. Types: 1=u32/4 bytes, 2=i32/4, 3=IEEE754 binary64/8, 4=bool/1 (00 or01), 5=UTF8/variable (no NUL). String maximum is measured in bytes. All 28 IDs are present in v1.0 and v1.1. Major other than 1, minor greater than 1, or unknown IDs are unsupported, not silently skipped. A future reader can add explicitly tested migrations; this reader cannot overwrite an unsupported image.

Boot checks both slots completely, then selects highest generation. Equal generations with unequal payloads are ambiguous and block automatic selection. Equal content/generation selects A. No wrapping: saving after `2^64-1` is refused. If either completed, CRC-valid slot contains an unsupported schema, expose it and inhibit automatic writes even when the other slot is readable. A torn/corrupt header is invalid data, not evidence of a future schema.

## Transaction required in P3

Back up all 4096 bytes before first deployment. Invalidate and verify the inactive footer; write header/payload in <=32-byte page-contained operations, ACK-poll with bounded timeout after each write, read back all used bytes and validate CRC/semantics; write matching footer last and read back. Only then publish persisted generation. Never invalidate the selected good slot. No automatic boot tests, periodic saves or writes when serialized values are unchanged. Test power interruption throughout each page and footer, I2C errors, both-invalid, unsupported schema and maximum generation. CRC detects damage; this is not a claim of atomic physical writes.

## Measurement formulas

`Vshunt_uV = signed20_count * (range0 ? 0.3125 : 0.078125)`.
`Vbus_V = unsigned20_count * 0.0001953125`.
`temperature_C = signed16_count * 0.0078125`.

`I_A = polarity * (Vshunt_uV-i_zero_uV)/shunt_uohm*i_gain`.
`U_V = (Vbus_V-u_zero_V)*u_gain`; `P_W=U_V*I_A`.

No shunt thermal correction without a measured shunt temperature/model. Die temperature is a separate diagnostic channel. Hardware range is not the permitted shunt load. Recorded engineering values are already calibrated; a viewer must not apply coefficients twice.
