# Verification status

Status: **FINAL PRE-ROUTING PLACEMENT CAPTURED / ERC PASSED WITH WARNINGS / NO ROUTING**.

Checked on 2026-09-28 with KiCad 10.0.0 and SKiDL 2.3.0.

## Automated checks

- Root plus nine child `.kicad_sch` files load and save through `kicad-cli sch upgrade --force`.
- PDF export succeeds to `reports/R3_power_schematic.pdf`.
- Grouped BOM export succeeds to `bom/R3_power_kicad_bom.csv`.
- ERC: **0 errors, 378 warnings**.
  - warnings remain limited to `lib_symbol_mismatch` and `endpoint_off_grid` from the SKiDL embedded-library/deterministic label-only drawing path;
  - there are no power-pin, conflicting-driver or required-pin connectivity errors.
- No power-pin, conflicting-driver, unconnected-required-pin or footprint-link ERC errors remain.
- `tools/logical_nets.json` contains distinct `DGND` and `GND_ISO` nets.
- J3/J6 contain isolated ground only. All other connectors are primary-side or raw-battery-side; no connector contains both `DGND` and `GND_ISO`.
- `VIN9_RAW`, `VIN9_PROT`, shared `+5V_PREISO_FILT` and connector-exposed `EN_5V_UVLO` are absent.
- U1 TPS62132 and U2 TPS54302 are fed from `VSYS_PROT`.
- U3 and U6 retain independent `+5V_PREISO_ADS` and `+5V_PREISO_INA` inputs.
- The PCB is 160 x 80 mm, has four copper layers, 176 footprints, one
  all-copper-layer isolation rule area, and **0 tracks / 0 vias**.
- The placement generator reports **0 courtyard overlaps**. PCB DRC reports
  256 ordinary placement/footprint findings, 371 expected unrouted
  connections, and 218 schematic-parity warnings caused mainly by the
  generated/local footprint representation. The 256 consist of 104
  silk-over-copper, 89 silk overlaps, 20 footprint-internal clearance, 18
  connector copper-to-edge, 13 silk-to-edge, 8 drill-range and 4 annular-width
  findings. There is no remaining net-conflict warning.
- This is a placement checkpoint. Unrouted connections and silkscreen cleanup
  are intentionally not claimed as routing-release DRC closure.
- `reports/R3_power_preliminary_placement.svg` and high-resolution `.png`
  capture the top-side placement. `reports/R3_power_zone_isolation_annotated.*`
  shows the zone boundaries, all-layer isolation corridor and thermal notes.

## Datasheet checks

- TPS62132: 3-17 V input, 100% duty mode, fixed-output FB connected to AGND/DGND.
- TPS54302: 4.5-28 V recommended VIN, internal UVLO about 4.1 V typical, EN tied to `VSYS_PROT`; 6 V/5 V full-load dropout still requires bench validation.
- TPS2121RUXR: verified RUX VQFN-HR-12 pinout and 2.8-22 V/4.5 A operating class.
- BQ25798RQM: verified all 29 pins against TI Table 5-1; 3.6-24 V, 1-4S, 5 A charge and NVDC power path.
- BQ28Z610DRZR: verified all 12 pins plus EP; 1-2S monitoring, protection, current measurement, NTC, high-side FET drive and internal balancing.
- BQ28Z610 typical 2S connection: verified VC2=stack top, VC1=cell midpoint
  and VSS=stack negative. Measurement filters are VC1-VSS (Cell1) and
  VC2-VC1 (Cell2). The common-drain DSG/CHG FET orientation, 5.1 kOhm gate
  resistors, 10 MOhm gate-source bias and 100 nF drain-source capacitors
  remain as reviewed against the EVM.
- STUSB4500QTR: verified QFN-24 pinout, 4.1-22 V VDD, 3.0-5.5 V VSYS, CC1DB/CC2DB dead-battery connections, 1 uF regulator bypass and autonomous three-PDO operation.
- BQ25798 Rev.C: charger-local VBUS bypass is 100 nF plus three 10 uF ceramics; ILIM_HIZ default is approximately 0.50 A using 243 kOhm/100 kOhm.
- Bourns SMBJ13A: 13 V VRWM, 14.4-15.9 V breakdown and 21.5 V clamp at 28 A (10/1000 us); applied to service and 12 V USB-PD inputs.
- Previously verified TPS62132, TPS54302, RS3E-0505S/H3, RS3-0505D/H3, ADM7150 and TPS7A2033 mappings remain unchanged except TPS54302 EN strategy.
- CSD17577Q3AT: 30 V; 4.8 mOhm maximum RDS(on) at 10 V and 13 nC typical
  gate charge. BQ28Z610 on-drive is 8.75-10.25 V, so the 10 V rating is the
  relevant comparison point.
- F1 `MF-R250-0-10`: 30 V, 2.50 A hold/5.00 A trip at 23 C, 1.70 A hold at 60 C.
- F2 `MF-MSMF260/16X-2`: 16 V, 2.60 A hold/5.00 A trip at 23 C, 2.00 A hold at 60 C.
- F3 `MF-MSMF250/16X-2`: 16 V, 2.50 A hold/5.00 A trip at 23 C, 1.85 A hold at 60 C.
- Separate SEMITEC `103AT-2` probes are fixed for NTC_BMS and NTC_CHG:
  10.0 kOhm at 25 C, B25/85=3435 K, 1%.

## Logical review

- Battery connector provides `BAT_POS_RAW`, `CELL_MID`, `BAT_NEG_RAW`, `NTC_BMS`.
- J9 returns `NTC_CHG` directly to `DGND`; its PCB return must be a quiet/Kelvin path to the BQ25798 ground area and must not cross the battery shunt.
- STUSB4500 owns CC1/CC2; legacy independent 5.1 kOhm Rd resistors are absent. CC1DB/CC2DB provide documented dead-battery Rd.
- STUSB4500 RESET is directly on `DGND`. PDO3 is 12 V/2 A and
  `POWER_OK_CFG=10b`, so `PD_CONTRACT_12V_N` corresponds only to a successful
  PDO3 contract after PS_READY.
- U11 is electrically unconnected and explicitly marked as a DNP
  footprint-space reservation; it is not a functional BQ294502 circuit.
- J10 pins 9/10 are `PD_ALERT_N` and `PD_CONTRACT_12V_N`.
- BQ28Z610 shunt inputs are connected through separate 100-ohm Kelvin filters and a differential 100 nF capacitor.
- Charger/status/BMS I2C remain in the primary domain.
- BQ25798 SYS creates `VSYS_RAW`; F3 produces `VSYS_PROT` for the existing primary converters.
- USB and service input are muxed before the charger; J1 no longer defines the system voltage.

## Visual review

The ten-page PDF was rendered page-by-page after deterministic layout. Root hierarchy, revised BMS/FET network, USB-C PD controller/protection, charger-local bypass, existing primary converters, isolation, clean LDOs and output connectors were inspected for clipping and component overlap. The dense battery sheet remains A3 and the charger/power-path sheet remains A2.

## Required before PCB routing

1. Validate Q2/Q3 CSD17577Q3AT protection-event SOA/turn-off and the specified
   200 mm2/thermal-via implementation at 5 A and hot ambient.
2. Program/verify the STUSB4500 NVM record and implement firmware contract-to-IINDPM policy.
3. Program and validate BQ28Z610 chemistry, protection, balancing and recovery data.
4. Validate the two 103AT-2 harness positions and programmed temperature limits.
5. Bench-test TPS54302 at 6.0 V and RS3 dual at the INA851 light load.
6. Measure real expected/peak loads and hot ambient; validate the fixed
   F1/F2/F3 parts and connector/wire/copper ratings. F2 cannot guarantee a
   continuous 2.25 A hold at 60 C without thermal/DPM derating.
7. Decide whether the DNP BQ2945xx secondary-OV option is populated and complete its exact active circuit if so.
8. Approve the 3.0 mm low-voltage functional-isolation rule; do not treat it as
   a mains/reinforced-insulation certification.
9. Check J3/J10 mating housing, latch, enclosure and bend-radius clearance in mechanical CAD.
10. Resolve or formally waive the 378 generator/library/grid warnings.
