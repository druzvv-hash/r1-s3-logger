# Schematic regeneration

## Routed F preservation

The active PCB is routed. Do not invoke placement or A-E routing recipes on it.
`finalize_routing.py` is incremental silk/redundancy cleanup; the separate
`fix_bootstrap_projection.py` records the audited F local C75 repair.
`verify_final_routing.py` compares current copper/placement to the preserved E
commit and checks the explicit exceptions, Kelvin pickups and SW projections.
`sync_routed_metadata.py` consumes a freshly exported `tmp/F_netlist.xml`, checks
pin/net parity and updates identifiers/fields only, never footprint geometry.
Do not bulk-update edited embedded footprints from stock libraries.

Run the schematic generator before its arranger: the arranger expects fresh
SKiDL blocks, not an already normalized KiCad save. It also serializes the
approved DNP flags that SKiDL 2.3 otherwise omits. This does not route/regenerate
the PCB. Do not use schematic regeneration as a substitute for routing.

`generate_hierarchical.py` is the reproducible electrical source for the root
sheet and ten KiCad 10 child sheets. It requires Python and `skidl==2.3.0`.

Set `KICAD10_SYMBOL_DIR` to KiCad's `share/kicad/symbols` directory, run the
generator from the `R3_PowerBox` directory, and then open/save the result in
KiCad 10. Then run `tools/arrange_schematic.py` from the same Python environment.
It applies the reviewed, deterministic sheet layout without changing connectivity.
Regeneration replaces the generated schematic sheets, so always rerun the
arranger before review.

The arranger also fixes the dense battery/BMS sheet to A3 and the
charger/power-path sheet to A2. This prevents SKiDL's automatic paper-size
selection from clipping or crowding those two sheets on regeneration.

The generator also writes `logical_nets.json`. This is the authoritative
pin-to-net map used by the arranger, avoiding accidental reliance on labels that
may overlap in the initial automatic drawing.

The project-local symbol source is `libraries/R3_POWER.lib`; the native KiCad
library used by the editor is `libraries/R3_POWER.kicad_sym`.

`generate_preliminary_placement.py` is a separate, explicitly unrouted PCB
placement generator. Run it with KiCad 10's bundled Python after schematic
regeneration. It exports a temporary XML netlist, reloads the assigned
footprints, assigns nets and packs them into the documented four zones while
preserving the outline and isolation keepout. It never creates tracks or vias.

The placement generator also adds the six project-local M3 NPTH footprints,
their four-layer keepouts and the `Dwgs.User` future-R3 envelope. These are
mechanical PCB objects and intentionally do not appear in the schematic BOM.

`generate_mechanical_views.py` regenerates the annotated zone/isolation,
stack-top and stack-side PNG references (plus the annotated-zone PDF) from the
dimensioned coordinates used by this pass.
