# R3 PowerBox review

Review date: 2026-09-28
Status: final UI / power-control / DRC pass complete; **routing remains blocked by the validation items below**.

The editable electrical source is `tools/generate_hierarchical.py`. Generated KiCad sheets, PDF and BOM are derived artifacts. The detailed battery decision record and budgets are in `R3_BATTERY_POWER_ARCHITECTURE.md`.

## Implemented in this pass

- Added a normal user load switch after F3: `VSYS_PROT -> Q4 -> VSYS_MAIN`.
  Q4 is `DMP3007LSS-13`, a 30 V P-channel SO-8 MOSFET. Its 100 kOhm
  gate-source resistor makes the default state OFF; SW1 closes only the
  low-current gate-control path through 10 kOhm, and C107 provides controlled
  turn-on. BMS, STUSB4500 and BQ25798 stay upstream, so charging continues
  while R3 main electronics are off.
- Corrected the invalid/ambiguous old `DMP3010LSS` reverse-polarity MPN to the
  verified P-channel `DMP3007LSS-13` for Q1 and added a project-local SO-8
  footprint with the physical 1-3=S, 4=G, 5-8=D mapping.
- Connected BQ25798 QON to local momentary SW2 and `QON_SERVICE`; QON remains a
  ship/wake/service input and is not used as normal ON/OFF.
- Added `LED_CHARGE` from REGN through 2.2 kOhm to raw open-drain
  `BQ_STAT_RAW`, and `LED_RUN` from switched `+3V3_D`. `CHARGE_STATUS` is now
  a separate 3.3 V logic net isolated from raw STAT by D7. Added ten-pin
  primary-only J11 for the user panel and SOC/I2C expansion.
- Cleared all 18 copper-to-edge, 8 drill-range, 4 annular-width and 20
  footprint-internal-clearance DRC findings. USB-C moved 1.8 mm inward from
  its original provisional origin; U1/U7 use non-via land patterns, with
  0.30/0.70 mm thermal vias reserved for routing. The project fine-pitch
  minimum is 0.13 mm versus the selected 4-layer process capability of
  0.09 mm; use 0.20 mm wherever density permits.

- Replaced service-input D1 and USB VBUS D3 with `SMBJ13A` (13 V VRWM,
  14.4-15.9 V VBR, 21.5 V clamp at 28 A/10-1000 us). At the 10 A design surge
  assumption the interpolated clamp is about 17.9 V, below TPS2121's 22 V
  recommended and 24 V absolute maximum limits.
- Corrected BQ28Z610 2S VC wiring to the TI pin definitions: `BAT_POS_RAW`
  through 100 ohm to VC2, `CELL_MID` through 100 ohm to VC1, and
  `BAT_NEG_RAW` to VSS. Cell filters are 100 nF VC1-VSS (Cell1) and 100 nF
  VC2-VC1 (Cell2).
- Rebuilt Q2/Q3 as the TI-EVM common-drain pair: DSG FET on PACK side, CHG FET
  on cell side, 5.1 kOhm gate resistors, 10 MOhm gate-source bias and 100 nF
  drain-source capacitors. Q2/Q3 are fixed as `CSD17577Q3AT` in the
  project-local 3.3 x 3.3 mm DQG/VSON footprint.
- Changed J9 pin 2 from `BAT_NEG_RAW` to `DGND`. Layout must implement the
  conductor as quiet `DGND_CHG_SENSE` direct to the BQ25798 ground area.
- Added BQ25798-local VBUS bypass: 100 nF 0402 plus three 10 uF/25 V ceramics.
- Added `STUSB4500QTR` autonomous PD sink, documented dead-battery CC wiring,
  ESDA25W CC protection, 5/9/12 V PDO record, PD test points and J10 PD status.
- Removed legacy independent 5.1 kOhm CC Rd resistors.
- Changed BQ25798 ILIM_HIZ divider to 243 kOhm/100 kOhm for approximately
  0.50 A hardware default until a source contract is confirmed.
- Marked U11 explicitly as an unconnected DNP footprint-space reservation,
  not a functional BQ294502 secondary-overvoltage circuit.
- Tied STUSB4500 RESET directly to `DGND`; PDO3 remains 12 V/2 A and
  `POWER_OK_CFG=10b` maps POWER_OK3 only to a successful PDO3 contract after
  PS_READY.

The earlier architecture items below remain valid unless superseded by this
correction list.

- Fixed the product architecture at 2S Li-ion, 6.0-8.4 V preliminary range and 8.4 V charge voltage.
- Renamed fixed-9-V system nets to `VSYS_RAW` and `VSYS_PROT`.
- Retained J1 and its protection as a 6-12 V service/bench charger input, not as the battery/system rail.
- Retained the USB protection/TPS2121 input mux and upgraded the USB-C input to autonomous 5/9/12 V PD with safe 5 V fallback.
- Added provisional BQ25798 1-4S buck-boost NVDC charger/power-path, configured as a 2S architecture.
- Added 4-pin keyed 2S connector with `BAT_POS_RAW`, `CELL_MID`, `BAT_NEG_RAW`, `NTC_BMS` and an optional separate charger-NTC connector.
- Added provisional BQ28Z610 1-2S gauge/protector with per-cell monitoring, internal balancing, CHG/DSG high-side FET control and a 10 mOhm Kelvin shunt.
- Added primary-side I2C and charger/status telemetry connector J10.
- Preserved the existing TPS62132, TPS54302, independent ADS/INA pre-isolation filters, RS3E, RS3 dual, ADM7150 and TPS7A20 architecture.
- Removed the TPS54302 8-V reference-design EN divider because it blocked the 6-8.4 V 2S range; EN now follows `VSYS_PROT` and battery cutoff belongs to the BMS.
- Added battery, cell, NTC, shunt, charger-input and VSYS test points.
- Added a reproducible preliminary placement inside the DIRTY -> PRIMARY ->
  ISOLATION -> CLEAN floorplan and retained the isolation copper/via/pad
  keepout. No routing, vias or copper pours were added.
- Converted the board definition to four copper layers and extended the
  3.0 mm isolation keepout across every copper layer and the entire board
  height. U3/U6 primary pins face DGND and secondary pins face GND_ISO.
- Fixed Rev.A protection/temperature choices: F1 `MF-R250-0-10`, F2
  `MF-MSMF260/16X-2`, F3 `MF-MSMF250/16X-2`, and two independent SEMITEC
  `103AT-2` NTC probes.

## Current power tree

```text
USB-C 5/9/12 V -- F2/SMBJ13A/STUSB4500 --+
                                  +-> TPS2121 -> CHARGER_IN
J1 service 6-12 V -- existing protection --+

2S cells -> BQ28Z610 / CHG+DSG FETs / shunt -> PACK_POS + DGND

CHARGER_IN + PACK_POS -> BQ25798 NVDC charger/power-path
                       -> VSYS_RAW -> F3 MF-MSMF250/16X-2 -> VSYS_PROT
                       -> Q4 DMP3007LSS / SW1 -> VSYS_MAIN

VSYS_MAIN -> TPS62132 -> +3V3_D
VSYS_MAIN -> TPS54302 -> +5V_PREISO
  -> FB6/C26/C27 -> +5V_PREISO_ADS -> RS3E -> isolated ADS rails
  -> FB7/C28/C29 -> +5V_PREISO_INA -> RS3 dual -> isolated INA rails

DGND || galvanic isolation || GND_ISO
```

## Direct 2S verification

- TPS62132: 3-17 V input and 100% duty mode; direct 2S operation is supported.
- TPS54302: 4.5-28 V input and internal UVLO below the 2S range. Required duty at 6.0 V to make 5.0 V is 83.3%. Direct operation is retained, but TI does not publish a guaranteed 5 V/3 A dropout curve at 6 V, so low-battery load/transient bench validation is mandatory.
- No 2S-to-9 V converter was added.

## New IC/package verification

| Part | Verified manufacturer pin/package summary |
|---|---|
| TPS2121RUXR | RUX VQFN-HR-12: OUT 1/8, IN2 2, CP2 3, OV2 4, OV1 5, PR1 6, IN1 7, ST 9, ILIM 10, SS 11, GND 12; 2.8-22 V, 24 V absolute maximum, 4.5 A class |
| BQ25798RQM | RQM VQFN-29 4x4 mm: exact pins 1-29 captured from TI Table 5-1; 3.6-24 V, 1-4S, 5 A charge, integrated buck-boost and NVDC BATFET power path |
| BQ28Z610DRZR | DRZ VSON-12+EP: VSS 1, SRN 2, SRP 3, TS1 4, SCL 5, SDA 6, DSG 7, PACK 8, CHG 9, PBI 10, VC2 11, VC1 12, EP 13; 1-2S gauge/protection/balancing |
| STUSB4500QTR | QFN-24 EP: official KiCad/ST pin mapping verified; VDD 4.1-22 V, VSYS 3.0-5.5 V, VBUS pins 28 V tolerant, CC short-to-VBUS protection to 22 V, 3 NVM PDOs and dead-battery operation |
| DMP3007LSS-13 | 30 V P-channel SO-8; 10 mOhm maximum RDS(on) at VGS=-4.5 V; project footprint maps physical 1-3=S, 4=G, 5-8=D to the logical PMOS symbol |

STUSB4500 `RESET` is tied directly to `DGND`. The NVM definition uses PDO3 =
12 V/2 A and `POWER_OK_CFG=10b`; consequently `PD_CONTRACT_12V_N` is low only
after PDO3 is selected and the source completes the transition with PS_READY.

Original TI datasheets are assigned in each symbol. The BQ28Z610 project
footprint follows TI DRZ0012A dimensions. Q2/Q3 are fixed as
`CSD17577Q3AT`; the project DQG footprint maps the physical gate, source and
drain lands to the existing logical three-pin symbol.

## Connectors

| Connector | Function/pinout |
|---|---|
| J1 | service/bench input: 1 `SERVICE_IN_RAW`, 2 `DGND` |
| J2 | digital power: two `+3V3_D`, two `DGND`, `PG_3V3_D`, NC |
| J3 | isolated rails with repeated `GND_ISO`, unchanged |
| J4 | `DGND`, `PG_3V3_D`, `CTRL_RS3E_PRI`, NC |
| J5/J6 | primary/isolated AUX DNP, unchanged |
| J7 | USB-C PD input; CC1/CC2 owned by STUSB4500 with CCxDB dead-battery connections; data pins unused |
| J8 | keyed 2S battery: `BAT_POS_RAW`, `CELL_MID`, `BAT_NEG_RAW`, `NTC_BMS` |
| J9 | optional separate `NTC_CHG`, `DGND` quiet/Kelvin charger return |
| J10 | `+3V3_D`, `DGND`, PM I2C, charge status, `PG_3V3_D`, charger fault/interrupt, input-source status, `PD_ALERT_N`, `PD_CONTRACT_12V_N` |
| J11 | user panel: 1 `+3V3_D`, 2 `DGND`, 3 `POWER_CTRL`, 4 `QON_SERVICE`, 5 `CHARGE_STATUS`, 6 `PG_3V3_D`, 7/8 PM I2C SCL/SDA, 9 `BQ_STAT_RAW`, 10 SPARE/NC |

No connector contains both `DGND` and `GND_ISO`.

## New test points

TP20 USB VBUS raw, TP21 charger input, TP22 VSYS raw, TP23 VSYS protected,
TP24 battery positive, TP25 cell midpoint, TP26 battery negative, TP27/TP28
filtered Kelvin shunt sense, TP29 BMS NTC, TP30 charger NTC, TP31/TP32 CC1/CC2,
TP33 protected USB VBUS, TP34 PD VDD, TP35 PD 2.7 V regulator, TP36 PD alert
and TP37/TP38 PM I2C. All existing primary and isolated test points remain.

## Budget summary

- Expected R3 system input: approximately 4.4 W.
- Expected battery current: 0.52 A at 8.4 V, 0.59 A at 7.4 V, 0.73 A at 6.0 V.
- Plausible peak case: approximately 8 W, or 0.95/1.08/1.33 A at 8.4/7.4/6.0 V.
- Converter-nameplate design worst case: approximately 19.8 W, or 2.36/2.68/3.30 A. This is a sizing bound, not the expected R3 operating load.
- Proposed battery path target: 5 A connector/FET/shunt/copper class. F3 is
  `MF-MSMF250/16X-2`: 2.50 A hold at 23 C and 1.85 A at 60 C, so the measured
  peak current/temperature gate remains mandatory.
- With 4.4 W system load and 90% conversion, 1 A charging needs 0.96/1.09/1.19 A from 12 V at BAT=6.0/7.4/8.4 V. A 2 A setting needs 1.52/1.78/1.96 A. The 12 V/2 A contract policy limits IINDPM to 1.80 A, so DPM must reduce charge near full battery and during system peaks.

### PD/source current policy

| Confirmed source | BQ25798 input limit | Available input power | Charging consequence with expected 4.4 W system load |
|---|---:|---:|---|
| unknown 5 V / no PD | 0.50 A hardware | 2.5 W | system may need battery supplement; charging not guaranteed |
| confirmed 5 V/1.5 A | 1.35 A | 6.75 W | slow charging only |
| confirmed 5 V/3 A | 2.25 A | 11.25 W policy cap | reduced charging; kept below TPS2121/F2 approximately 2.5 A hardware class |
| 9 V/2 A PD | 1.80 A | 16.2 W | 1 A charge expected; 2 A not sustainable |
| 12 V/2 A PD | 1.80 A | 21.6 W | 2 A possible at low/mid BAT; reduced near 8.4 V/peak load |

## Technical issues not silently hidden

1. **PD configuration:** STUSB4500 is implemented, but its NVM must be programmed/read back and USB-PD behavior verified with an analyzer before higher IINDPM values are enabled.
2. **Dual temperature inputs:** Rev.A uses two independent SEMITEC `103AT-2`
   probes (10.0 kOhm at 25 C, B25/85=3435 K, 1%). `NTC_BMS` terminates at
   the pack/BQ28Z610 reference; `NTC_CHG` returns quietly to charger DGND.
3. **BMS configuration:** BQ28Z610 safety and gauge data-flash values, chemistry profile, recovery and balancing require configuration and test.
4. **MOSFETs:** Q2/Q3 use the final pre-routing `CSD17577Q3AT` selection and a
   project-local DQG/VSON footprint. BQ28Z610 drives approximately 9.5 V, so
   the relevant 10 V maximum RDS(on) is 4.8 mOhm: pair conduction loss is
   9.6 mW at 1 A, 104.5 mW at 3.3 A and 240 mW at 5 A at 25 C. Using a
   conservative 1.8x hot-resistance multiplier gives 17.3 mW, 188 mW and
   432 mW for the pair. Reserve at least 200 mm2 combined L1 spreading copper
   and 4-6 0.30 mm finished thermal vias per FET into primary copper. Protection
   event SOA/turn-off and assembly yield still require validation.
   Distributor check on 2026-09-28 found CSD17577Q3AT stocked at Mouser; the
   part is active, but procurement must recheck stock at release time.
5. **TPS54302 dropout:** verify 5 V regulation, startup and load steps at `VSYS=6.0 V`.
6. **INA isolated supply:** RS3-0505D/H3 light-load regulation and rail balance remain unresolved.
7. **BMS hardware fault signal:** BQ28Z610 has autonomous FET protection and I2C status but no general alert pin. Add an external supervisor only if the MCU requires a dedicated fault wire.
8. **PPTC temperature:** F1/F2/F3 are fixed for Rev.A placement and BOM, but
   their hold current derates with ambient. At 60 C F1 is 1.70 A, F2 is
   2.00 A and F3 is 1.85 A. The 5 V/3 A firmware policy remains 2.25 A, so
   sustained hot operation must invoke charger thermal/DPM derating or use a
   separately reviewed non-resettable-fuse option.
   MF-MSMF250/16X-2, MF-MSMF260/16X-2 and MF-R250-0-10 were stocked at
   authorized distributors on 2026-09-28; purchasing must preserve the exact
   F1 5.1 mm lead-style suffix.

## USER POWER AND INDICATION

- **Normal OFF:** SW1 open lets R102 pull Q4 gate to `VSYS_PROT`; Q4 is off,
  `VSYS_MAIN`, TPS62132, TPS54302 and all R3 main loads are de-energized.
  BQ28Z610, STUSB4500 and BQ25798 remain connected to their upstream rails.
- **Normal ON:** SW1 closes `POWER_CTRL` to DGND through R103. At 8.4 V the
  control current is about 76 uA; no 3-5 A load current crosses SW1. C107/R103
  controls the gate edge. Q4 logical pin 2/physical pins 1-3 are the source on
  `VSYS_PROT`; logical pin 3/physical pins 5-8 are the drain on `VSYS_MAIN`.
- **Loss:** using a conservative hot 15 mOhm Q4 resistance gives 15/30/49.5 mV
  drop and 15/60/163 mW at 1/2/3.3 A. Even the 3.3 A design-worst case is
  modest for SO-8 with local top copper; verify temperature on the prototype.
- **Charge while OFF:** BQ25798 SYS/charger and STAT are upstream of Q4, so
  charging and LED_CHARGE remain functional with `VSYS_MAIN` off.
- **QON/ship mode:** SW2 or J11.4 momentarily pulls the internally biased QON
  pin low. Rev.C uses the programmed 1 s default or 15 ms `WKUP_DLY` interval
  to exit ship mode; an approximately 10 s low requests system-power reset.
  No external ship FET is fitted in Rev.A.
- **CHARGE LED:** REGN -> R104 2.2 kOhm -> red D5 -> `BQ_STAT_RAW`. Expected current is
  about 1.3 mA. Charging=ON, complete/disabled/battery-only=OFF, fault=1 Hz
  blink. R80 pulls the separate `CHARGE_STATUS` net to switched +3V3_D, while
  D7 `BAT54WS-7-F` connects anode=`CHARGE_STATUS`, cathode=`BQ_STAT_RAW`.
  Therefore STAT LOW propagates to logic but REGN/D5 cannot back-power
  +3V3_D. At the combined approximately 1.6 mA STAT sink, the TI maximum
  `VOL_STAT` specification is 0.4 V; adding the BAT54WS maximum 0.32 V at
  1 mA gives a conservative logic LOW no greater than 0.72 V. This is below
  the ESP32-S3 0.25*VDD = 0.825 V and STM32H755 0.3*VDD = 0.99 V limits at
  3.3 V.
- **RUN LED:** +3V3_D -> R105 2.2 kOhm -> green D6 -> DGND, about 0.6-0.8 mA.
  It indicates the actual main digital rail and is dark in normal OFF.
- **SOC:** no analog LED gauge is added. BQ28Z610 supplies SOC, voltage,
  current/state and capacity over PM I2C to the R3 display/UI.
- **J11:** primary-only user-panel connector; it never exposes GND_ISO or the
  onboard LED anode nets. J11.9 is raw open-drain `BQ_STAT_RAW`; every panel
  LED must have its own series resistor. `POWER_CTRL` accepts only a latching
  contact to DGND; `QON_SERVICE` accepts only a momentary contact to DGND.

## ERC and files

Final ERC result: **0 errors and 412 warnings**, limited to 206
`endpoint_off_grid` and 206 `lib_symbol_mismatch` findings from the SKiDL
embedded-library/deterministic-grid generation path. The count is recorded in
`reports/R3_power_erc.txt` and `docs/VERIFICATION.md`. Generated outputs are:

- schematic PDF: `reports/R3_power_schematic.pdf`;
- BOM: `bom/R3_power_kicad_bom.csv`;
- harness BOM: `bom/R3_power_harness_bom.csv`;
- logical pin/net map: `tools/logical_nets.json`.
- high-resolution placement: `reports/R3_power_preliminary_placement.png`;
- annotated zones/isolation: `reports/R3_power_zone_isolation_annotated.png`;
- stacked-board top/side references:
  `reports/R3_power_mechanical_stack_top.png` and
  `reports/R3_power_mechanical_stack_side.png`;
- unrouted placement DRC: `reports/R3_power_pcb_drc.txt`.

## Mechanical and board-to-board interface

Six electrically floating 3.20 mm NPTH M3 holes are present. Each has an
8.0 x 8.0 mm four-copper-layer routing/pad/via/pour keepout and 8.0 mm
courtyard. Coordinates are H1 (35.0,25.5), H2 (174.5,25.5), H3
(25.5,94.5), H4 (174.5,94.5), H5 (115.0,25.5) and H6 (135.0,94.5). H1-H4
are the preferred common mounting set for the future R3 board; H5/H6 stiffen
the PowerBox without entering x=121...124 mm.

J12 is a DNP generic 2x8/2.54 mm THT primary header at pin-1 origin
(106.0,28.0). It duplicates +3V3_D/DGND contacts and exports PM I2C, PG,
charger/input/PD status, POWER_CTRL and QON_SERVICE. J13 is a physically
separate DNP 2x5/2.54 mm THT isolated header at (154.0,24.0), with one
GND_ISO return adjacent to each clean rail. J12 has no GND_ISO and J13 has no
DGND. Existing Micro-Fit cable connectors are unchanged and remain in parallel.

The future-board reference envelope is on `Dwgs.User`, not `Edge.Cuts`.
U3/U6 set the height limit at 11.1 mm. A 12 mm spacing leaves only 0.9 mm
nominal and requires an upper-board cutout/keepout; **15 mm is recommended**
and leaves about 3.9 mm nominal. Final header/socket MPNs, standoff tolerance,
J3/J10/J11 latch access and enclosure cable bends remain a mechanical-CAD
gate. Full dimensions and pin tables are in
`docs/R3_BOARD_TO_BOARD_INTERFACE.md`.

## PCB recommendation and blockers

The board is explicitly four-layer: L1 components/critical loops, L2 primary
DGND, L3 power/quiet routing and L4 secondary/clean routing. Every layer is
interrupted by the x=121...124 mm isolation rule area. The resulting 3.0 mm
minimum board copper clearance/creepage is the maximum supported by the SIP8
pad-3/pad-5 geometry (3.08 mm edge-to-edge) and is accepted here for
low-voltage functional isolation only, not certified mains/reinforced safety.

The unrouted PCB DRC has **zero** clearance, copper-to-edge, hole-to-hole,
hole-to-copper, drill-range, annular-width and courtyard-overlap errors. It
retains 437 expected unconnected/ratsnest findings, 233 expected
schematic-parity findings and 214 non-electrical silkscreen findings.
These do not authorize routing release; final reference-text cleanup remains.

PCB routing is blocked by STUSB4500 NVM/compliance validation, BQ28Z610
configuration thresholds, Q2/Q3 protection-event SOA, hot PPTC/current
validation, enclosure/mating-connector/B2B stack clearance, measured power budget,
TPS54302 low-battery validation and the RS3 INA light-load decision. Secondary
OV remains a documented DNP space reservation and is not active in Rev.A.
