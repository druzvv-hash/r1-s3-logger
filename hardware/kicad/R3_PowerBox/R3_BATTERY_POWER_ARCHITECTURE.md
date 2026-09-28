# R3 PowerBox 2S battery and power architecture

Date: 2026-09-28
Status: architecture pass; schematic implementation is provisional and not a procurement or PCB-routing release.

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

The old 511 kOhm / 105 kOhm external EN divider was copied from the 8-28 V reference design and would block part of the required 2S range. It has been removed; EN follows `VSYS_PROT`. Battery undervoltage protection is owned by the BMS and TPS54302 retains internal UVLO.

## Implemented architecture

```text
2S cells: BAT_POS_RAW / CELL_MID / BAT_NEG_RAW
  -> BQ28Z610 gauge + protection + cell balancing
  -> high-side CHG/DSG N-FET pair (exact MPN open)
  -> PACK_POS
  -> 10 mOhm Kelvin shunt in negative path -> DGND

USB-C 5 V fallback -> F2 / TVS ---+
                                     -> TPS2121 input mux -> CHARGER_IN
J1 service/bench 6-12 V -> existing protection ---+

CHARGER_IN -> BQ25798 buck-boost NVDC charger/power-path
PACK_POS   -> BQ25798 BAT
BQ25798 SYS -> VSYS_RAW -> F3 system protection -> VSYS_PROT

VSYS_PROT -> TPS62132 -> +3V3_D
VSYS_PROT -> TPS54302 -> +5V_PREISO
  -> independent +5V_PREISO_ADS filter -> RS3E -> ADS isolated rails
  -> independent +5V_PREISO_INA filter -> RS3 dual -> INA851 +/-5 V
```

`DGND` and `GND_ISO` remain galvanically separate. `BAT_NEG_RAW` is in the primary domain but is not the same schematic net as `DGND` because the Kelvin current shunt lies between them.

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

## USB-C and PD decision

The schematic currently implements a standards-recognizable **5 V sink fallback** using independent 5.1 kOhm Rd resistors on CC1/CC2. No USB data path is used. A PD controller is intentionally not fixed in this pass.

For 2S, 12 V PD is recommended if 2 A charging is required:

- 5 V avoids a PD controller but forces boost-mode charging and high cable/input current;
- 12 V PD lets BQ25798 operate mainly in buck mode, lowers cable current and usually reduces thermal stress;
- 9 V PD has limited headroom near an 8.4 V battery and is less attractive than 12 V.

PD sink candidates for the next decision:

- STUSB4500: standalone sink with nonvolatile PDO configuration; simple host-independent operation;
- Infineon CYPD3177: resistor-configured standalone sink, good repairability and no application firmware;
- TI TPS25750: highly integrated PD policy engine and charger-oriented ecosystem, but more configuration complexity.

If PD is added, R70/R71 are removed from the direct CC path and the chosen controller owns CC1/CC2. Undocumented trigger modules are not acceptable.

## Input and power-path behavior

TPS2121 combines the USB input and the retained J1 service/bench input. It supports 2.8-22 V, reverse-current blocking, seamless switchover and programmable current limiting. R73 currently targets about 2.5 A typical. J1 keeps its PTC, reverse-polarity PMOS, TVS and filter, but is now explicitly an alternate charger input rather than a fixed 9 V system rail.

BQ25798 NVDC power-path supplies R3:

- from external input with battery absent;
- from battery with external input absent;
- while charging;
- with input-current/voltage DPM and battery supplement behavior during source overload.

## Temperature sensing

One NTC cannot be connected directly to both BQ28Z610 TS1 and BQ25798 TS because each IC biases its input. The schematic therefore provides:

- J8 pin 4: `NTC_BMS` for BQ28Z610;
- J9: optional separate `NTC_CHG` and `BAT_NEG_RAW` return for BQ25798.

This is deliberately visible rather than silently tying the pins together. Before PCB layout choose dual thermistors, an approved buffer/supervisor scheme, or a documented single-controller safety policy. Dual thermistors are the current recommendation.

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
9. NC
10. NC

BQ28Z610 has no dedicated general fault interrupt pin. Critical faults autonomously control CHG/DSG FETs; detailed status is read over I2C. If the MCU requires a separate hardware BMS fault line, an additional supervisor or FET-state detector is still open.

## Power budget assumptions

The expected table is an engineering planning case, not a measured result. It assumes STM32/ESP32/SD average digital load of 0.85 A at 3.3 V, about 0.8 W into the ADS isolated converter, and about 0.25 W no/light-load input for the INA converter. Peak is a plausible simultaneous activity case. Design worst case is the sum of converter nameplate limits and is not an intended operating mode.

### A. Design worst case

| Rail | Voltage | Worst current | Output power | Assumed efficiency | Upstream input/current | Thermal estimate |
|---|---:|---:|---:|---:|---:|---:|
| `VSYS_PROT` | 6.0-8.4 V | 3.30 A at 6 V equivalent | 19.8 W input demand | - | battery: 3.30 A at 6 V | wiring/FET/shunt case, not normal load |
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
- F3 system protection: target at least 2.0 A hold at maximum enclosure temperature; exact PPTC/fuse remains open after thermal derating;
- charge/input connector and protection: minimum 3 A if 5 V fallback is used near its useful limit.

## Charge-current examples

Assuming 90% charger efficiency and 4.4 W simultaneous system load:

| Charge setting | Battery charge power at 8.4 V | Total input power | 5 V input current | 12 V input current | Consequence |
|---:|---:|---:|---:|---:|---|
| 1 A | 8.4 W | about 14.2 W | about 2.84 A | about 1.18 A | feasible only from a known 5 V/3 A source; 12 V preferred thermally |
| 2 A | 16.8 W | about 23.6 W | about 4.71 A | about 1.96 A | not valid from standard 5 V USB-C; requires PD/high-power source and thermal validation |

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

Existing primary and isolated test points are retained. Dirty and clean points belong on opposite physical areas.

## PCB floorplan and layers

The PCB draft is expanded to four explicit spatial zones:

```text
DIRTY EDGE                     MIDDLE                    CLEAN EDGE
+----------------------+----------------+-----------+----------------------+
| USB-C / J1 / battery | TPS62132       | RS3E/RS3  | ADM7150 / TPS7A20    |
| TPS2121 / BQ25798    | TPS54302       | isolation | clean filters        |
| BQ28Z610 / FET/shunt | digital output | keep-out  | ADS/INA connectors   |
+----------------------+----------------+-----------+----------------------+
```

Charger SW1/SW2 and L3 stay entirely inside Zone A. TPS62132/TPS54302 switching loops stay in Zone B. RS3E/RS3 sit at the isolation corridor, not in the clean LDO area. USB/battery and clean connectors are on opposite edges. The draft contains an explicit copper/via/pad keepout strip at the isolation barrier; no tracks or zones were routed.

A four-layer board is recommended:

- L1 components/signals and compact switching loops;
- L2 continuous primary DGND plane, interrupted only by the isolation corridor;
- L3 power distribution/quiet routing with no copper under the barrier;
- L4 secondary routing and clean ground/power areas.

Four layers improve return-path control, EMI and heat spreading enough to justify the added cost. A two-layer board remains possible only with larger area and more difficult control of charger/switcher return currents; it is not recommended for the low-noise R3 objective.

## Open technical decisions and blockers

1. Select PD strategy/controller. Current hardware is 5 V fallback only; 12 V PD is recommended for 2 A charge.
2. Select exact BMS CHG/DSG MOSFETs and verify the 5 A thermal path and BQ28Z610 gate-drive behavior.
3. Decide dual-NTC versus buffered/supervised single-NTC architecture.
4. Freeze battery chemistry/capacity and program/validate BQ28Z610 protection, balancing, recovery and gauge parameters.
5. Validate BQ25798/BQ28Z610 host/master-mode interoperability and define boot-safe charger register defaults.
6. Bench-test TPS54302 5 V regulation and transients at VSYS = 6.0 V.
7. Resolve RS3-0505D/H3 light-load and rail-balance behavior for INA851.
8. Freeze expected/peak measured loads, then choose F2/F3, connector contacts, MOSFETs and copper widths.
9. Define formal creepage/clearance from working voltage and safety requirements.

PCB routing and production outputs remain blocked until these decisions are closed.

## Original manufacturer references

- TI TPS62132: https://www.ti.com/lit/ds/symlink/tps62132.pdf
- TI TPS54302: https://www.ti.com/lit/ds/symlink/tps54302.pdf
- TI TPS2121: https://www.ti.com/lit/ds/symlink/tps2121.pdf
- TI BQ25798: https://www.ti.com/lit/ds/symlink/bq25798.pdf
- TI BQ28Z610: https://www.ti.com/lit/ds/symlink/bq28z610.pdf
- TI BQ25713 candidate: https://www.ti.com/lit/ds/symlink/bq25713.pdf
- TI BQ24780S candidate: https://www.ti.com/lit/ds/symlink/bq24780s.pdf
- ST STUSB4500 candidate: https://www.st.com/resource/en/datasheet/stusb4500.pdf
- TI TPS25750 candidate: https://www.ti.com/lit/ds/symlink/tps25750.pdf
- Infineon CYPD3177 candidate product page: https://www.infineon.com/part/CYPD3177-24LQXQ
