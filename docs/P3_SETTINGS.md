# P3 — firmware configuration and 24C32 persistence

Implemented in CONFIG v0.12. Firmware settings use the exact [P1 contract](CONFIG_SCHEMA.md) and [28-field registry](../schemas/config-v1.json). `tools/generate_config.py` generates the C++ fields, bounds and TLV codec; the generated files are committed and checked for drift. No compiler-struct serialization is used. The host compares C++ slot bytes with the Python reference and golden fixture.

## Lifecycle and hardware apply

Boot reads both slots without writing. A verified supported highest generation becomes the draft and is applied to INA228; absent valid settings expose nominal defaults as UNSAVED. Future schemas, conflicting equal generations and read failures block saves. No schema migration is guessed. `draft -> APPLY -> SAVE` are separate explicit operations. Import changes only the draft. Failed apply restores old INA CONFIG/ADC_CONFIG; failed restoration latches measurement off until reboot. Failed save exposes UNSAVED/uncertain persistence while retaining the previously published generation.

INA apply checks identity and theoretical conversion duration, puts the ADC into shutdown, sets range/conversion times/averaging, clears conversion delay and reads registers back. Diagnostic measurements explicitly trigger with these settings and apply shunt/polarity/offset/gain formulas from the contract. OLED contrast, refresh frequency and display-only filter are applied. The diagnostic measurement cadence is still approximately 1 Hz: requested 10/50/100 Hz and live/queue/rotation/flush/UTC-policy fields are stored for P4–P6, **not evidence that production recording exists**. No current calibration was performed by saving nominal values.

All mutations require STOP through `setSettingsRecording`; no START/recorder command exists in this stage. P5 must wire its state transitions into this guard and require INA/SD/RTC/config readiness. Firmware UI/forms and recording metadata are later consumers of the same applied snapshot.

## A/B transaction

Slots occupy 0x0000–0x05FF and 0x0600–0x0BFF; 0x0C00–0x0FFF stays untouched. The inactive footer is invalidated and read back first. Header/used payload writes are <=32 bytes and never cross a page, with bounded ACK polling after each. Used bytes are read back before the commit footer is written last; the completed slot must pass CRC, generation and semantic checks. Unused payload padding is outside the contract CRC and is not rewritten. Matching serialized values skip writes. No generation wrapping or automatic repair/boot save.

The EEPROM adapter follows the [24LC32A page-write and ACK-polling description](https://ww1.microchip.com/downloads/en/DeviceDoc/24AA32A-24LC32A-32-Kbit-I2C-Serial-EEPROM-20001713N.pdf); the installed module was identified by function as 24C32, not by an electronic manufacturer ID. INA register fields follow the [INA228 datasheet](https://www.ti.com/lit/ds/symlink/ina228.pdf). Actual physical brownout behavior remains a separate bench test; byte-cut simulation does not certify the hardware.

## Profile workflow

Use Python with pyserial (the existing PlatformIO Python includes it). Close other COM5 monitors. Run from the repository root; change `--port` if necessary:

```text
python tools/settings.py status
python tools/settings.py export profile.json
python tools/settings.py import edited-profile.json
python tools/settings.py apply
python tools/settings.py save
```

Exports are complete versioned JSON envelopes and never overwrite an existing file. Import validates types/fields/units contract and prints differences from the applied values, then transfers a CRC-checked draft and verifies it by readback. Use `export draft.json --source draft` or `--source persisted` to inspect each state. `defaults` changes the draft only. `save` creates a new private 4096-byte backup plus checksum manifest under Documents/R1-S3 Backups before sending SAVE, then compares persisted versus applied bytes. The raw UART command bypasses this host backup helper; boot and import never save implicitly. The CLI is the current service workflow; broad coefficient bounds are not a normal calibration UI.

UART protocol, newline terminated, bounded 159-byte lines:

- `CONFIG STATUS`, `CONFIG GET`, `CONFIG DRAFT`, `CONFIG PERSISTED`: read state or a TLV dump with SHA256, ordered 32-byte HEX chunks and END.
- `CONFIG BEGIN <bytes>`; `CONFIG HEX <offset-hex> <up-to-32-byte-hex>`; `CONFIG END <CRC32-hex>`: replace draft only after complete validation, <=1472 bytes.
- `CONFIG DEFAULTS`, `CONFIG APPLY`, `CONFIG SAVE`: explicit mutations. Incomplete transfers cannot APPLY/SAVE.
- Existing `EEPROM DUMP` and `TIME UTC ...` remain available.

## Evidence — 2026-09-08

- 33 host tests passed. The native C++ test executes the same store/codec/INA apply code as firmware. It tests cuts after every transaction byte, read failures, acknowledged-but-protected EEPROM writes, unchanged saves, no-valid-slot defaults, unknown version/ID, torn CRC, equal-generation conflict, maximum generation and untouched active slot/reserve. INA faults verify rollback, failed-rollback latching and identity rejection. This is simulated fault coverage, not physical power cuts.
- C++ serialized defaults and a changed UTF-8/calibration profile exactly match P1 Python slot bytes. Registry generation is checked. Native tests require g++ (`R1_HOST_CXX` can select it); they explicitly skip if no host compiler is available.
- Normal and service firmware builds passed; only normal firmware was uploaded over automatic UART/COM5 with flash hashes verified.
- Fresh pre-deployment full backup matched P0: CRC32 8C31ED44, SHA256 78c5017e9cac1ce1807b838a3c168c10e8ab1776354b7e68abdaaa1b10cd8545. First v0.12 boot left this image unchanged.
- Physical board: impossible averaging/timeout profile rejected; draft did not alter applied settings. Saved defaults to A generation 1, changed only OLED contrast to B generation 2, then restored defaults to A generation 3. Previous good slot and reserve compared unchanged at each transition. Repeated unchanged SAVE left the complete EEPROM image identical.
- Reset restored SAVED generation 3 and exact default payload. Full EEPROM remained unchanged after reboot, CRC32 EBDAE9A1. INA identity/readback and fresh ADC resumed. No physical interruption during EEPROM write and no calibration/load-accuracy claim.

Next: P4 production acquisition, timestamps/raw/quality, queue and measured cadence, followed by P5 self-contained files. Owner deferred further viewer work until these files exist.
