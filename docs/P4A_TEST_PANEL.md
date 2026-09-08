# Device test panel v0.15

This is the device control interface, separate from the deferred offline recording viewer.
It reuses the recovered R1 instrument colors: cyan current, yellow voltage, pink power,
a dark graph and compact tabs. It reports actual timed samples, not simulated data.

## Opening the panel

- **PC, USB-UART:** connect the UART connector, close Termite/PlatformIO Serial Monitor,
  then run device_ui/start.cmd. It opens the loopback USB bridge on port 8767 with a
  per-run URL token. PlatformIO's Python with pyserial is used; another installation
  can run python device_ui/bridge.py --port COM5 --open.
- **Phone, standalone:** the normal firmware starts a password-protected AP named
  R1-S3-xxxx. Its generated password is visible in the USB panel's Diagnostics tab
  and in the UART boot message. Join this network, keep the connection without Internet,
  and open http://192.168.4.1/. No PC bridge is needed for this route.
- Before flashing, use **Release USB for flashing** in Diagnostics or device_ui/stop.cmd.
  Closing only a browser tab does not release a serial port held by the bridge.
- Direct file:// opening is unsupported and displays launcher instructions.
  The existing offline viewer remains on its own port 8766.

The AP credential is generated on first use and stored in internal NVS at boot,
before the UI task starts. It is separate from the measurement EEPROM schema and
never exported in configuration profiles. This is the only new automatic persistent
write in this stage. There is no inherited donor password, cloud service or CDN.
STA/home-Wi-Fi provisioning is not implemented in this test panel.

## Available controls

| Control | Owner behavior |
|---|---|
| Live U/I/P, temperature, raw counts/shunt µV | Applied calibration coefficients; invalid/stale values shown as unavailable |
| U/I graph | 10/30 second viewport; 30/60 FPS rendering; real timestamped samples and visible gaps |
| Measurement frequency | Apply 10/50/100 Hz immediately; Save remains explicit |
| Pause/clear graph | Browser display only; does not stop device conversions |
| Measure now | Fresh triggered INA228 conversion with ADC register restoration |
| I²C scan | Address acknowledgements/errors, only on explicit request after startup |
| SD read test | Mount and open root read-only, no format, no file creation |
| EEPROM read test | Two matching complete 4096-byte reads, no writes |
| RTC test / UTC sync | Read health; explicit host UTC write with register readback |
| Configuration | All 28 schema fields, local draft/difference, Apply, separate Save |
| Profile import/export | P1 r1s3-config v1.0 JSON envelope and exact TLV encoding |

Apply validates schema, bounds and INA timing before hardware register readback.
Failed readback retains the earlier applied configuration or exposes the existing
INA fault latch. Save uses the existing A/B footer-last store; no slider autosaves.
Boot identity and configuration revision reject stale edits after a reboot, another
panel's apply, or a UART settings transfer. An uncertain command timeout is never
automatically retried. Read the current device state before deciding what to repeat.

For the installed 400 A / 60 mV shunt, the default is 150 µΩ. The narrow ±40.96 mV
range cannot cover its full rating. Applying nominal values does not validate calibration.

## Task and memory boundaries

- Core 0: UART protocol service plus Wi-Fi AP and HTTP service in an explicitly pinned low-priority task.
- Core 1: existing Arduino hardware owner; INA, RTC, EEPROM, SD diagnostics and OLED.
- HTTP consumes a copied JSON snapshot and submits a bounded command queue. It never
  accesses Wire, SD, the mutable configuration or the recording buffers.
- UART executes the same owner-side command dispatcher and uses request identifiers
  so old responses cannot be mistaken for a new request.
- Web, UART and owner stacks are internal RAM, 24 KiB each. Queue/control storage is internal;
  the existing sample pool remains explicitly allocated in PSRAM and SD staging is
  8 KiB internal DMA-capable RAM.
- Firmware snapshots publish up to twice per second; the browser/USB bridge polls about
  once per second, with separate live batches at the configured delivery target. Heartbeat freshness is checked independently from HTTP success:
  a responding web task cannot make a frozen owner snapshot look live.

The embedded HTML is generated from device_ui/index.template.html, style.css,
codec.js, app.js and the existing config registry. tools/build_panel.py emits
the USB HTML and a gzip PROGMEM asset; PlatformIO regenerates it through a pre-build hook.
No browser libraries or assets are fetched from the Internet.

## Scope and limits

The timed acquisition/live portion of P4b is now active. See
[v0.15 scheduling, quality and transport](P4B_LIVE_ACQUISITION.md).
OLED data is sent in short chunks by the single I2C owner. The browser independently
animates up to 60 FPS. Maintenance commands pause acquisition and mark a gap.

Production SD sessions, totals and file download remain pending. Recorder fields are
marked as future settings. FIFO budget changes require saving then rebooting; Apply
does not resize the recording pool.

The encoder remains a no-GPIO stub. Local menus, confirmed input GPIO, AP lifecycle
during production recording and log list/download are still pending.

## v0.14 baseline validation

For current cadence acceptance, see [v0.15 results](P4B_LIVE_ACQUISITION.md).

- 40 host tests include the existing EEPROM fault injection and FIFO tests, plus JS/Python
  TLV agreement, invalid inputs and loopback API token/origin/size boundaries.
- Chrome fixture acceptance covers dirty drafts, invalid values, external revision
  changes, disconnected/frozen data and responsive layout.
- Physical USB acceptance: normal firmware upload, live INA values, reversible OLED
  contrast Apply/restore through the real browser, and saved generation 3 retained.
- Physical API tests passed for INA, I²C, SD read, EEPROM read and RTC read. A stale boot
  SAVE command was rejected. The complete post-upload EEPROM image matches the pre-panel
  backup byte for byte (CRC32 EBDAE9A1). No EEPROM Save or clock adjustment was needed.
- Normal and explicit service configurations compile; only normal firmware is flashed.
- Native AP startup is reported by the board. Phone-to-AP browser operation still
  needs the owner's check; desktop USB acceptance is not evidence of that radio path.

Private EEPROM backups, live captures and connection credentials remain under
private backup folders / ignored data/, outside the public repository.
