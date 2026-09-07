# P0: preserved baseline and non-writing storage checks

Completed 2026-09-07. Annotated tag `hwtest-v0.10` preserves commit `de37e6d`, the live OLED/INA228 bench baseline. Its built firmware.bin/ELF, PlatformIO config and SHA256 manifest were additionally saved outside this repository. Baseline wiring and owner evidence remain in [migration journal](R1_MIGRATION.md) and [pin map](../hardware/pinmap.md).

Current **BASE v0.11** retains one-second INA228 diagnostics/live OLED, 180-degree SH1106, periodic I2C/RTC and explicit RTC synchronization. Ordinary boot mounts and reads the SD root, then reads EEPROM twice and compares all 4096 bytes. No SD test file or EEPROM pattern write is performed. This is still bring-up firmware, not production acquisition/recording or an EEPROM settings implementation. OLED `READ` means a read check, not a new write-test PASS.

| Environment | Purpose |
|---|---|
| `esp32-s3` (default) | Automatic UART upload, normal non-writing storage checks |
| `esp32-s3-uart-manual` | Same normal application, BOOT/RESET fallback, no esptool reset |
| `esp32-s3-usb` | Same normal application through experimental native USB; not bench-validated |
| `esp32-s3-service` | Explicit service build; creates SD test/backup files and performs original EEPROM write/restore test |

Normal builds exclude `eeprom_test.cpp` and compile out the SD write test. Do not deploy the service profile once production settings occupy EEPROM without revisiting its permitted test area. Existing service guard/backup/restore behavior is retained, not a general-purpose persistence guarantee. Current storage checks do not claim a physically write-protected SD driver; the application opens only the root for reading and disables format-on-failure.

## Backup

Close Serial Monitor/Termite, then run using a Python environment with pyserial:

```text
python tools/backup_eeprom.py <private-directory>/eeprom-backup.bin --port COM5
```

Firmware command `EEPROM DUMP` reads twice before reporting offset-tagged hex and CRC. Host requests two full dumps, validates offsets/length/CRC and exact match, then creates a new binary and JSON manifest without overwriting existing backup files. Nothing is written to EEPROM or SD. Keep the backup private; it can contain earlier settings.

Bench backup: 4096 bytes, CRC32 `8C31ED44`, SHA256 `78c5017e9cac1ce1807b838a3c168c10e8ab1776354b7e68abdaaa1b10cd8545`; two independently requested dumps matched (each itself checked two reads). Binary stored outside Git. Post-reset startup CRC matched this backup.

## Verification and limits

Normal and service builds passed. Only normal v0.11 was uploaded; automatic UART upload succeeded with flash hash verification. A subsequent reset capture showed SD READ, EEPROM READ with matching CRC, all four I2C addresses without bus errors, INA228 ADC OK and RTC tick PASS. See [capture](p0-v0.11-serial.txt). Application source/build separation establishes absence of the startup write tests; no SD bus trace or power-cut durability claim is made.

Owner-reported low-side wiring: IN+ to load-return shunt sense, IN- and module GND to supply-negative shunt sense, VBUS to supply positive, VIN+-VBUS jumper open. Module R015 removed by owner. Not independently inspected. Nominal shunt is 150 microohms, no new gain/offset correction.

Active ALERT functionality remains untested (passive GPIO14 LOW only). Sustained fresh-sample cadence, SD latency, temperature drift and independent current calibration are P4/P7 gates. The approximately one-second test loop is not the proposed 50 Hz recorder.
