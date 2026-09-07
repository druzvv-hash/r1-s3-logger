# Hardware

The current bench consists of an ESP32-S3 board and external INA228 module, shared I²C peripherals and SPI SD storage. Initial supply checks were reported as normal; a complete numerical measurement record is still needed.

- [Pin map](pinmap.md)
- [Bring-up plan and results](../docs/bring-up.md)

The owner reports ESP32-S3-WROOM-2-N32R16V (MCN32R16V): 32 MB Octal Flash / 16 MB Octal PSRAM. Firmware detects 32 MiB Flash and approximately 16 MiB PSRAM; no stress test has been performed. The bench CP210x USB–UART bridge currently appears as COM5 on Windows.

Store schematics, BOM, wiring photos and shunt specifications here as they become available. No schematic or PCB files are included yet. Record the exact board revision, SH1106G OLED and DS3231 module wiring, SD module power circuitry, shunt resistance and allowable current.

## External shunt

Owner-confirmed on 2026-09-07: **60 mV / 400 A**, nominal **150 microohms (0.00015 ohm)**; owner reports it connected. HWTEST v0.9 uses this nominal resistance for signed current from VSHUNT. This is not measured calibration. Wiring/polarity, shunt tolerance and temperature coefficient remain to be recorded. See [migration journal](../docs/R1_MIGRATION.md).
