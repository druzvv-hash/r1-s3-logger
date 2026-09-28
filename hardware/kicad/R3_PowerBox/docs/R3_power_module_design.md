# R3 PowerBox design notes

Status: unified 2S architecture review; not ready for PCB routing.

Authoritative documents:

- `../R3_POWER_REVIEW.md`
- `../R3_BATTERY_POWER_ARCHITECTURE.md`
- reproducible source: `../tools/generate_hierarchical.py`

## Architecture

```text
USB-C 5 V fallback + protected J1 service input
  -> TPS2121 input mux
  -> BQ25798 2S buck-boost charger/NVDC power-path

2S cells
  -> BQ28Z610 gauge/protection/balancing
  -> external CHG/DSG FETs + Kelvin shunt
  -> BQ25798 BAT

BQ25798 SYS -> VSYS_RAW -> F3 MF-MSMF250/16X-2 -> VSYS_PROT
  +-> TPS62132 -> +3V3_D
  +-> TPS54302 -> +5V_PREISO
       +-> separate ADS filter -> RS3E -> clean ADS rails
       +-> separate INA filter -> RS3 dual -> INA +/-5 V
```

No 2S-to-9 V stage is used. `DGND` and `GND_ISO` remain galvanically separate. `BAT_NEG_RAW` differs from `DGND` only across the battery-current shunt and must use Kelvin sensing.

## Floorplan constraints

- Zone A, dirty edge: USB-C, J1, TPS2121, BQ25798, battery connector, BQ28Z610, protection FETs, shunt and charger inductor.
- Zone B: TPS62132, TPS54302, digital output/control.
- Zone C: RS3E/RS3 modules and explicit isolation keepout.
- Zone D, opposite clean edge: secondary filters, ADM7150, TPS7A20, isolated connectors/test points.
- Keep charger SW1/SW2/L3 loop local. Do not route it under or toward the clean secondary zone.
- Do not cluster the charger, TPS62132, TPS54302 and RECOM magnetics; vary orientation and spacing after mechanical review.
- Use one controlled DGND plane rather than arbitrary split islands. Keep high-current and sense returns local, with Kelvin shunt and quiet cell/NTC traces.
- Use four copper layers: L1 critical loops/components, L2 primary DGND, L3
  power/quiet routing and L4 clean/secondary routing. The full-height 3.0 mm
  isolation rule area blocks pads, vias, tracks and pours on every copper layer.
- Rev.A protection parts are F1 `MF-R250-0-10`, F2 `MF-MSMF260/16X-2` and F3
  `MF-MSMF250/16X-2`. NTC_BMS and NTC_CHG are separate `103AT-2` probes.
- Four layers are recommended; no final stackup is approved yet.

The current PCB file contains the floorplan/keepout and a preliminary
component placement. It intentionally contains no routing or vias.
