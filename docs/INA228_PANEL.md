# INA228 controls and live chart navigation (PANEL v0.26)

The Overview page now exposes averaging, conversion times for shunt voltage,
bus voltage and die temperature, shunt ADC range, and acquisition rate. Values
are human-readable selectors over the existing configuration fields; the EEPROM,
JSON profile and recording formats are unchanged.

## Acquisition controls

The chip averages 1, 4, 16, 64, 128, 256, 512 or 1024 conversions for each active
input. Conversion time is individually selectable from 50 to 4120 microseconds.
All three inputs remain enabled in triggered mode. These settings affect the
measurements sent to live view and recording, not just their presentation.
The two shunt ranges are ±163.84 mV and ±40.96 mV. The UI calculates the ADC's
current range from the configured shunt resistance; this is not a shunt power
rating. See [TI INA228 datasheet, ADC_CONFIG and sections 7.3.4–7.3.4.2](https://www.ti.com/lit/ds/symlink/ina228.pdf).

The displayed conversion duration is the sum of the three channel durations,
multiplied by the averaging count. The production timing check mirrors
`settings::runtimeTimingFeasible`: conversion must finish strictly before the
ADC timeout and integer acquisition period, with 4000 µs service reserve at
1–100 Hz or 2500 µs at 101–300 Hz. This is a configuration constraint, not a
claim that every physical board/load has passed the maximum rate.

Editing ADC fields adjusts the draft timeout and integration gap allowance.
Incompatible combinations disable Apply and offer an explicit button to choose
the calculated maximum compatible integer rate. If no rate in 1–300 Hz fits,
the user must reduce averaging/conversion times. No setting is applied merely
by selecting an option. The device still validates and reads back register writes.

The INA228 block and Settings page share one draft and show all pending changes.
Apply changes volatile settings; Save remains an explicit, separate EEPROM action.
Recording locks these controls, and changed boot/revision invalidates stale drafts.
Quick frequency changes preserve INA228 settings by default. An explicit
“Auto ADC” choice retains the earlier rate profiles and clears averaging, with
that consequence visible before application.

## Chart

- 10, 30 and 60 second windows; mouse-wheel zoom around the cursor.
- Drag, arrow buttons or arrow keys to pan; plus/minus buttons or keys to zoom.
- Live, Home or double-click returns to the selected live window.
- Browsing history keeps collecting new points; Pause retains the existing
  freeze behavior. Neither action changes acquisition or SD recording.
- Browser history retains up to 180 seconds, capped at 60,000 points. It starts
  when this page receives samples, clears on board reboot, and is not SD history.
- Existing UART bandwidth limitations still produce explicit preview gaps at
  high rates. A 60-second viewport does not imply uninterrupted UART coverage.
- Visible points are selected by binary search. First/last/min/max reduction
  per screen column retains peaks and explicit invalid/configuration boundaries.
  Current and voltage keep separate automatic vertical scales.

## Validation

`tests/ina_chart_ui.cjs` uses explicit synthetic device fixtures and checks timing
boundaries, averaging retention, no implicit mutation/Save, draft conflicts,
recording locks, range display, 54,001-point history, zoom anchoring, drag,
window selection, pause/live, peak/gap preservation and mobile overflow.
Existing rate/panel browser checks and eight panel/rate host tests also passed.
The desktop fixture averaged about 4.9 ms per chart draw for a 60-second window
at 300 Hz; this is a local rendering measurement, not guaranteed display FPS.

Live-board acceptance results are recorded in the migration log. USB uses the
generated HTML file; Wi-Fi uses its identical gzip payload embedded in firmware.
