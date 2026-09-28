# R3 PowerBox

Editable KiCad 10 project for the R3 power module. The schematic uses one root
page and nine functional child sheets so battery/BMS, charger/power-path,
primary converters, isolation, LDOs, INA bipolar power and connectors can be
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
  primary external input; the current schematic implements 5 V fallback while
  the 12 V PD controller decision remains open.
- `DGND` and `GND_ISO` are separate galvanic domains and must never be joined.
- The present files are an engineering prototype, not a manufacturing release.
- Exact BMS MOSFETs, PD controller, battery chemistry/configuration and final
  protection parts must be selected before ordering a PCB.
- The PCB currently contains a 160 x 80 mm floorplan-only outline, four spatial
  zone annotations and an isolation keepout. It has no routing.
- KiCad ERC has zero errors. Remaining generator-related warnings and the visual
  review limitations are recorded in `docs/VERIFICATION.md`.

Start with [the current power review](R3_POWER_REVIEW.md) and
[battery architecture](R3_BATTERY_POWER_ARCHITECTURE.md), then see the compact
[design notes](docs/R3_power_module_design.md) and
[verification status](docs/VERIFICATION.md).
