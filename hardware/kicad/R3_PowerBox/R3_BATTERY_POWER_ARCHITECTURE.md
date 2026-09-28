# R3 PowerBox 2S battery and power architecture

Date: 2026-09-28
Status: final UI / power-control / DRC pass complete; electrical validation gates
remain before a routing release.

## Fixed system decision

R3 uses one onboard-managed **2S Li-ion battery**:

- nominal stack voltage: about 7.4 V;
- maximum charge voltage: 8.4 V;
- preliminary operating system range: 6.0-8.4 V;
- final per-cell undervoltage thresholds remain a chemistry/BMS configuration decision.

There is no separate BMS/charger board and no intermediate 2S-to-9 V converter.

## Direct 2S operation of the existing converters

### TPS62132

The official datasheet specifies 3-17 V input, 3 A output and 100% duty-cycle operation. A 6.0-8.4 V system rail is therefore inside the guaranteed input range with ample headroom for 3.3 V. Startup UVLO is below the 2S range. Existing soft-start, FB-to-AGND connection, inductor and output capacitors are retained.

### TPS54302

The official datasheet specifies 4.5-28 V input, 3 A, 400 kHz operation and internal VIN UVLO of 4.1 V typical. At 6.0 V input, an ideal 5 V output requires 83.3% duty cycle. This is within a normal buck operating region, but TI's published reference design is characterized from 8 V and the datasheet does not give a guaranteed dropout curve at 5 V/3 A. Direct 2S operation is retained, with a required bench test at 6.0 V under load and transient conditions.

The old 511 kOhm / 105 kOhm external EN divider was copied from the 8-28 V reference design and would block part of the required 2S range. It has been removed; EN follows the switched `VSYS_MAIN` rail. Battery undervoltage protection is owned by the BMS and TPS54302 retains internal UVLO.

## Implemented architecture

```text
2S cells: BAT_POS_RAW / CELL_MID / BAT_NEG_RAW
  -> BQ28Z610 gauge + protection + cell balancing
  -> TI-EVM-style common-drain CSD17577Q3AT DSG/CHG N-FET pair
  -> PACK_POS
  -> 10 mOhm Kelvin shunt in negative path -> DGND

USB-C -> F2 / SMBJ13A / STUSB4500 (5/9/12 V PD) ---+
                                     -> TPS2121 input mux -> CHARGER_IN
J1 service/bench 6-12 V -> existing protection ---+

CHARGER_IN -> BQ25798 buck-boost NVDC charger/power-path
PACK_POS   -> BQ25798 BAT
BQ25798 SYS -> VSYS_RAW -> F3 system protection -> VSYS_PROT
             -> Q4 DMP3007LSS user load switch -> VSYS_MAIN

VSYS_MAIN -> TPS62132 -> +3V3_D
VSYS_MAIN -> TPS54302 -> +5V_PREISO
  -> independent +5V_PREISO_ADS filter -> RS3E -> ADS isolated rails
  -> independent +5V_PREISO_INA filter -> RS3 dual -> INA851 +/-5 V
```

`DGND` and `GND_ISO` remain galvanically separate. `BAT_NEG_RAW` is in the primary domain but is not the same schematic net as `DGND` because the Kelvin current shunt lies between them.

## USER POWER AND INDICATION

Normal user power control is deliberately downstream of the charger. Q4
`DMP3007LSS-13` is a 30 V P-channel SO-8 high-side switch between
`VSYS_PROT` and `VSYS_MAIN`. R102 (100 kOhm) returns its gate to the source, so
the default/unplugged state is OFF. Local maintained SW1 or a remote switch on
J11 closes `POWER_CTRL` to DGND through R103 (10 kOhm); C107 (100 nF) controls
the gate edge. The switch carries about 55-76 uA over 6.0-8.4 V, not load
current.

At a conservative hot RDS(on) of 15 mOhm, Q4 drop/loss is:

| Main current | Voltage drop | Q4 dissipation |
|---:|---:|---:|
| 1.0 A | 15 mV | 15 mW |
| 2.0 A | 30 mV | 60 mW |
| 3.3 A | 49.5 mV | 163 mW |

With SW1 OFF, BQ28Z610, STUSB4500 and BQ25798 remain operational and charging
continues; only `VSYS_MAIN` and the downstream R3 electronics are removed.
QON is separately connected to momentary SW2/J11.4 for ship exit, wake and the
documented long-hold reset. It is not the normal user power switch, and no
external ship FET is populated in Rev.A.

The red CHG indicator is powered from BQ25798 REGN through 2.2 kOhm and sinks
into raw open-drain `BQ_STAT_RAW`, so it works while `VSYS_MAIN` is off.
`CHARGE_STATUS` has a separate 10 kOhm pull-up to +3V3_D and reaches raw STAT
only through D7 `BAT54WS-7-F` (anode at logic, cathode at raw STAT). This
prevents the REGN/LED circuit from back-powering the main 3.3 V rail. The green
RUN indicator is powered from +3V3_D and therefore shows actual main-rail
operation. Battery level is software-derived from BQ28Z610 SOC/capacity over
PM I2C rather than an analog voltage LED bar.

J11 USER PANEL is primary-only: 1 +3V3_D, 2 DGND, 3 POWER_CTRL,
4 QON_SERVICE, 5 CHARGE_STATUS, 6 PG_3V3_D, 7 PM_I2C_SCL, 8 PM_I2C_SDA,
9 BQ_STAT_RAW and 10 SPARE/NC. It never carries GND_ISO or shared onboard LED
anode nets. Panel indicators require their own series resistors. POWER_CTRL is
for a latching contact to DGND only; QON_SERVICE is for a momentary contact to
DGND only.

## Charger and power-path comparison

| Candidate | Topology and strengths | Costs/risks | Result |
|---|---|---|---|
| TI BQ25798 | 3.6-24 V input, 1-4 cells, integrated four-switch buck-boost, integrated BATFET/current sensing, 5 A programmable charge, NVDC power path, DPM, I2C, ADC and NTC; 29-pin 4x4 mm QFN | fine-pitch QFN, firmware/register configuration, switching noise must be confined to Zone A; no per-cell balancing | **Implemented provisional recommendation**; works from 5 V and future 9/12 V PD without changing charger |
| TI BQ25713 | 1-4 cell buck-boost NVDC controller with external power MOSFETs; high power and repairable external switches | largest BOM/area, most high-current loops and gate-drive layout risk | Good for substantially higher power; unnecessarily complex for current R3 load |
| TI BQ24780S | SMBus narrow-VDC buck charger, suitable for 12 V PD to 2S and external FETs | cannot charge 2S from 5 V without another boost stage; external FET/BOM complexity | Lowest conversion complexity with mandatory 12 V PD, but loses useful 5 V fallback |

The BQ25798 is not treated as the BMS. Its charger protections do not replace independent per-cell OV/UV, short-circuit and pack-current protection.

## BMS, protection and balancing comparison

| Candidate | Coverage | Result |
|---|---|---|
| TI BQ28Z610 | 1-2S gauge, per-cell measurement, programmable voltage/current/temperature protection, high-side CHG/DSG N-FET drive, internal 200-ohm balancing paths, coulomb counter, I2C/SOC | **Implemented provisional recommendation** |
| TI BQ40Z50-R2 | 2-4S gauge/protector/balancer with more pins and pack-management features | technically capable but larger and unnecessarily complex for fixed 2S |
| TI BQ29209 plus separate protector/gauge | 2S overvoltage protection and balancing | incomplete by itself: still needs UV, current/short protection, current measurement and SOC; more ICs and validation |

The BQ28Z610 requires data-flash configuration and validation of OV, UV, overcurrent, short-circuit, temperature, recovery, balancing and FET behavior before it is safety-relevant.

### BQ28Z610 reference-network correction

The schematic now follows BQ28Z610EVM Figure 20 for the requested functions:

- `VC2` senses `BAT_POS_RAW`; `VC1` senses `CELL_MID`; VSS senses
  `BAT_NEG_RAW`;
- the retained 100 ohm Kelvin resistors feed the two VC pins;
- 100 nF is connected VC1-to-VSS for Cell1 and another 100 nF VC2-to-VC1
  for Cell2;
- the high-side N-FETs are common-drain: `PACK_POS -> Q2 DSG source`, common
  drains, then `Q3 CHG source -> BAT_POS_RAW`;
- each gate has the EVM-class 5.1 kOhm series resistor and 10 MOhm
  gate-to-local-source bias; each FET has 100 nF drain-source capacitance;
- the 10 mOhm Kelvin shunt, 100 ohm SRP/SRN resistors and 100 nF differential
  capacitor are retained.

U11 is only an unconnected DNP DRV0006A footprint-space reservation for a
possible future `BQ294502DRVR`/BQ2945xx secondary-overvoltage circuit. It is
not a populate-able or functional protection circuit and must not be fitted in
Rev.A. The exact threshold variant, cell RC network, OUT/fuse interface and
local bypass must be designed and reviewed before any future population.

### Q2/Q3 MOSFET study

Losses below use published **maximum** RDS(on) at 10 V and two series devices
at 25 C, matching the BQ28Z610 nominal 9.5 V drive more closely. Hot
resistance/PCB copper must still be validated.

| Candidate | VDS / package | Max RDS(on) @10 V | Pair loss @1 A | @3.3 A | @5 A | Comment |
|---|---|---:|---:|---:|---:|---|
| TI CSD17577Q3A | 30 V, SON 3.3 x 3.3 mm | 4.8 mOhm | 9.6 mW | 104.5 mW | 240 mW | **selected for Rev.A**; compact, 13 nC Qg |
| Vishay SiRA80DP | 30 V, PowerPAK SO-8 | 0.62 mOhm | 1.24 mW | 13.5 mW | 31.0 mW | lowest conduction loss; about 60 nC Qg |
| Vishay SQJA26EP | 30 V, PowerPAK SO-8L | 0.77 mOhm | 1.54 mW | 16.8 mW | 38.5 mW | AEC-Q101; larger package and gate charge |

`CSD17577Q3AT` is the fixed Rev.A pre-routing Q2/Q3 selection. The BQ28Z610 specifies
8.75-10.25 V FET-on drive over the relevant stack range, so the device's
4.8 mOhm maximum RDS(on) at 10 V is the correct nominal design point. Pair
loss is 9.6 mW at 1 A, 104.5 mW at 3.3 A and 240 mW at 5 A at 25 C. Its
13 nC typical gate charge is materially easier on the gauge's protected FET
drive than the roughly 60 nC SiRA80DP. A project-local DQG/VSON footprint is
assigned. Using 1.8x the 25 C maximum RDS(on) as a conservative hot estimate,
pair loss is 17.3 mW at 1 A, 188 mW at 3.3 A and 432 mW at 5 A. Reserve at
least 200 mm2 combined L1 spreading copper and 4-6 x 0.30 mm finished thermal
vias per FET into primary copper. SOA/short-circuit interruption and assembly
yield remain validation gates, not component-selection blockers.

## USB-C and PD implementation

`STUSB4500QTR` is now the provisional standalone PD sink. It negotiates without
the MCU, is powered from protected connector-side VBUS, and uses the documented
`CC1DB->CC1` / `CC2DB->CC2` dead-battery wiring. Legacy R70/R71 standalone Rd
resistors are removed. USB data remains unused.

The programmed logical NVM profile is:

| PDO | Voltage/current | Use |
|---|---|---|
| PDO1 | 5 V / 3 A maximum capability | Type-C/PD fallback; actual draw remains source-capability limited |
| PDO2 | 9 V / 2 A | secondary PD fallback |
| PDO3 | 12 V / 2 A | preferred R3 contract |

No 15 V or 20 V PDO is advertised. `RESET` is tied directly to `DGND`.
`POWER_OK_CFG=10b` selects ST power-OK configuration 2: `POWER_OK3` is
active-low only after a successful PDO3 contract and PS_READY, so it is valid
as `PD_CONTRACT_12V_N`; `ALERT` is exported as `PD_ALERT_N`. The exact NVM record,
programming and recovery procedure are in `docs/STUSB4500_PD_CONFIG.md`.

Before any confirmed contract/source capability, the BQ25798 243 kOhm/100 kOhm
ILIM_HIZ divider enforces about 0.50 A. Firmware may clear `EN_EXTILIM` and
increase IINDPM only after reading the STUSB4500 state: 1.35 A for confirmed
5 V/1.5 A, 2.25 A for confirmed 5 V/3 A, and 1.80 A for 9 V/2 A or 12 V/2 A.
The 2.25 A cap deliberately stays below the approximately 2.5 A TPS2121 ILIM
and current F2 design class; the 12 V/2 A policy is unchanged.

## Input and power-path behavior

TPS2121 combines the USB input and the retained J1 service/bench input. It supports 2.8-22 V, reverse-current blocking, seamless switchover and programmable current limiting. R73 currently targets about 2.5 A typical. J1 keeps its PTC, reverse-polarity PMOS, TVS and filter, but is now explicitly an alternate charger input rather than a fixed 9 V system rail. D1 and USB D3 are Bourns-class SMBJ13A: 13 V VRWM, 14.4-15.9 V breakdown and 21.5 V maximum clamp at 28 A for a 10/1000 us pulse. At the documented 10 A design surge assumption, linear interpolation gives about 17.9 V, leaving about 4.1 V to the TPS2121 22 V recommended maximum; even the TVS-rated 28 A clamp remains 0.5 V below that recommended maximum and 2.5 V below the 24 V absolute maximum.

BQ25798 has a distinct local VBUS bypass bank of 100 nF plus three 10 uF/25 V ceramics. The 100 nF part is a 0402 intended directly at the VBUS/GND pins; C73 remains TPS2121 output bulk and is not counted as this bypass.

BQ25798 NVDC power-path supplies R3:

- from external input with battery absent;
- from battery with external input absent;
- while charging;
- with input-current/voltage DPM and battery supplement behavior during source overload.

## Temperature sensing

One NTC cannot be connected directly to both BQ28Z610 TS1 and BQ25798 TS because each IC biases its input. The schematic therefore provides:

- J8 pin 4: `NTC_BMS` for BQ28Z610;
- J9: separate `NTC_CHG` and `DGND` return for BQ25798. On PCB this conductor is named/treated as `DGND_CHG_SENSE`: a quiet Kelvin return to the charger ground area, never to `BAT_NEG_RAW` on the battery side of the shunt.

Rev.A therefore uses two separate SEMITEC `103AT-2` probes: 10.0 kOhm at
25 C, B25/85=3435 K, both resistance and B-value tolerance 1%. The harness
entries are recorded in `bom/R3_power_harness_bom.csv`; the probes are not
shared or passively paralleled.

## Battery and MCU telemetry

The BQ28Z610 exposes cell voltages, pack voltage, current, temperature and SOC over primary-side `PM_I2C_SCL/SDA`. These correspond to `CELL1_VOLTAGE`, `CELL2_VOLTAGE`, `BAT_VOLTAGE`, `BAT_CURRENT`, `BAT_TEMPERATURE` and `SOC`; duplicate analog dividers were not added.

J10 exports:

1. `+3V3_D`
2. `DGND`
3. `PM_I2C_SCL`
4. `PM_I2C_SDA`
5. `CHARGE_STATUS`
6. `PG_3V3_D` as system power-good
7. `CHARGER_INT_FAULT`
8. `INPUT_SOURCE_STATUS`
9. `PD_ALERT_N`
10. `PD_CONTRACT_12V_N`

J11 exports the primary user-panel interface documented above. Pin 9 is the
raw open-drain charger status, not a shared LED-anode feed, and J11 contains no
GND_ISO.

BQ28Z610 has no dedicated general fault interrupt pin. Critical faults autonomously control CHG/DSG FETs; detailed status is read over I2C. If the MCU requires a separate hardware BMS fault line, an additional supervisor or FET-state detector is still open.

## Power budget assumptions

The expected table is an engineering planning case, not a measured result. It assumes STM32/ESP32/SD average digital load of 0.85 A at 3.3 V, about 0.8 W into the ADS isolated converter, and about 0.25 W no/light-load input for the INA converter. Peak is a plausible simultaneous activity case. Design worst case is the sum of converter nameplate limits and is not an intended operating mode.

### A. Design worst case

| Rail | Voltage | Worst current | Output power | Assumed efficiency | Upstream input/current | Thermal estimate |
|---|---:|---:|---:|---:|---:|---:|
| `VSYS_PROT` | 6.0-8.4 V | 3.30 A at 6 V equivalent | 19.8 W input demand | - | battery: 3.30 A at 6 V | wiring/FET/shunt case, not normal load |
| `VSYS_MAIN` | 6.0-8.4 V minus Q4 drop | 3.30 A at 6 V equivalent | 19.8 W demand | Q4 >99% | from VSYS_PROT | about 0.163 W at 3.3 A using 15 mOhm hot estimate |
| `+3V3_D` | 3.3 V | 3.00 A | 9.90 W | 90% planning | 11.0 W from VSYS | about 1.1 W converter loss |
| `+5V_PREISO` | 5.0 V | 1.59 A | 7.95 W | 90% planning | 8.83 W from VSYS | about 0.88 W buck loss |
| `+5V_PREISO_ADS` | 5.0 V | 0.80 A nominal / 0.889 A at U3 4.5 V limit | 4.0 W input | branch loss negligible | U3 limited to 3 W output | bead rated 2 A |
| `+5V_PREISO_INA` | 5.0 V | 0.789 A nominal / 0.877 A at U6 4.5 V limit | 3.95 W input | branch loss negligible | U6 limited to 3 W output | bead rated 2 A |
| `+5V_ISO_RAW` | 5.0 V | 0.60 A | 3.00 W | U3 75% typical | 4.0 W from ADS branch | about 1.0 W U3 loss |
| `+5V_ISO_A` | 5.0 V | 0.30 A allocation | 1.50 W | filter | from U3 shared 3 W | measure bead rise |
| `+5V_ISO_D` | 5.0 V | 0.30 A allocation | 1.50 W | filter | from U3 shared 3 W | measure bead rise |
| `+3V3_A_ISO` | 3.3 V | 0.30 A planning cap | 0.99 W | LDO | 1.50 W at 5 V | about 0.51 W LDO loss |
| `+3V3_D_ISO` | 3.3 V | 0.30 A IC limit | 0.99 W | LDO | 1.50 W at 5 V | about 0.51 W LDO loss |
| `+5V_INA` | +5.0 V | 0.30 A converter rating | 1.50 W | U6 combined 76% minimum | shared with negative rail | not a valid INA851 load case |
| `-5V_INA` | -5.0 V | 0.30 A converter rating | 1.50 W | U6 combined 76% minimum | shared with positive rail | not a valid INA851 load case |

### B. Expected R3 load

| Rail | Expected current | Peak current | Expected power | Efficiency/input estimate | Approximate local loss |
|---|---:|---:|---:|---:|---:|
| `VSYS_PROT` | 0.59 A at 7.4 V | 1.08 A at 7.4 V | 4.4 W expected / 8.0 W peak | battery path | shunt 3.5 mW expected |
| `VSYS_MAIN` | 0.59 A at 7.4 V | 1.08 A at 7.4 V | 4.4 W expected / 8.0 W peak | Q4 >99% | about 5.2 mW expected / 17.5 mW peak using 15 mOhm |
| `+3V3_D` | 0.85 A | 1.50 A | 2.81 W | 90%; about 3.12 W input | about 0.31 W expected |
| `+5V_PREISO` | 0.21 A | 0.44 A | 1.05 W | 90%; about 1.17 W input | about 0.12 W expected |
| `+5V_PREISO_ADS` | 0.16 A | 0.35 A | 0.80 W | feeds U3 | bead loss negligible at expected load |
| `+5V_PREISO_INA` | 0.05 A | 0.10 A | 0.25 W | dominated by U6 light-load draw | validate on bench |
| `+5V_ISO_RAW` | 0.12 A | 0.25 A | 0.60 W | about 75% U3 | about 0.20 W expected |
| `+5V_ISO_A` | 0.08 A | 0.15 A | 0.40 W | ADM7150 input | filter loss small |
| `+5V_ISO_D` | 0.04 A | 0.10 A | 0.20 W | TPS7A20 input | filter loss small |
| `+3V3_A_ISO` | 0.08 A | 0.15 A | 0.264 W | LDO | about 0.136 W expected |
| `+3V3_D_ISO` | 0.04 A | 0.10 A | 0.132 W | LDO | about 0.068 W expected |
| `+5V_INA` | 6 mA | 20 mA | 30 mW | U6 light-load operation | included in U6 idle loss |
| `-5V_INA` | 6 mA | 20 mA | 30 mW | U6 light-load operation | included in U6 idle loss |

### Battery current

| Battery voltage | Expected 4.4 W | Peak 8.0 W | Design-worst 19.8 W |
|---:|---:|---:|---:|
| 8.4 V | 0.52 A | 0.95 A | 2.36 A |
| 7.4 V | 0.59 A | 1.08 A | 2.68 A |
| 6.0 V | 0.73 A | 1.33 A | 3.30 A |

## Battery-path sizing target

Based on expected peak rather than only regulator nameplates:

- keyed battery connector: at least 5 A/contact system rating with suitable wire;
- BMS path and protection FETs: 5 A continuous design target, at least 8-10 A short transient capability, at least 20 V VDS;
- shunt: 10 mOhm, 1 W, Kelvin connected; 0.25 W at 5 A;
- battery/system copper: size for 5 A local path and temperature rise, not for average current only;
- TPS2121 input mux: 2.5 A typical current-limit target in current draft;
- F1 service input: Bourns `MF-R250-0-10`, 30 V, 2.50 A hold/5.00 A trip at
  23 C, 1.70 A hold at 60 C, radial 5.1 mm pitch;
- F2 USB input: Bourns `MF-MSMF260/16X-2`, 16 V, 2.60 A hold/5.00 A trip at
  23 C, 2.00 A hold at 60 C, 1812;
- F3 system rail: Bourns `MF-MSMF250/16X-2`, 16 V, 2.50 A hold/5.00 A trip at
  23 C, 1.85 A hold at 60 C, 1812;
- charge/input connector and protection: minimum 3 A if 5 V fallback is used near its useful limit.

The PPTCs are fixed for Rev.A placement/BOM, but hot sustained current is still
a validation gate. In particular, the 2.25 A confirmed 5 V/3 A firmware policy
exceeds F2's 60 C hold value; charger thermal/DPM derating or a separately
reviewed fuse option is required if that combination must be continuous.

## Charge-current examples

Assuming 90% conversion efficiency and 4.4 W simultaneous expected system
load, required adapter input is `(VBAT * ICHG + 4.4 W) / 0.90`:

| VBAT | 1 A charge input power / current at 12 V | 2 A charge input power / current at 12 V |
|---:|---:|---:|
| 6.0 V | 11.56 W / 0.96 A | 18.22 W / 1.52 A |
| 7.4 V | 13.11 W / 1.09 A | 21.33 W / 1.78 A |
| 8.4 V | 14.22 W / 1.19 A | 23.56 W / 1.96 A |

The 12 V/2 A contract is limited in firmware to 1.80 A (21.6 W) for margin.
It supports 2 A charging at low/mid state of charge with expected system load,
but cannot maintain a full 2 A near 8.4 V or during the 8 W system peak. Input
DPM must reduce charge current; battery supplement may carry brief system peaks.
At 9 V/2 A with a 1.80 A policy limit, only 16.2 W is available, so 2 A charge
is not sustainable and even 1 A charge must be power-managed at peak load.
Unknown 5 V starts at 0.50 A (2.5 W), which may require battery supplement and
does not guarantee charging. Confirmed 5 V/1.5 A or 3 A may use the documented
1.35 A or 2.25 A limits, respectively.

Charge current remains programmable and is not frozen until cell capacity, allowed C-rate, connector temperature and enclosure cooling are known.

## Test points

New dirty-side test points:

- TP20 `USB_VBUS_RAW`
- TP21 `CHARGER_IN`
- TP22 `VSYS_RAW`
- TP23 `VSYS_PROT`
- TP24 `BAT_POS_RAW`
- TP25 `CELL_MID`
- TP26 `BAT_NEG_RAW`
- TP27 `BMS_SRP_FILT`
- TP28 `BMS_SRN_FILT`
- TP29 `NTC_BMS`
- TP30 `NTC_CHG`
- TP31 `USB_CC1`
- TP32 `USB_CC2`
- TP33 `USB_VBUS_PROT`
- TP34 `PD_VDD` (fed from protected VBUS through the 0 ohm R85 link)
- TP35 `PD_VREG_2V7`
- TP36 `PD_ALERT_N`
- TP37 `PM_I2C_SCL`
- TP38 `PM_I2C_SDA`
- TP39 `QON_SERVICE`
- TP40 `VSYS_MAIN`

Existing primary and isolated test points are retained. Dirty and clean points belong on opposite physical areas.

## PCB floorplan and layers

The PCB draft uses four explicit spatial zones:

```text
DIRTY EDGE                     MIDDLE                    CLEAN EDGE
+----------------------+----------------+-----------+----------------------+
| USB-C / J1 / battery | TPS62132       | RS3E/RS3  | ADM7150 / TPS7A20    |
| TPS2121 / BQ25798    | TPS54302       | isolation | clean filters        |
| BQ28Z610 / FET/shunt | Q4 / J10 / J11 | keep-out  | ADS/INA connectors   |
+----------------------+----------------+-----------+----------------------+
```

Charger SW1/SW2 and L3 stay entirely inside Zone A. TPS62132/TPS54302
switching loops stay in Zone B. U3/U6 pins 1/2/3 face primary and pins
5/6/7/8 face clean. The full-height x=121...124 mm rule area blocks pads,
vias, tracks and pours on all four copper layers. The SIP8 geometry provides
3.08 mm edge-to-edge between pad 3 and pad 5, so the adopted rule is 3.0 mm
minimum copper clearance and board-surface creepage. This is a low-voltage
functional-isolation rule, not a mains/reinforced certification claim.

A four-layer board is recommended:

- L1 components/signals and compact switching loops;
- L2 continuous primary DGND plane, interrupted only by the isolation corridor;
- L3 power distribution/quiet routing with no copper under the barrier;
- L4 secondary routing and clean ground/power areas.

Four layers improve return-path control, EMI and heat spreading enough to
justify the added cost. No thermal copper, plane or via may cross the isolation
corridor. L3 charger, L1 TPS62132 and L2 TPS54302 are alternately oriented;
U3/U6 are vertically separated from that magnetic group and from the clean
LDOs. Board size remains 160 x 80 mm.

## Mechanical mounting and future R3 stacking

The PowerBox now has six 3.20 mm NPTH M3 holes with no electrical net or
plating. Their coordinates are H1 (35.0,25.5), H2 (174.5,25.5), H3
(25.5,94.5), H4 (174.5,94.5), H5 (115.0,25.5) and H6 (135.0,94.5). Every
hole includes an 8 mm all-copper-layer keepout/courtyard. No hole or hardware
enters the x=121...124 mm functional-isolation corridor; insulating standoffs
are the prototype default.

Cable assembly remains fully supported. Optional DNP J12 (primary 2x8) and J13
(isolated 2x5) provide parallel generic 2.54 mm THT stacking interfaces without
mixing DGND and GND_ISO. The future-R3 envelope is a `Dwgs.User` reference only.
Use 15 mm standoffs as the baseline because U3/U6 are 11.1 mm high; 12 mm is
conditional on an upper-board cutout/keepout. Exact dimensions, pinouts and
header/socket guidance are maintained in
`docs/R3_BOARD_TO_BOARD_INTERFACE.md`.

## Open technical decisions and blockers

1. Program and compliance-test the provisional STUSB4500 5/9/12 V NVM profile and firmware current-limit policy.
2. Validate CSD17577Q3AT protection-event SOA/turn-off and the specified
   thermal-copper implementation at 5 A/hot conditions.
3. Validate both 103AT-2 harness locations and temperature thresholds.
4. Freeze battery chemistry/capacity and program/validate BQ28Z610 protection, balancing, recovery and gauge parameters.
5. Validate BQ25798/BQ28Z610/STUSB4500 shared-bus interoperability and the boot-safe 0.50 A charger default.
6. Bench-test TPS54302 5 V regulation and transients at VSYS = 6.0 V.
7. Resolve RS3-0505D/H3 light-load and rail-balance behavior for INA851.
8. Measure expected/peak loads and hot ambient, then validate the fixed
   F1/F2/F3 choices, connector contacts and copper widths.
9. Decide whether the reserved BQ2945xx secondary-OV footprint is populated; its active network is intentionally DNP/unconnected in Rev.A.
10. Check J3/J10/J11 mating-housing, latch, enclosure and cable-bend clearances in
    mechanical CAD.
11. Freeze J12/J13 long-post header/socket MPNs and verify engagement at the
    selected 15 mm spacing; validate the M3 hardware diameter against the 8 mm
    local keepouts.

PCB routing and production outputs remain blocked until these decisions are closed.

## Original manufacturer references

- TI TPS62132: https://www.ti.com/lit/ds/symlink/tps62132.pdf
- TI TPS54302: https://www.ti.com/lit/ds/symlink/tps54302.pdf
- TI TPS2121: https://www.ti.com/lit/ds/symlink/tps2121.pdf
- TI BQ25798: https://www.ti.com/lit/ds/symlink/bq25798.pdf
- TI BQ28Z610: https://www.ti.com/lit/ds/symlink/bq28z610.pdf
- TI BQ25713 candidate: https://www.ti.com/lit/ds/symlink/bq25713.pdf
- TI BQ24780S candidate: https://www.ti.com/lit/ds/symlink/bq24780s.pdf
- ST STUSB4500: https://www.st.com/resource/en/datasheet/stusb4500.pdf
- TI BQ28Z610EVM: https://www.ti.com/lit/ug/sluube3/sluube3.pdf
- Bourns SMBJ series: https://www.bourns.com/data/global/pdfs/SMBJ.pdf
- Bourns MF-R: https://www.bourns.com/docs/product-datasheets/mf-r.pdf
- Bourns MF-MSMF: https://www.bourns.com/docs/product-datasheets/mf-msmf.pdf
- SEMITEC 103AT-2: https://www.semitec-global.com/products/thermistor_at/
- TI CSD17577Q3A: https://www.ti.com/lit/ds/symlink/csd17577q3a.pdf
- ST ESDA25W: https://www.st.com/resource/en/datasheet/esdaxxxwx.pdf
- TI TPS25750 candidate: https://www.ti.com/lit/ds/symlink/tps25750.pdf
- Infineon CYPD3177 candidate product page: https://www.infineon.com/part/CYPD3177-24LQXQ
