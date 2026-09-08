# PANEL v0.19 firmware

PlatformIO + Arduino for ESP32-S3 N32R16V. Run commands from the repository root. See the [main README](../README.md) for build and upload environments.

The [device test panel](../docs/P4A_TEST_PANEL.md) now provides USB/Wi-Fi controls.
The hardware owner remains core 1; the web task on core 0 uses snapshots and commands.
I²C scanning after startup is explicit, not periodic. Timed 10/50/100 Hz sampling,
chunked OLED and PSRAM live preview are implemented. [Session recording](../docs/P5_RECORDING.md) uses the PSRAM FIFO and checked SD block writes.
See [cadence and transport](../docs/P4B_LIVE_ACQUISITION.md).
Existing SD files can now be downloaded through the panel; the dedicated storage
owner is in `sd_files.cpp`. See [file transfers](../docs/SD_DOWNLOADS.md).

- `src/main.cpp`: memory information, explicit I²C scans, SD test and SH1106G 128×64 OLED rotated 180°.
- `src/eeprom_test.cpp`: 24C32 backup to SD, sample write, restoration and full-image comparison.
- `src/rtc_test.cpp`: read-only DS3231 calendar/BCD, temperature, OSF/EOSC and tick checks.
- `include/pins.h`: GPIO constants matching [hardware/pinmap.md](../hardware/pinmap.md).

Ordinary boot only reads SD/EEPROM. Explicit CONFIG SAVE writes settings; see [P3 workflow](../docs/P3_SETTINGS.md). `esp32-s3-service` explicitly enables the legacy SD file and EEPROM pattern/restore tests. Periodic checks never set time; the explicit browser command does. See [RTC sync](../docs/rtc-sync.md). The EEPROM write test is temporary diagnostic code; keep power connected until restoration completes.

The default environment is `esp32-s3`; manual UART remains a fallback. Automatic UART reset and experimental native USB environments remain in `platformio.ini`. Automatic UART uploads passed after USB-UART controller rework; long-term reliability remains to be established. See [bring-up results](../docs/bring-up.md).

- `src/ina228_test.cpp`: identity, fresh triggered VBUS/VSHUNT/temperature sample, ADC_CONFIG restoration and passive ALERT level. See the [migration journal](../docs/R1_MIGRATION.md) for test side effects and acceptance limits.

- `include/shunt_config.h`: historical nominal shunt checks. Runtime conversion now uses `appliedSettings()` with validated polarity, shunt, offsets and gains.
- `settings_core.cpp`: portable TLV/CRC/A-B store, INA apply/readback/rollback.
- `settings.cpp`: 24C32 adapter and STOP-only draft/apply/save UART workflow.
- `config_fields.h` and `config_codec_generated.inc`: generated from schemas/config-v1.json. Regenerate with tools/generate_config.py; do not hand-edit.
- `local_input.cpp`: no-hardware encoder stub; no GPIO accessed. [Selected encoder](../hardware/encoder.md).
- `recording_buffer.cpp`: SPSC numeric FIFO and checked block-output primitives; `recording_memory.cpp` reserves PSRAM payload plus an 8 KiB internal DMA-capable staging buffer at boot. Acquisition/SD owners are not yet connected to them. [Reuse evidence and limits](../docs/BUFFERING_AND_REUSE.md).

- `src/storage_check.cpp`: read-only SD-independent EEPROM checks and `EEPROM DUMP` backup transport. See [P0](../docs/P0_BASELINE.md).
