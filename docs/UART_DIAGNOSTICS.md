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

## 2026-09-08 — simultaneous PC byte capture and logger Wi-Fi state

After another owner reconnect, UART responses were already corrupted before any
new test reset. This round performed **no reset, firmware upload or settings
SAVE**. Device-side evidence consists of the logger's existing Wi-Fi state
snapshots; this is not an instrumented ESP32 UART ISR/TX log or an oscilloscope
capture. PC evidence includes exact transmitted/received bytes and error masks
returned by Windows `ClearCommError`, captured before pySerial discards them.

The first direct bulk-read run passed all 24 requests (short deterministic error
replies, STATE, 2,018-byte requests and LIVE). Simultaneous Wi-Fi provided 16
snapshots with one boot ID and 326 additional samples. A subsequent comparison
of the panel's line reader and a bulk reader failed all four initial requests,
including damaged UTF-8; neither reader consistently eliminated the fault.

A controlled run kept the **same COM5 handle open at 115200, 8N1**, with DTR/RTS
inactive, while switching the PC's Wi-Fi association. It alternated STATE and
short read-only protocol probes. No Flash/EEPROM operation was sent.

| Network condition, in execution order | Valid UART replies / requests |
| --- | --- |
| Original PC network, before switching | 28 / 31 |
| Logger AP, with simultaneous HTTP state polling | 38 / 38 |
| Logger AP, without HTTP polling | 42 / 42 |
| Original PC network again | 25 / 28 |
| Logger AP again, with HTTP polling | 10 / 17 |

Total: **143/156 valid UART replies**, with 98 UTF-8 replacement characters in
the failing received byte streams. Here valid means a complete parseable JSON
reply with the matching request ID; STATE does not carry an end-to-end frame
CRC, so this is not proof that every bit of those replies was correct.
The seven reported Windows error events all
had mask **`0x0008` (`CE_FRAME`)**. These are seven error notifications, not a
count of damaged bytes or necessarily seven individual bad frames. No
`CE_RXOVER`, `CE_OVERRUN` or parity error was reported. Lack of a driver error
notification on another failed request does not establish clean transmission.

Microsoft defines `CE_FRAME` as a hardware-detected framing error; buffer
overflow uses different flags. See
[ClearCommError error masks](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-clearcommerror).
The evidence therefore points below the panel's JSON parser, particularly at
the receive path **ESP32 UART TX → wiring → CP210x RX → driver**. It does not
identify whether signal levels/timing, ground/power integrity, the bridge or its
driver is responsible. A framing error is distinct from USB packet CRC failure.

During the controlled run, 55 Wi-Fi snapshots retained the same ESP32 boot ID;
device uptime advanced 37,642 ms and its sample counter advanced by 1,882.
The application remained READY at the persisted 50 Hz profile. Short good and
bad UART periods occurred with and without AP association, including failures
on the second AP visit: Wi-Fi connection alone is not a demonstrated fix or
cause. The PC's original network was restored after each roundtrip.

Final Wi-Fi verification restored the exact previously selected volatile 100 Hz
profile and confirmed READY with EEPROM generation 3 unchanged. No SAVE was
performed. UART remains intermittent; successful Wi-Fi restoration is not a
UART recovery claim.

Raw exchanges and paired state/error reports are retained privately under
`data/uart-both-ends/`. Source-level UART receive/transmit counters have not been
installed: this round deliberately tested the existing v0.22 binary.

## Next controlled check

1. Capture UART0 TX at ESP32 GPIO43 and at the CP210x RX connection while the
   same known request is repeated. Compare levels, bit timing and missing or
   malformed transitions with the PC error timestamps. Check ground and supply
   integrity at both devices; the error notification alone cannot name a part.
2. Isolate the bridge/PC path with a known-good external USB-UART adapter or
   another PC, ensuring only one transmitter drives each UART input. Keep the
   same firmware and load for a useful comparison.
3. Once continuous UART traffic is reliable, repeat automatic ROM entry and
   examine EN/GPIO0 timing if boot-mode failures remain. Reset circuitry is not
   the only suspect now that failures also occur without resets.

Raw logs, private state snapshots and diagnostic helpers are in the ignored
`data/uart-new-cable/` directory. No network credentials or full state payloads
are included in this public report.
