# HWTEST v0.6 firmware

PlatformIO + Arduino for ESP32-S3 N32R16V. Run commands from the repository root. See the [main README](../README.md) for build and upload environments.

- `src/main.cpp`: memory information, repeated I²C scans, SD test and SH1106G 128×64 OLED rotated 180°.
- `src/eeprom_test.cpp`: 24C32 backup to SD, sample write, restoration and full-image comparison.
- `src/rtc_test.cpp`: read-only DS3231 calendar/BCD, temperature, OSF/EOSC and tick checks.
- `include/pins.h`: GPIO constants matching [hardware/pinmap.md](../hardware/pinmap.md).

The SD test retains its v0.2 payload and creates a new file on every boot. The RTC test never sets time. The EEPROM write test is temporary diagnostic code; keep power connected until restoration completes.

The default environment is `esp32-s3-uart-manual`. Automatic UART reset and experimental native USB environments remain in `platformio.ini`. Firmware builds passed; reliable bootloader entry is still unresolved. See [bring-up results](../docs/bring-up.md).
