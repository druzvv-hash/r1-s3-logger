# R1-S3 pin map

Numbers below are **ESP32-S3 GPIO numbers**, not connector pin positions.

| Interface | Signal | GPIO |
|---|---|---:|
| I²C | SDA | 8 |
| I²C | SCL | 9 |
| SD / SPI | CS | 10 |
| SD / SPI | MOSI | 11 |
| SD / SPI | SCK | 12 |
| SD / SPI | MISO | 13 |
| INA228 | ALERT | 14 |

All four I²C devices share the bus. Verify common ground and SDA/SCL pull-ups to 3.3 V, not 5 V. Check the actual INA228 module schematic for ALERT wiring and pull-up requirements before testing.

## I²C addresses

| Device | 7-bit address | Evidence |
|---|---|---|
| INA228 | `0x40` | ID 0x5449/0x2281 and fresh ADC readings confirmed; analog comparison pending |
| SH1106G OLED, 128×64 | `0x3C` | ACK and readable image confirmed; rotation 180° |
| EEPROM 24C32 | `0x50` | ACK and sample write/restore test PASS |
| DS3231 RTC | `0x68` | UTC synchronization and ticking confirmed, OSF=0; time retained after main-power removal |

Repeated scans found all four addresses without bus errors. Address ACK alone does not establish device identity or full functionality. EEPROM address depends on A0–A2; INA228 address depends on its address configuration.

Keep this map and [firmware/include/pins.h](../firmware/include/pins.h) synchronized when wiring changes.

Local encoder A/B/SW: **not assigned, hardware not installed**. The current input adapter is a no-GPIO stub. See [selected encoder](encoder.md) before assigning three new input pins.
