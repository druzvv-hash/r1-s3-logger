# Bill of materials

Review1 (2026-10-03): schematic BOM fixes exact J7=USB4105-GF-A,
F2=2920L260/33DR, FB1=BLM31KN121SN1L, FB6/7=BLM31KN601SH1L,
C23/C24/C40/C41/C42=GRM32ER71E226KE15L (1210, not 1206), and R76/R77
28.7k/10k 0.1%. The capacitor MPN is a selected implementation candidate,
NOT a completed DC-bias qualification. No purchasing approval.
R107/R108 preload and INA FB4/FB5 population remain bench-selectable.

- `R3_power_kicad_bom.csv` is generated directly from the current KiCad
  schematic and is the sole reference for schematic quantities, values,
  footprints and designators.
- `R3_power_harness_bom.csv` records the two off-board SEMITEC 103AT-2
  temperature probes plus the optional DNP stacking-mate/standoff selections
  that cannot be fully represented by populated PowerBox footprints.
- Sourcing status, package checks and unresolved selections are maintained in
  `../R3_POWER_REVIEW.md` so they cannot drift from the design review.

Regenerate the KiCad BOM after every schematic change. It is not an approved
purchasing list until all exact manufacturer part numbers and package variants
listed in the power review have been closed.
