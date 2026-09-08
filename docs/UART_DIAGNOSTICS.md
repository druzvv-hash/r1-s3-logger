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

## 2026-09-08 — repeat after another alcohol cleaning

The owner cleaned the board again. The bench supply was **OFF, with the wires
still connected**, as confirmed by the owner. Firmware v0.22 was unchanged;
COM5 used 115200 baud. Initial settings were READY at 50 Hz, SAVED, EEPROM
generation 3. Earlier failing runs had a powered load, so this comparison does
not isolate the effect of cleaning from the changed load conditions.

Acquisition was temporarily set to 300 Hz without saving to EEPROM. The
continuous test included STATE/LIVE polling and a complete existing SD file
download through UART; no new load recording was made.

| Check | Result |
| --- | --- |
| Continuous exchange | 471.5 seconds; 1,578 measured requests; zero request errors |
| Request breakdown | 196 STATE, 531 LIVE, 849 file chunks, OPEN and CLOSE |
| SD file transfer | 1,737,293 bytes; every chunk CRC32 and whole-file SHA-256 verified |
| Application during exchange | One boot ID; zero missed/invalid samples; 1,764 OLED frames |
| Windows UART flags | None reported, including no `CE_FRAME` |
| Port close/open/STATE cycles | 10/10 passed; no unexpected reset |
| Automatic ROM read sessions | 9/10 passed; first response truncated; all ten recovered to READY |

The downloaded existing file was
`r1s3_2026-09-08_15-27-02Z_3047473d_f5b0eb2c_0000.csv`, with SHA-256
`aef5a75c9cd200e3377e2da3a6ddf307cb667b16eb58b0e7c1b91e004af58a05`.
Measured request latency was 375 ms median and 407 ms maximum, including the
large hexadecimal file replies; this is not the acquisition interval.

Each ROM test used standard esptool reset control, one connection attempt,
`--no-stub` and read-only `read_mac` at 115200 baud. The **first session entered
DOWNLOAD and exchanged SYNC replies**, then its READ_REG response was truncated:
`Packet content transfer stopped (received 9 bytes)`. This was not a failure to
enter download mode. An automatic recovery reset restored the application;
the next nine sessions succeeded. No Windows UART error flag was reported in
any of these sessions. Host traces record requested DTR/RTS changes and raw
serial bytes, not measured EN/GPIO0 voltage waveforms.

Final state was READY at the exact initial 50 Hz configuration, with EEPROM
generation 3 unchanged. No firmware write, Flash erase or EEPROM SAVE was
performed. Continuous UART traffic improved in these conditions, but the
remaining ROM transfer failure prevents declaring the issue resolved. Evidence
and private raw captures are under `data/uart-after-clean/`.

## Next controlled check

First repeat the continuous UART/file test with the previous powered bench load,
keeping the cleaned board, cable and wiring unchanged. This separates the
changed load condition from cleaning. If corruption recurs, continue below.

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
