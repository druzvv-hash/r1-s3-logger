# R3 PowerBox board-to-board and mounting interface

Status: **mounting/B2B reference preserved through F prototype routing**.

Review1 (2026-10-03) independently confirms unchanged J12/J13 and all six
mounting coordinates against cf7ea7c. 15 mm stack baseline remains. New F2
2920L260/33DR is on B.Cu, maximum body height 1.8 mm: allow additional bottom
enclosure/assembly clearance, not only the upper-board standoff distance.
Pinouts are unchanged; follow the updated ST first-power programming procedure
before using a PD source. See [Review1](REVIEW1_FIXES.md).

`reports/routing_invariants.json` verifies J12/J13, all six mounting holes,
board outline and future-R3 envelope against the approved baseline. Their
coordinates/pinouts below are unchanged. J7 has a documented outward-facing
correction: (23.675,33), 270 degrees. SW2 is (85,78). C74/C75 and several local
filters are underneath; reserve underside service/standoff clearance.
15 mm stack baseline and connector access envelopes remain unchanged.
Mechanical mating and enclosure acceptance still require real parts/CAD;
the prototype routing is not a released enclosure drawing. See `ROUTING_F.md`.

## Coordinate system

All dimensions below are millimetres in the KiCad PCB coordinate system. The
PowerBox outline is x=20.0...180.0, y=20.0...100.0 (160 x 80 mm). Coordinates
refer to the KiCad footprint origin/pin-1 origin, not the footprint centroid.
The proposed future-R3 reference envelope is drawn on `Dwgs.User` from
(22.0,22.0) to (178.0,98.0). It is intentionally not on `Edge.Cuts` and is not
a final upper-board outline.

## M3 mounting pattern

All six holes use the project-local
`MountingHole_M3_NPTH_3.2mm_Keepout8mm` footprint: 3.20 mm NPTH, unplated,
unnumbered and electrically floating. Each footprint carries an 8.0 x 8.0 mm
keepout on F.Cu, In1.Cu, In2.Cu and B.Cu plus an 8.0 mm courtyard. Tracks,
vias, pads and copper pours are prohibited in that square. The courtyard is the
minimum screw-head/washer/standoff component clearance; enlarge it in the final
enclosure if the selected hardware exceeds 8 mm diameter.

| Hole | X | Y | Note |
|---|---:|---:|---|
| H1 | 35.0 | 25.5 | moved inward for USB-C plug/shell access |
| H2 | 174.5 | 25.5 | upper-right corner |
| H3 | 25.5 | 94.5 | lower-left corner |
| H4 | 174.5 | 94.5 | lower-right corner |
| H5 | 115.0 | 25.5 | upper long edge, primary side |
| H6 | 135.0 | 94.5 | lower long edge, isolated side |

H1-H4 are the preferred reusable four-hole upper-board pattern. H5/H6 add
PowerBox stiffness; their asymmetric x coordinates avoid J10/J11 and the
x=121...124 mm isolation corridor. No hole or 8 mm keepout enters the corridor.
Use insulating standoffs for the prototype. Metal hardware remains floating;
do not use a mounting hole as DGND, GND_ISO or chassis bonding.

## J12 PRIMARY B2B

Footprint origin/pin 1: **(106.0,28.0)**. Footprint:
`PinHeader_2x08_P2.54mm_Vertical`, generic 2x8, 2.54 mm pitch, THT, DNP in
Rev.A. Odd/even pins are paired by row.

| Pin | Signal | Pin | Signal |
|---:|---|---:|---|
| 1 | +3V3_D | 2 | +3V3_D |
| 3 | DGND | 4 | DGND |
| 5 | PM_I2C_SCL | 6 | PM_I2C_SDA |
| 7 | PG_3V3_D | 8 | CHARGE_STATUS |
| 9 | CHARGER_INT_FAULT | 10 | INPUT_SOURCE_STATUS |
| 11 | PD_ALERT_N | 12 | PD_CONTRACT_12V_N |
| 13 | POWER_CTRL | 14 | QON_SERVICE |
| 15 | SPARE / NC | 16 | SPARE / NC |

Pins 1/2 and 3/4 intentionally share current and reduce connector/return
impedance. `POWER_CTRL` is a maintained contact to DGND only. `QON_SERVICE` is
a momentary contact to DGND only. J12 contains no GND_ISO.

## J13 ISOLATED B2B

Footprint origin/pin 1: **(154.0,24.0)**. Footprint:
`PinHeader_2x05_P2.54mm_Vertical`, generic 2x5, 2.54 mm pitch, THT, DNP in
Rev.A.

| Pin | Signal | Pin | Signal |
|---:|---|---:|---|
| 1 | +5V_ISO_RAW | 2 | GND_ISO |
| 3 | +3V3_A_ISO | 4 | GND_ISO |
| 5 | +3V3_D_ISO | 6 | GND_ISO |
| 7 | +5V_INA | 8 | GND_ISO |
| 9 | -5V_INA | 10 | GND_ISO |

Every even pin is the same GND_ISO network and gives its adjacent rail a short
return. J13 contains no DGND. J12 and J13 are on opposite sides of the
functional-isolation barrier; no trace, plane, via, pad or mounting hardware may
bridge the x=121...124 mm corridor.

## Header/socket combinations and stack height

The land patterns accept ordinary straight male headers, female sockets and
long-post stacking headers. A right-angle part is mechanically possible on the
same 2.54 mm grid but must be checked against the upper board and adjacent
parts. Do not select a shrouded body larger than the plotted courtyard without
rerunning the mechanical check.

- **15 mm recommended:** 15 mm M3 standoffs, a 2xN long-post/stacking male on
  one PCB and a low-profile 2xN female socket on the other. Select post length
  for at least 2.5-3.0 mm contact engagement after both PCB thicknesses and the
  socket-body height are included. This gives about 13 mm practical under-board
  component allowance after reserving about 2 mm for tolerance/solder leads.
- **12 mm conditional:** 12 mm standoffs with a low-profile female socket and
  appropriately shortened stacking post. Practical allowance is about 10 mm.
  It is not acceptable over U3/U6 without an upper-board cutout/keepout because
  the RECOM modules are 11.1 mm high.

Freeze an exact header/socket manufacturer series only after the future R3 PCB
thickness, standoff tolerance and enclosure height are known. The DNP Rev.A
default preserves cable-only assembly.

## Component-height and upper-board keepout

| Item | Height / constraint | Stack result |
|---|---|---|
| U3 RS3E-0505S/H3 | 11.1 mm manufacturer height | fails the practical 12 mm allowance; fits nominal 15 mm with about 3.9 mm geometric clearance |
| U6 RS3-0505D/H3 | 11.1 mm manufacturer height | same as U3 |
| C1 CP_Elec_6.3x5.8 | 5.8 mm body | fits 12/15 mm |
| L3 SRP7028A class | 2.8 mm class | fits 12/15 mm |
| L1 XFL4020 | about 2.1 mm class | fits 12/15 mm |
| L2 SRP5030T class | about 3.0 mm class | fits 12/15 mm |
| Micro-Fit right-angle headers | edge-entry; housing/latch/cable envelope dominates | keep upper-board edge and enclosure out of mating/latch corridor |
| test points | bare plated-hole footprint; probe hardware not fixed | use low-profile pads under overlap; tall posts require upper-board keepout |
| SW1/SW2 | local low-profile controls | provide finger/tool cutout if the upper board overlaps them |

For a 12 mm stack, the upper board must exclude/cut out the U3/U6 projected
areas. For 15 mm, retain at least 1.5-2.0 mm tolerance above every fitted item;
the nominal 3.9 mm margin over U3/U6 satisfies that target. STEP/enclosure CAD
remains required before production release.

## Cable and stacked assembly

- **Cable mode:** populate the existing Micro-Fit/JST connectors; leave J12 and
  J13 DNP.
- **Stacked mode:** populate J12/J13 with the selected header/socket pair.
  Existing cable connectors remain electrically parallel and may remain fitted.
- J1/J7/J8 exit the DIRTY edge; J2/J4/J9 exit the upper primary edge; J3/J6
  exit the CLEAN edge; J10/J11 exit the lower primary edge. Their side-entry
  mating direction remains unobstructed by the reference upper PCB, but the
  final upper-board/enclosure outline needs local edge notches or setbacks for
  latch release and cable bend radius.
- J3, J10 and J11 remain the highest-risk access interfaces. Validate the exact
  43645 mating housings, wire gauge, latch tool/finger access and bend radius in
  assembly CAD before routing release.

## Isolation restrictions

The 3.0 mm corridor x=121...124 mm is an all-layer functional-isolation rule
area. L1/L2/L3/L4 copper, zones, tracks, vias and pads are forbidden. The future
R3 PCB must implement its own corresponding barrier and must not reconnect
DGND to GND_ISO through headers, mounting hardware, shields, test equipment or
mechanical metalwork. This is low-voltage functional isolation, not a claim of
mains/basic/reinforced safety certification.
