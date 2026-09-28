# R3 PowerBox

Editable KiCad 10 project for the R3 power module. The schematic uses one root
page and ten functional child sheets so battery/BMS, charger/power-path,
user system-power control, primary converters, isolation, LDOs, INA bipolar power and connectors can be
reviewed independently.

## Open

Open `R3_power.kicad_pro` in KiCad 10. The canonical schematic is
`R3_power.kicad_sch`; the PCB file is `R3_power.kicad_pcb`.

## Directory layout

- `R3_power.kicad_pro` — KiCad project settings;
- `R3_power.kicad_sch` — power schematic;
- `R3_power.kicad_pcb` — PCB workspace;
- `libraries/` — project-local symbols and source libraries;
- `footprints/` — project-local provisional footprints;
- `docs/` — design decisions, checks, and transfer notes;
- `bom/` — KiCad-exported BOM plus sourcing/review notes;
- `legacy/` — read-only KiCad 5 source retained for migration reference;
- `tools/` — reproducible schematic generator and its setup notes;
- `manufacturing/` — release outputs only after schematic/PCB review;
- `reports/` — ERC/DRC reports generated during checks.

## Safety and design status

- The board is a unified 2S Li-ion power-management design. The preliminary
  system range is 6.0-8.4 V; there is no intermediate 2S-to-9 V converter.
- J1 is retained as a protected service/bench charger input. USB-C is the
  primary external input; STUSB4500 implements 5/9/12 V negotiation with
  12 V/2 A preferred and a boot-safe 0.50 A charger default.
- `DGND` and `GND_ISO` are separate galvanic domains and must never be joined.
- SW1/Q4 disconnect only `VSYS_MAIN`; BMS, PD and charging remain active while
  R3 is off. SW2 is the separate QON ship/wake/service control.
- The present files are an engineering prototype, not a manufacturing release.
- Q2/Q3, F1/F2/F3 and the dual-NTC strategy are selected for Rev.A. Battery
  chemistry/configuration, hot-current validation and PD NVM compliance remain
  open before ordering a PCB.
- The PCB contains a 160 x 80 mm outline, four spatial zones, an isolation
  keepout on all four copper layers and final pre-routing component placement.
  It has no routing or vias.
- KiCad ERC has zero errors. Remaining generator-related warnings and the visual
  review limitations are recorded in `docs/VERIFICATION.md`.

Start with [the current power review](R3_POWER_REVIEW.md) and
[battery architecture](R3_BATTERY_POWER_ARCHITECTURE.md), then see the compact
[design notes](docs/R3_power_module_design.md) and
[verification status](docs/VERIFICATION.md). Placement images are in
`reports/R3_power_preliminary_placement.png` and
`reports/R3_power_zone_isolation_annotated.png`.
