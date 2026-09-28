# R3 PowerBox preliminary placement

Status: final pre-routing placement checkpoint; **no tracks or production
copper pours are present**.

## Board and zones

Rev.A remains 160 x 80 mm and four-layer. Placement follows the approved
left-to-right order:

1. DIRTY: USB-C, service input, TPS2121, BQ25798, battery connector,
   BQ28Z610, Q2/Q3 and the Kelvin shunt.
2. PRIMARY: TPS62132, TPS54302, digital/control connectors and primary test
   points.
3. ISOLATION: RS3E-0505S/H3 and RS3-0505D/H3.
4. CLEAN: ADM7150, TPS7A20, isolated filtering, isolated test points and J3.

U3 and U6 are oriented with pins 1/2/3 toward PRIMARY and pins 5/6/7/8 toward
CLEAN. Their pad-3 to pad-5 center gap is 5.08 mm. With 2.0 mm pads the board
edge-to-edge copper gap is 3.08 mm; this layout therefore adopts a **3.0 mm
minimum copper clearance and surface creepage corridor** from x=121 to
x=124 mm across the full board height. The rule area blocks pads, vias,
tracks and copper pours on L1, L2, L3 and L4. It is a low-voltage functional
isolation decision, not a claim of mains/reinforced-insulation certification.

## Stackup intent

- L1: components, critical signals and the smallest switching loops.
- L2: primary DGND plane; it stops completely at the isolation corridor.
- L3: power distribution and quiet sensing; no copper crosses the corridor.
- L4: secondary/clean routing and GND_ISO copper; it also stops at the
  corridor.

No split islands are planned inside the primary domain. Return-current control
comes from compact placement and uninterrupted local reference copper.

## Critical placement

- BQ25798, L3, bootstrap capacitors, charger-local VBUS bank, PMID, SYS and
  BAT capacitors are grouped in Zone A. SW1/SW2 copper must remain local and
  must not extend under any adjacent block.
- STUSB4500, CC ESD and TP31/TP32 are adjacent to J7. CC test pads are inline
  access points, not permission for long routed stubs.
- BQ28Z610, the common-drain CSD17577Q3AT pair, VC filters, SRP/SRN filters and
  WSL2512 shunt form one battery-management group. SRP/SRN and VC1/VC2 remain
  Kelvin/quiet paths.
- L3 is rotated 90 degrees, L1 is 0 degrees and L2 is 90 degrees. U3/U6 retain
  the electrical left-to-right isolation orientation and are vertically
  separated. These choices avoid a single aligned magnetic row and keep all
  magnetics away from the clean-edge LDOs.
- C40-C44 surround U4 and C50/C51 flank U5. These parts are placement-locked
  for short stability/bypass connections during routing.
- J3 and J6 are vertical at the clean edge. J1/J7/J8 remain on the dirty edge,
  J2/J4 on the primary edge, and J10 on the primary/service edge. Courtyards
  do not overlap; the board-edge side of each right-angle connector is left
  free for its mating housing, latch and cable bend.

Primary and dirty test points remain left of the isolation corridor. TP7-TP14
form two dedicated isolated rows at the clean edge. Silkscreen explicitly says
`PRIMARY / DGND`, `ISOLATED / GND_ISO` and marks the isolation boundary.

## Thermal reservations

- Q2/Q3: at least 200 mm2 combined top-layer drain/source copper around the
  pair, with 4-6 x 0.30 mm finished thermal vias per FET into primary-domain
  spreading copper where the Kelvin path permits.
- BQ25798, TPS2121, TPS62132 and TPS54302: exposed-pad copper and thermal-via
  arrays per the respective manufacturer land/layout guidance.
- R93: symmetric 2512 copper with Kelvin taps taken inside the force-current
  pads; do not add thermal-via asymmetry that creates measurement error.
- ADM7150: local copper/EP vias only if the validated load makes its estimated
  dissipation require them.

No thermal copper or via crosses the isolation corridor.

## Connector mechanical gate

The footprints/courtyards are collision-free, but enclosure CAD and the exact
mating housings are still required before routing release. J3 and J10 are the
highest-risk interfaces because their latch access and cable bend direction
must be checked against the future enclosure.
