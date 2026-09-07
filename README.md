# R1-S3 Logger

**English** | [Українська](README.uk.md)

Rebuilding Logger R1 around **ESP32-S3 + INA228**. Current firmware: **BASE v0.11**, with live measurements and non-writing storage checks. The original R1 application has not been ported yet.

## Hardware

- ESP32-S3-WROOM-2-N32R16V (reported marking MCN32R16V): 32 MB Octal Flash, 16 MB Octal PSRAM.
- Shared I²C bus: SDA GPIO8, SCL GPIO9, 100 kHz; INA228 `0x40`, SH1106G 128×64 OLED `0x3C`, 24C32 EEPROM `0x50`, DS3231 RTC `0x68`.
- SPI SD: CS GPIO10, MOSI GPIO11, SCK GPIO12, MISO GPIO13.
- INA228 ALERT: GPIO14. External shunt: owner-confirmed 60 mV / 400 A (150 microohms).
- OLED rotation: 180°. The current bench uses a CP210x USB–UART bridge.

See the [pin map](hardware/pinmap.md). Board revision and SD module circuitry remain to be recorded.

## Verified status

| Component | Result |
|---|---|
| Flash / PSRAM | Detected; no memory stress test performed |
| I²C | Four expected addresses responding in repeated scans without bus errors |
| SD | 10 MHz write, close, remount and exact readback PASS; output files checked on a PC |
| OLED | SH1106G 128×64 image and 180° rotation confirmed by the owner |
| EEPROM | Owner confirmed EEP PASS: backup, sample write, restore and full-image comparison |
| RTC | Browser UTC synchronization verified; OSF=0, tick PASS; retention checked after owner-reported power disconnection |
| INA228 | Fresh ADC and owner-reported voltage comparison established; independent current calibration and active ALERT pending |

Automatic UART uploads succeeded after USB-UART controller rework. The cause of earlier intermittent bootloader failures remains unproven; native USB operation is not confirmed.

## VS Code / PlatformIO

Open the repository root in VS Code with PlatformIO IDE installed. Dependencies are pinned to `espressif32@6.12.0` (Arduino 2.0.17) and `Adafruit SH110X@2.1.12`.

```sh
pio run
```

The default environment is `esp32-s3`: automatic UART upload, CDC disabled, COM5 at 115200 baud. Close Termite / Serial Monitor before uploading. Change the port for another workstation.

```sh
pio run -e esp32-s3 -t upload
pio device monitor -e esp32-s3
```

`esp32-s3-uart-manual` retains the BOOT + RESET fallback (manual RESET after upload). `esp32-s3-usb` is an unverified native-USB alternative. The explicit `esp32-s3-service` build enables the original SD/EEPROM write tests; ordinary builds exclude them.

## Current behavior and migration

Normal boot reads the SD root and checks two complete EEPROM reads, then displays live voltage/current. It creates no SD test files and writes no EEPROM patterns. `SD READ / EEP READ` indicate read checks. The explicit [RTC sync](docs/rtc-sync.md) command remains available. INA228 still uses the diagnostic conversion/restore path; production recording is pending.

[P0 baseline and backup evidence](docs/P0_BASELINE.md). P1 contracts: [settings/EEPROM](docs/CONFIG_SCHEMA.md), [self-contained CSV](docs/FILE_FORMAT.md), [viewer compatibility](docs/VIEWER_COMPATIBILITY.md). Run host checks with `python -m unittest discover -s tests -v` (Python 3.10+; standard library). Next stage: P2 offline viewer core.

## Repository guide

- [firmware/](firmware/README.md): Arduino test firmware and GPIO constants.
- [hardware/](hardware/README.md): hardware notes and pin map.
- [Bring-up plan and results](docs/bring-up.md).
- [SD serial evidence](docs/sd-test-v0.2-serial.txt).
- [Project context](docs/project-context-review.md): relevant findings from earlier logger work.
- [Ukrainian owner notes](docs/uk/README.md): historical bench notes and local workspace review.

See the staged plan below for remaining acquisition, calibration, ALERT and recording acceptance work.

Legacy recovery: [R1 firmware and viewer review](docs/legacy-r1-analysis.md).

- [Migration journal](docs/R1_MIGRATION.md): migration stages, decisions and dated hardware evidence.

- [Engineering plan](docs/R1_S3_PLAN.md): architecture, EEPROM, self-contained recording and cross-version viewer roadmap.
