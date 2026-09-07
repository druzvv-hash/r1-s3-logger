# BASE v0.11 firmware

PlatformIO + Arduino for ESP32-S3 N32R16V. Run commands from the repository root. See the [main README](../README.md) for build and upload environments.

- `src/main.cpp`: memory information, repeated I²C scans, SD test and SH1106G 128×64 OLED rotated 180°.
- `src/eeprom_test.cpp`: 24C32 backup to SD, sample write, restoration and full-image comparison.
- `src/rtc_test.cpp`: read-only DS3231 calendar/BCD, temperature, OSF/EOSC and tick checks.
- `include/pins.h`: GPIO constants matching [hardware/pinmap.md](../hardware/pinmap.md).

Ordinary builds only read SD/EEPROM. `esp32-s3-service` explicitly enables the legacy SD file and EEPROM pattern/restore tests. Periodic checks never set time; the explicit browser command does. See [RTC sync](../docs/rtc-sync.md). The EEPROM write test is temporary diagnostic code; keep power connected until restoration completes.

The default environment is `esp32-s3`; manual UART remains a fallback. Automatic UART reset and experimental native USB environments remain in `platformio.ini`. Automatic UART uploads passed after USB-UART controller rework; long-term reliability remains to be established. See [bring-up results](../docs/bring-up.md).

- `src/ina228_test.cpp`: identity, fresh triggered VBUS/VSHUNT/temperature sample, ADC_CONFIG restoration and passive ALERT level. See the [migration journal](../docs/R1_MIGRATION.md) for test side effects and acceptance limits.

- `include/shunt_config.h`: nominal 60 mV / 400 A shunt; signed current conversion with compile-time checks. Current is printed in Serial and is not yet calibrated against a reference.

- `src/storage_check.cpp`: read-only SD-independent EEPROM checks and `EEPROM DUMP` backup transport. See [P0](../docs/P0_BASELINE.md).
