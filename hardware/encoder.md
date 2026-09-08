# Local control encoder

Selected 2026-09-08: **Bourns PEC11R-4220F-S0024**, plus a knob for a **6 mm D-shaft**. The owner has not purchased/installed it yet. GPIO remain unassigned.

This part has 24 detents and 24 quadrature pulses/revolution, a momentary push switch, a 20 mm metal flatted shaft and panel fastening hardware. One complete quadrature cycle corresponds to one detent. The 20 mm dimension is the manufacturer's actuator dimension; check the drawing against the enclosure and knob depth before drilling. Source: [Bourns PEC11R datasheet and ordering table](https://www.bourns.com/docs/product-datasheets/pec11r.pdf). [Supplier product page](https://www.tme.eu/en/details/pec11r-4220f-s0024/incremental-type-encoders/bourns/); no price or stock level is frozen in this document.

This is a compact mechanical menu control, not a precision shaft-position sensor. It offers enough tactile steps for navigating the small OLED, fine adjustments and software-selected larger increments. The push switch provides Select; a long press can provide Back. Keep a visible Back menu action too. A separate momentary REC/STOP button is optional, not required to use the logger. Debounce and full quadrature transition validation are required when implementing the real adapter.

## Electrical implementation target

- Bare encoder: A/B/common contacts and two separate push-switch contacts; no module power pin. Common and one switch contact go to GND; A, B and the other switch contact go to three confirmed GPIO inputs.
- Use pull-ups to **3.3 V** for ESP32-S3 inputs. The datasheet's 5 V contact rating is not a requirement to apply 5 V to the MCU. Select pull-ups/filter values for the actual wiring; the manufacturer shows a filter example. Verify bounce, fast rotation, press/release and idle levels on the assembled unit.
- Confirm the particular footprint/contact orientation from the drawing. Do not infer pin order from a generic KY-040 board.
- Keep BOOT/RESET and the existing I2C/SD/ALERT wiring unchanged; no pin allocation in this stage.

`firmware/include/local_input.h` defines Previous/Next/Select/Back/Start/Stop actions. `local_input.cpp` is deliberately disconnected: available=false, poll returns no action, with no GPIO, pull-up or interrupt operations. The future adapter changes input acquisition, not recording ownership. The stub is not a simulated working encoder and not a finished menu UI.
