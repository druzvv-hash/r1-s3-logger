# Schematic regeneration

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
