# Browser RTC synchronization (HWTEST v0.7)

After uploading the UART `esp32-s3` environment, close all serial monitors. Run from the repository root using Python with pyserial (PlatformIO's Python already includes it):

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\python.exe" tools/rtc_sync.py --serial-port COM5
```

Open http://127.0.0.1:8765 and click the synchronization button. The browser samples `Date.now()` at the click, and a loopback-only helper sends `TIME UTC <Unix seconds>` at 115200 baud. The RTC stores UTC, while the page also shows browser-local time. It uses the computer clock, not an independent Internet time source. Accuracy is limited by whole-second resolution and browser/serial latency; this is not precision clock calibration.

Firmware accepts explicit newline-terminated commands for 2000–2099 only. It enables battery oscillator operation (EOSC=0), writes the calendar in 24-hour mode, verifies readback (including a one-second rollover), then clears OSF while preserving alarm flags and other status configuration. Failed/partial operations report an error; they do not claim that the old time was restored. Periodic checks and reboot never set time automatically.

The helper accepts same-origin JSON requests only and closes the serial port after each request. Stop it with Ctrl+C when finished. A request is not successful until the firmware acknowledges verified readback. If opening the port resets a particular board, wait for startup and retry with a fresh browser timestamp.

After synchronization, check RTC tick PASS with OSF=0. Battery retention still requires a separate main-power-off test.
