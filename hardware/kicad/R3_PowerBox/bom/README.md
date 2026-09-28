# Bill of materials

- `R3_power_kicad_bom.csv` is generated directly from the current KiCad
  schematic and is the sole reference for schematic quantities, values,
  footprints and designators.
- Sourcing status, package checks and unresolved selections are maintained in
  `../R3_POWER_REVIEW.md` so they cannot drift from the design review.

Regenerate the KiCad BOM after every schematic change. It is not an approved
purchasing list until all exact manufacturer part numbers and package variants
listed in the power review have been closed.
