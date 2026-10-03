# Logo, fabrication export and 3D viewing

2026-10-03 — IMPLEMENTED / HOST TESTED, not bench accepted.

Owner authorized prototype Gerber export. The supplied raster logo was manually
interpreted as monochrome native F.SilkS artwork, center (162.5,45.0) mm,
approximately 12.3 mm envelope. Text height 0.8 mm; graphic strokes 0.15 mm,
text strokes 0.13 mm. Metallic texture/color intentionally omitted.
`tools/add_board_logo.py` replaces only its own named graphic group.
It does not regenerate the PCB or modify the approved schematic.

`reports/branding_invariants.json` proves every pre-existing board record is
unchanged from 5d3da52; only 96 silk/group records added. Pads, routes, zones,
mounting, outline, isolation and footprint positions are exactly preserved.
`reports/branding_drc.json`: 0 errors, 0 unconnected, 0 parity issues;
41 existing library-copy warnings. Initial logo overlapped the J13 legend;
moved down 2 mm and text enlarged to eliminate all new warnings.

Gerber/drill output and README: `manufacturing/RevA_prototype_logo/`.
Archive: `manufacturing/R3_PowerBox_RevA_PROTOTYPE_Gerbers.zip`.
SHA256 manifest covers the archive's individual files. This export does not
close Review1 component/thermal/PD qualification gates or authorize an order.

## Rotate the board

Open R3_power.kicad_pcb in KiCad PCB Editor, then View > 3D Viewer (Alt+3).
Drag with the left mouse button to rotate; use the wheel to zoom.
An exported rotatable GLB is `reports/R3_PowerBox_RevA.glb`.
Preview is `reports/R3_PowerBox_logo_3D.png`.

The GLB omits DNP parts and contains only available component models.
Missing library models include Micro-Fit connectors, some power ICs, L3 and
PPTCs; U3/U6 also have no complete modeled bodies in this preview.
Do NOT use empty-looking areas as proof of assembly or upper-board clearance.
The native PCB footprints and mechanical clearance documentation remain the
authority. No invented substitute models were used to hide missing parts.

Schematic/PDF/BOM unchanged: this is graphics-only, with no new electrical part.
