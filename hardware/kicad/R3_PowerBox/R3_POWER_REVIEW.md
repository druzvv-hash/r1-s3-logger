# R3 PowerBox review

Review date: 2026-09-28
Status: final pre-routing placement pass complete; **routing remains blocked by the validation items below**.

The editable electrical source is `tools/generate_hierarchical.py`. Generated KiCad sheets, PDF and BOM are derived artifacts. The detailed battery decision record and budgets are in `R3_BATTERY_POWER_ARCHITECTURE.md`.

## Implemented in this pass

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

VSYS_PROT -> TPS62132 -> +3V3_D
VSYS_PROT -> TPS54302 -> +5V_PREISO
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

## ERC and files

Final ERC result: **0 errors and 378 warnings**, limited to
`lib_symbol_mismatch` and `endpoint_off_grid` from the SKiDL
embedded-library/deterministic-grid generation path. The count is recorded in
`reports/R3_power_erc.txt` and `docs/VERIFICATION.md`. Generated outputs are:

- schematic PDF: `reports/R3_power_schematic.pdf`;
- BOM: `bom/R3_power_kicad_bom.csv`;
- harness BOM: `bom/R3_power_harness_bom.csv`;
- logical pin/net map: `tools/logical_nets.json`.
- high-resolution placement: `reports/R3_power_preliminary_placement.png`;
- annotated zones/isolation: `reports/R3_power_zone_isolation_annotated.png`;
- unrouted placement DRC: `reports/R3_power_pcb_drc.txt`.

## PCB recommendation and blockers

The board is explicitly four-layer: L1 components/critical loops, L2 primary
DGND, L3 power/quiet routing and L4 secondary/clean routing. Every layer is
interrupted by the x=121...124 mm isolation rule area. The resulting 3.0 mm
minimum board copper clearance/creepage is the maximum supported by the SIP8
pad-3/pad-5 geometry (3.08 mm edge-to-edge) and is accepted here for
low-voltage functional isolation only, not certified mains/reinforced safety.

PCB routing is blocked by STUSB4500 NVM/compliance validation, BQ28Z610
configuration thresholds, Q2/Q3 protection-event SOA, hot PPTC/current
validation, enclosure/mating-connector clearance, measured power budget,
TPS54302 low-battery validation and the RS3 INA light-load decision. Secondary
OV remains a documented DNP space reservation and is not active in Rev.A.
