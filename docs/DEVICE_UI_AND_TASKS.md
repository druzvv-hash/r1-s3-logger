# Device control UI and task ownership

Implementation update, 2026-09-08: [PANEL v0.15](P4B_LIVE_ACQUISITION.md) provides
the USB/AP test interface, real 10/50/100 Hz acquisition and batched live preview.
UART/HTTP run on core 0; core 1 owns INA and chunked OLED I2C transfers.
The map below remains the production target: local menu rendering and the separate
SD recorder are not yet implemented.

Owner requirement, 2026-09-08: operate the logger through an actual UI, preserve the late R1 Fnirsi-style instrument workflow, and separate UI from acquisition/storage across the ESP32-S3 cores. This concerns the **device control panel**, not further offline-viewer feature work. The P3 UART/JSON utility is a service tool, not the final user interface.

## Recovered UI evidence

Read-only review of `Logger_Analysis/Projects/bekup/main21_12_3STAB.cpp` (HTML starting near line 118) confirms a dark compact device panel, START/STOP, view pause, reset, RAW/FILTER, browser time sync, requested rate, calibration unlock and settings, live I/U/P/Wh/Whc/Whd and a canvas graph. Current is cyan (#00c8ff), voltage yellow (#ffd600), power magenta (#ff66ff). The old hardware constants/calibration/timezone behavior are not reusable unchanged.

`Logger_Analysis/Viewer/Prototype/viewer_test.html` explicitly names FNIRSI style and has the matching black chart, dim grid, cyan current/yellow voltage and compact tabs; it is a viewer prototype, not proof that it was the final device firmware. Preserve these demonstrated visual conventions; do not claim an unidentified later donor has already been recovered.

## Device interface scope

Owner confirmed browser control plus standalone physical buttons/encoder, and recording to the existing microSD. The OLED must provide local menus and session controls, not just status. Selected encoder: [Bourns PEC11R-4220F-S0024](../hardware/encoder.md); owner has not installed it yet. A no-GPIO input stub is implemented; GPIO remain pending. No old AP/password is copied from archived code.

- **Live instrument:** large U/I/P readings and units, signed current, recording state, elapsed session time, Ah+/Ah-/Wh+/Wh-, RTC status, SD free capacity, requested versus measured cadence, dropped/invalid samples. Compact scrolling U/I chart; pausing the browser trace never pauses acquisition/recording. Live display filtering does not replace raw recording data.
- **Session controls:** START, STOP, new-session/reset-totals while stopped, filename/session identifier and finalization status. START is enabled only after the P5 recorder exists and passes readiness gates; no fake successful recording controls in a UI-only build.
- **Settings:** shunt/polarity, offsets/gains, INA profile, display options, queue/flush/rotation limits. Clear draft/applied/saved states, changed-field preview, Apply then explicit Save, versioned JSON import/export. Changes require STOP; no slider autosaves or hidden calibration changes.
- **Time and storage:** explicit UTC sync from browser, RTC validity, log list/download through the storage owner. Do not list/download an active file while pretending it is finalized; prioritize recording over downloads.
- **OLED:** current, voltage and READY/RUN/STOPPING/ERROR, elapsed time, SD/config/RTC health, local menu and parameter editing; retain 128x64 and 180-degree rotation. Display builds frames from snapshots; it never queries INA228 directly. Adapt the dense instrument layout to monochrome; cyan/yellow traces belong to the browser display.

Bundle page/CSS/JS locally; no CDN. Network connection and browser lifetime must not control the measurement task. Network setup (AP/STA and credentials) is a separate explicit device setting, outside public measurement/config exports. State-changing commands use POST plus session/config revision checks and bounded queues; UI reports an acknowledged owner result, not merely a successful HTTP send.

## Standalone controls and OLED workflow

Local operation must work with Wi-Fi off and no browser. Input hardware maps to semantic actions (previous/next, select, back, start, stop); the UI state machine must not depend on particular GPIO. Provisionally support a rotary encoder with push switch; a dedicated REC/STOP button is useful if fitted. A button-only adapter can generate the same actions. Neither an encoder nor an extra button is claimed to be installed yet.

| Screen / action | Behavior |
|---|---|
| Main readings | Large U/I; page change exposes P, charge/energy, elapsed time and health. Recording state remains visible on every page. |
| Menu | Session, measurement, calibration, display, clock and diagnostics. Previous/next selects; Select enters; Back returns. |
| Parameter edit | Show value, units and increment; change a draft, Select accepts the draft field, Back cancels that edit. Applying and saving are separate explicit actions. |
| Start recording | Main menu or dedicated REC action, if fitted. Validate readiness; show RUN only after recorder acknowledgement and a successfully created session file. |
| Stop recording | Always reachable during recording. Show STOPPING until queued data and finalization are handled, then READY or an explicit storage error. Repeated STOP is idempotent. |
| Calibration / clock / reset totals | Available while stopped. Explicit confirmation for zero calibration or resetting totals; no automatic zero or persistent write from an encoder turn. |

Decode/debounce inputs on core 0 without delays or storage calls in interrupt handlers. Exact detent, long-press and button mapping are finalized with the actual controls. Bound and coalesce navigation events; navigation traffic must not displace STOP.

Web, local controls and UART submit commands to the same owners and observe the same acknowledged state. Keep edits associated with a config revision; an external apply invalidates a stale draft rather than silently replacing newer settings. Distinguish EDITED, APPLIED/UNSAVED and SAVED on OLED as well as in the browser. JSON import/export remains available through the browser/service tool; local operation must not require typing JSON.

## Core and task map — implementation target

| Core | Task / owner | Priority and boundary |
|---|---|---|
| 0 | Buttons/encoder, local menus, web/control, network service, OLED frame rendering | Low application priority; snapshot consumer, never direct sensor/config/SD ownership |
| 1 | Acquisition / I2C owner | Highest application priority; INA ready handling, original timestamp/raw/quality, calibrated sample, bounded enqueue |
| 1 | Recorder / sole SD owner | Lower than acquisition; consumes sample queue, writes batches, flush/checkpoint/finalize, handles storage requests |

Use explicit FreeRTOS task affinity. Wi-Fi/OS tasks continue to exist; pinning does not dedicate an entire physical core or remove shared-resource contention. ESP-IDF supports pinned tasks and prioritization; see the [4.4 ESP32-S3 scheduling/performance guide](https://docs.espressif.com/projects/esp-idf/en/v4.4.6/esp32s3/api-guides/performance/speed.html), matching the Arduino 2.x generation used here.

**Acquisition and recording are separate tasks even on the same core.** Slow SD writes must not execute inline in the sample producer. A bounded queue absorbs stalls; overflow/short writes produce explicit counters/state and incomplete-session evidence, never silent overwrite. UI snapshots may drop intermediate updates; the recording queue may not silently drop samples. UI commands travel to the owning task and return revisions/results. No shared mutable config object is edited by the web handler.

## Shared bus and flash constraints

At 100 kHz a 1024-byte OLED framebuffer needs at least `1024 * 9 / 100000 = 92.16 ms` for data+ACK alone, excluding addressing/control and software overhead. This exceeds a 20 ms period at 50 Hz. Moving a monolithic `oled.display()` onto core 0 does not fix bus occupancy. A mutex prevents transaction corruption but does not bound latency.

Keep one I2C transaction owner. Core 0 renders a coherent frame into a staging buffer; the owner transmits bounded addressed chunks only within measured acquisition slack. Freeze the source buffer until that frame finishes transmitting; replace only the waiting next frame with newer snapshots. Account for skipped UI frames separately; this does not promise atomic frame presentation on the OLED. RTC reads are scheduled, EEPROM writes and full I2C scans only while stopped. Validate chunk size/time, avoiding unbounded queues or locks held across rendering/network/SD.

Possible later hardware alternatives are a second I2C bus or SPI display, but current confirmed GPIO/wiring stay unchanged. A faster I2C clock is not assumed until verified on all installed modules and wiring.

The confirmed recording target is microSD; internal Flash is not the session storage backend. Firmware/NVS writes should not occur during recording: internal Flash writes/erase have cache/flash-operation effects that core pinning alone cannot isolate.

## Revised sequence and acceptance

1. P4a: task/snapshot/command boundaries and initial Fnirsi-style device control UI for existing P3 settings, including standalone OLED menus and the physical input adapter once hardware/GPIO are confirmed; display real available measurements/state. Keep recorder controls unavailable until connected to P5.
2. P4b: production INA acquisition/ready/timestamps/quality and bounded queue. Measure supported cadence under simultaneous OLED, live UI and network load.
3. P5: sole-owner SD recorder, START/STOP, self-contained files; connect session controls and storage browser.
4. Finish P6 usability/network packaging and deferred viewer analysis using actual files.

Acceptance must record core IDs, stack high-water marks, sample jitter/late counts, queue high-water, OLED transaction maximum, I2C wait time, SD write/flush maximum, and deliberate slow-client/SD-stall behavior. Reload/disconnect the UI during a run; acquisition/session state must survive. Run a complete local start/stop and settings apply/save cycle with Wi-Fi off. Verify input bounce generates no duplicate session actions, STOP remains reachable under event load, and concurrent stale local/web commands cannot overwrite a newer applied config. UI screenshots alone do not establish timing or persistence.

Current CONFIG v0.13 source still uses the diagnostic Arduino loop and has no device web server or production recorder. It adds an encoder stub and [PSRAM FIFO / block-buffer foundation](BUFFERING_AND_REUSE.md), with boot-time memory reservation. This document is the design/acceptance contract, not a claim that the tasks/UI are already implemented.
