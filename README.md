# R1-S3 Logger

**English** | [Українська](README.uk.md)

Rebuilding Logger R1 around **ESP32-S3 + INA228**. Current firmware: **HWTEST v0.7**, focused on hardware bring-up. The original R1 application has not been ported yet.

## Hardware

- ESP32-S3-WROOM-2-N32R16V (reported marking MCN32R16V): 32 MB Octal Flash, 16 MB Octal PSRAM.
- Shared I²C bus: SDA GPIO8, SCL GPIO9, 100 kHz; INA228 `0x40`, SH1106G 128×64 OLED `0x3C`, 24C32 EEPROM `0x50`, DS3231 RTC `0x68`.
- SPI SD: CS GPIO10, MOSI GPIO11, SCK GPIO12, MISO GPIO13.
- INA228 ALERT: GPIO14. External shunt specifications are still to be documented.
- OLED rotation: 180°. The current bench uses a CP210x USB–UART bridge.

See the [pin map](hardware/pinmap.md). Board revision, SD module circuitry and shunt ratings remain to be recorded.

## Verified status

| Component | Result |
|---|---|
| Flash / PSRAM | Detected; no memory stress test performed |
| I²C | Four expected addresses responding in repeated scans without bus errors |
| SD | 10 MHz write, close, remount and exact readback PASS; output files checked on a PC |
| OLED | SH1106G 128×64 image and 180° rotation confirmed by the owner |
| EEPROM | Owner confirmed EEP PASS: backup, sample write, restore and full-image comparison |
| RTC | Browser UTC synchronization verified; OSF=0, tick PASS; battery retention pending |
| INA228 | Address ACK only; functional testing pending |

Bootloader entry remains intermittent: successful uploads and No serial data / Wrong boot mode errors have both occurred. The cause is unresolved. BOOT/EN measurements are the next diagnostic step; native USB operation is not confirmed.

## VS Code / PlatformIO

Open the repository root in VS Code with PlatformIO IDE installed. Dependencies are pinned to `espressif32@6.12.0` (Arduino 2.0.17) and `Adafruit SH110X@2.1.12`.

```sh
pio run
```

The default environment is `esp32-s3-uart-manual`: UART console, CDC disabled, 115200 baud, and esptool reset sequences disabled before and after upload. `COM5` is the current bench setting; change the UART environment ports in `platformio.ini` for another workstation.

Close Termite / Serial Monitor. With the UART cable connected, hold BOOT, press and release RESET, then release BOOT before uploading:

```sh
pio run -e esp32-s3-uart-manual -t upload
pio device monitor -e esp32-s3-uart-manual
```

Press RESET after a successful upload to start the application. This profile is a diagnostic workaround, not a verified fix for the intermittent connection problem.

Other environments:

- `esp32-s3`: UART with automatic reset.
- `esp32-s3-usb`: experimental native USB Serial/JTAG, `USB_MODE=1`, `USB_CDC_ON_BOOT=1`, no fixed COM port. Serial output uses the native USB connector in this build.

## HWTEST behavior

At startup: memory information, I²C scan, SD test using a new file, OLED, EEPROM backup/test/restore, and read-only RTC inspection. I²C and RTC checks repeat every 10 seconds.

The EEPROM test requires working SD storage and a verified 4096-byte backup. It changes 16 bytes in the last page only if the entire page contains uniform FF or 00, restores the original bytes, and compares the full image. Keep power connected until restoration completes. This is temporary bring-up behavior, not the intended production startup sequence.

Periodic RTC checks do not write time. Explicit [browser synchronization](docs/rtc-sync.md) sets UTC, verifies readback and clears OSF. An I²C ACK proves an address response, not device identity or full functionality.

## Repository guide

- [firmware/](firmware/README.md): Arduino test firmware and GPIO constants.
- [hardware/](hardware/README.md): hardware notes and pin map.
- [Bring-up plan and results](docs/bring-up.md).
- [SD serial evidence](docs/sd-test-v0.2-serial.txt).
- [Project context](docs/project-context-review.md): relevant findings from earlier logger work.
- [Ukrainian owner notes](docs/uk/README.md): historical bench notes and local workspace review.

Next: verify continued upload reliability and RTC battery retention, test INA228 ID/VBUS/VSHUNT/temperature/ALERT, then restore R1 functionality incrementally.

Legacy recovery: [R1 firmware and viewer review](docs/legacy-r1-analysis.md).
