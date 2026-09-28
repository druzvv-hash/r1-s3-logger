# Schematic regeneration

`generate_hierarchical.py` is the reproducible electrical source for the root
sheet and nine KiCad 10 child sheets. It requires Python and `skidl==2.3.0`.

Set `KICAD10_SYMBOL_DIR` to KiCad's `share/kicad/symbols` directory, run the
generator from the `R3_PowerBox` directory, and then open/save the result in
KiCad 10. Then run `tools/arrange_schematic.py` from the same Python environment.
It applies the reviewed, deterministic A4 layout without changing connectivity.
Regeneration replaces the generated schematic sheets, so always rerun the
arranger before review.

The generator also writes `logical_nets.json`. This is the authoritative
pin-to-net map used by the arranger, avoiding accidental reliance on labels that
may overlap in the initial automatic drawing.

The project-local symbol source is `libraries/R3_POWER.lib`; the native KiCad
library used by the editor is `libraries/R3_POWER.kicad_sym`.
