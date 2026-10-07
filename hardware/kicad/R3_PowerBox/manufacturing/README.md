# Manufacturing outputs

2026-10-07: owner authorizes a new RevA_PROTOTYPE_<source-sha> release from the
corrected board. Its manifest is authoritative; J7 is manually aligned/reviewed
in JLC, C1 is MANUAL_POPULATE / NOT DNP, and unresolved sourcing is not substituted.
Older RevA_prototype_logo and jlc_quote_0aeaea7 outputs remain obsolete.

**2026-10-07 HOLD:** the existing prototype Gerber ZIP and quote BOM/CPL files
predate the physical U4 pin-numbering repair. They are obsolete for fabrication
and assembly. Do not upload/order them. See
[orientation audit](../docs/JLC_ORIENTATION_FINAL_AUDIT.md) for the corrected PCB,
missing supplier acceptance and same-revision regeneration gates.

Put reviewed release artifacts here: Gerbers, drill files, position files, BOM,
assembly drawings, and a release checksum manifest.

Do not manufacture from this directory until ERC and DRC are clean, footprints
are verified against purchased parts, and a release revision is recorded.
