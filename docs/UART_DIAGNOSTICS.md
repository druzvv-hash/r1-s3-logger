# USB-UART diagnostics

## 2026-09-08 — new cable, failure after automatic ROM entry

**Result: replacing the cable did not eliminate the UART failure.** The ESP32-S3
continued to acquire samples and serve Wi-Fi state while UART commands timed out.
This does not identify a failed component or exclude the old cable as an earlier
contributing factor. No controlled old/new cable comparison was performed.

Setup: clean firmware v0.22 (`ab1e7d0`), CP210x on COM5, 115200 baud, Windows
driver 11.3.0.176, esptool 4.9.0. Initial runtime was READY at 100 Hz with EEPROM
generation 3. The USB panel was stopped cleanly before direct serial access.
No Flash write/erase, EEPROM SAVE, calibration or RTC write was requested.

| Check | Observed result |
| --- | --- |
| Close/open COM5 ten times with DTR/RTS inactive, request STATE | 10/10 replies, 281–297 ms; unchanged boot ID and advancing samples |
| Standard esptool auto-reset, one connection attempt, ROM-only `read_mac` at 115200 | Failed on the first run; invalid chip magic `0x000009`, then `The chip stopped responding` |
| Return to application via 150 ms RTS reset | No valid UART state reply; later Wi-Fi checks confirmed the application was running |
| RTS resets held for 0.5, 1 and 2 seconds; capture UART for eight seconds after each | 0, 660 and 884 bytes respectively; later captures contained incomplete application startup text and invalid UTF-8 bytes |
| Independent Wi-Fi state checks after the UART failure | 12/12 fresh snapshots, sample counter advanced by 326, READY at persisted 50 Hz, unchanged EEPROM generation 3 |
| Restore original volatile settings over Wi-Fi | Exact original config payload restored to 100 Hz; EEPROM generation 3 unchanged; PC returned to its original network |
| Reopen at 115200; then reinitialize through 38400 and 230400 before returning to 115200 | All three STATE requests at 115200 timed out; these were driver reinitialization checks, not application tests at alternative baud rates |
| Restart the identified CP210x device through Windows PnP | Rejected with `Access is denied`; no successful device restart |

COM5 remained enumerated with Windows status OK and device error code 0. This
indicates device enumeration, not successful serial data delivery. The planned
remaining ROM-entry repetitions and continuous UART/live/file-transfer test were
not run after recovery failed; they must not be counted as passed.

The initial UART recovery report labels `application_ready=false` because it
could not obtain a UART response. The independent Wi-Fi check supersedes that
interpretation: the application was running. The observed problem is in serial
communication/reset handling, with CP210x, driver, wiring, reset circuitry and
power integrity still requiring isolation. The failure already occurred while
talking to ROM, before any application image upload.

Espressif documents that automatic boot entry uses DTR/RTS through GPIO0/EN and
that both circuit timing and OS/driver behavior can affect reset. See
[boot mode selection](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/advanced-topics/boot-mode-selection.html)
and [connection troubleshooting](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/troubleshooting.html).
These are diagnostic possibilities, not a confirmed cause on this board.

## Next controlled check

1. Physically disconnect/reconnect USB to reinitialize the bridge, keeping the
   new cable and the same PC port. Verify recovery before another auto-reset.
2. Run continuous UART state/live traffic first; then repeat the same ROM-only
   auto-entry command, with no Flash writes. Preserve failures separately.
3. If auto-reset triggers failure again, compare physical BOOT/RESET entry and
   capture EN, GPIO0 and UART signals around the failing transition. A matching
   old/new cable comparison can then isolate any cable contribution.

Raw logs, private state snapshots and diagnostic helpers are in the ignored
`data/uart-new-cable/` directory. No network credentials or full state payloads
are included in this public report.
