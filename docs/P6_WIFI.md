# P6a — Direct Wi-Fi control

PANEL v0.20 adds a dedicated Wi-Fi tab, transport labels and associated-station
count. It uses the existing password-protected ESP access point; home-router STA
provisioning and switching Wi-Fi off are not part of this increment.

## Connection and ownership

The PC bridge marks its state as `transport=usb`. Native HTTP state explicitly
reports `transport=wifi`; a browser screen cannot be counted as radio acceptance
merely because the AP startup flag is true. The Wi-Fi task on core 0 samples its
station count every 500 ms, and the owner copies the atomic value into snapshots.
The count includes all associated clients, not just an open browser. Task scheduling
or a long command can delay its display; it is not an acquisition heartbeat.

The AP password remains in the existing NVS namespace and is not changed by this
increment. It is revealed only when the user opens the password details in the UI;
all clients that can join this private AP can access its panel. Measurement EEPROM
profiles, calibration, clock, pinmap and file schema are unchanged.

HTTP on port 80 serves embedded assets, state, live batches and command submission.
Downloads redirect to a separate server on port 81, using the same sole SD owner.
START/STOP always go through the owner command queue; HTTP handlers do not touch
I2C or format recorded samples. Closing a browser does not submit STOP.

## Native acceptance procedure

The opt-in `tests/native_wifi_ui.cjs --hardware` test assumes the test PC is already
connected to the logger AP. It never changes host networking itself. An ignored
`data/wifi-tests/baseline.json` from the current device is required; it contains
private connection/configuration data and must not be committed. USB bridge and
other serial clients must be stopped for an independent radio-path test.

The test checks direct HTTP transport, station association, mobile viewport layout,
Start/Stop from the browser, ten seconds with the browser closed, continued rows
after reopening, directory paging and actual browser download. An optional
`--reference <local-verified-CSV>` compares the corresponding larger `/records/`
file byte-for-byte by SHA-256 while checking the independent state endpoint.
Downloaded native files must also pass the independent contract decoder and
production viewer. Exact applied configuration and saved generation must remain
unchanged. A failed test stops only its own identified recording when possible.

Desktop Chrome with a mobile viewport is not Android Chrome. Physical phone
acceptance separately checks joining the AP despite the no-Internet warning,
opening the panel, reconnecting and finding the downloaded CSV on the phone.
Power-only standalone operation and long-duration/fault tests retain their P7 gates.

Evidence and results are appended to [the migration journal](R1_MIGRATION.md).
Private captures and test recordings remain under ignored `data/wifi-tests/`.

## Physical acceptance — 2026-09-08

Clean commit `a7777f1ac1f2e44fe20fd8e89182a54b6ae8645b` was built and deployed
as v0.20 with flash hash verification. The PC joined the actual ESP AP using its
Wi-Fi adapter while the USB bridge was stopped. Chrome used a 390 x 844 viewport.
The temporary network profile was removed and the original PC connection restored.

| Check | Observed result |
|---|---|
| Direct connection | Native HTTP reports `wifi`; one associated station |
| Browser Start, close for 10 s, reopen, Stop | Same boot/session; 512 additional rows while the browser was closed |
| Completed recording | 541 rows over 10.800001 s at 50 Hz; 139,320 bytes |
| Timing and queue | 19.831–20.150 ms intervals; median 20 ms; FIFO high-water 2; no overflow |
| Independent file checks | Metadata/CRC/SHA and production viewer pass; no missing sequences, quality flags or unverified tail |
| Browser download | Correct CSV filename and complete bytes through native port 81 |
| Larger prior recording | All 615,956 bytes match the previously verified local file by SHA-256 |
| UI during larger download | State response at 207 ms; download completed at 2.72 s |
| Final state | READY, 50 Hz, saved generation 3; exact configuration and AP password unchanged |

Six panel host tests and the browser fixture/regression suite passed before deployment.
The real radio test passed without a serial control process. USB still supplied power;
this is not power-only supply acceptance. Physical Android download/reconnection,
Wi-Fi-off operation and long-duration/fault tests remain open. The USB flashing link
needed retries and confirmed ROM download entry before the final 38,400-baud write;
this increment does not establish a permanent USB repair.

See [Ukrainian connection notes](uk/WIFI.md) for operation from the phone.
