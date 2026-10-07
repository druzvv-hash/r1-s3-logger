# JLC orientation audit — R3 PowerBox Rev.A

Date: 2026-10-07. Evidence: HOST TESTED, not assembled/bench tested.
Base: `0aeaea77a38e7b103af06dd491d3ec8ec9fd85f6`, branch
`fix/r3-powerbox-reva-review1`; corrections are local working-tree changes.

## Release status: BLOCKED, audit not fully closed

The U4 physical numbering defect is corrected in both the project footprint and
PCB, with a bounded local reroute. Critical CAD pin/net/order checks pass.
This is **not** a completed JLC assembly-orientation acceptance or production
release. The accepted JLC BOM/LCSC export and supplier placement models are not
available locally. In particular C1 exact MPN and J7 selected supplier part /
centroid remain unknown. No guessed JLC rotations/offsets were applied.

Do not upload the old prototype ZIP or the quote files under
`manufacturing/jlc_quote_0aeaea7`: they predate the U4 correction.
No replacement manufacturing ZIP/BOM/CPL is released until the missing gates
below pass. No order, substitution, remote push or main-branch modification.

## Critical component chain

Angles below are **native KiCad** degrees, not supplier-library rotation
corrections. All listed critical component origins and angles are unchanged.
`CAD` means checked physical order, symbol function where applicable, PCB net,
and native position-file parity. It does not certify the selected JLC part.

| Ref | MPN/design identity | Datasheet pin 1 / polarity | PCB pad 1 | Net verification | Original rotation | Final rotation | Position changed? | Routing changed? | Result |
|---|---|---|---|---|---:|---:|---|---|---|
| U1 | TPS62132RGTR | SW; counterclockwise RGT top view | SW | SW pins 1–3; FB/AGND to DGND; EP DGND | 180 | 180 | No | No | CAD PASS |
| U2 | TPS54302DDCR | GND, DDC | GND | SW/VIN/FB/EN/BOOT checked; EN remains intentional NC | 180 | 180 | No | No | CAD PASS |
| U4 | ADM7150ACPZ-3.3-R7 | VREG, upper left | VREG at corrected upper left | 1 N$13; 2 +3V3_A_ISO; 3 N$14; 4/9 GND_ISO; 5/6 ADM7150_REF; 7 EN; 8 +5V_ISO_A | 0 | 0 | No | **Yes, local** | Corrected; CAD PASS |
| U5 | TPS7A2033PDBVR | IN, DBV | IN | IN/EN +5V_ISO_D; OUT +3V3_D_ISO; NC4 | 0 | 0 | No | No | CAD PASS |
| U7 | TPS2121RUXR | OUT; manufacturer bottom-view transformed to top | OUT | IN1 USB; IN2 service; OUT CHARGER_IN | 0 | 0 | No | No | CAD PASS |
| U8 | BQ25798RQMR; source abbreviated BQ25798RQM | STAT | BQ_STAT_RAW | All 29 pins checked, including nonuniform power lands | 0 | 0 | No | No | CAD PASS; supplier ordering suffix reconciliation pending |
| U9 | BQ28Z610DRZR | VSS | BAT_NEG_RAW | VC2/VC1, SRP/SRN, CHG/DSG and EP checked | 0 | 0 | No | No | CAD PASS |
| U10 | STUSB4500QTR | CC1DB | USB_CC1 | CC pairs, RESET ground, VDD/VSYS, status and EP checked | 0 | 0 | No | No | CAD PASS |
| Q1 | DMP3007LSS-13 source; **AO4407A owner-selected JLC** | Physical 1–3 S, 4 G, 5–8 D | Logical 1 = physical 4, G | S SERVICE_IN_REV; G Q1_GATE; D SERVICE_IN_FUSED | 0 | 0 | No | No | Physical compatibility PASS; sourcing record pending |
| Q2 | CSD17577Q3AT | Physical 1–3 S, 4 G, 5–8/EP D | Logical 1 = G | S PACK_POS; G BMS_DSG_GATE; D BMS_FET_COMMON | 0 | 0 | No | No | CAD PASS |
| Q3 | CSD17577Q3AT | Same as Q2 | Logical 1 = G | S BAT_POS_RAW; G BMS_CHG_GATE; D BMS_FET_COMMON | 180 | 180 | No | No | CAD PASS; common drain preserved |
| Q4 | DMP3007LSS-13 source; **AO4407A owner-selected JLC** | Physical 1–3 S, 4 G, 5–8 D | Logical 1 = physical 4, G | S VSYS_PROT; G SYS_LOAD_GATE; D VSYS_MAIN | 0 | 0 | No | No | Physical compatibility PASS; sourcing record pending |
| D1 | SMBJ13A, exact manufacturer pending | Cathode band | K | K SERVICE_IN_REV; A DGND | 180 | 180 | No | No | CAD polarity PASS; exact sourcing pending |
| D2 | BZT52C10 | Cathode band | K | K SERVICE_IN_REV; A Q1_GATE | 180 | 180 | No | No | CAD polarity PASS; exact sourcing pending |
| D3 | SMBJ13A, exact manufacturer pending | Cathode band | K | K USB_VBUS_PROT; A DGND | 180 | 180 | No | No | CAD polarity PASS; exact sourcing pending |
| D4 | ESDA25W | Three-terminal TVS, not generic two-pad diode | USB_CC1 | 1 CC1; 2 CC2; 3 DGND | 180 Bottom | 180 Bottom | No | No | Net contract PASS; full manufacturer graphical/supplier orientation review still open |
| D5 | CHG LED, exact accepted part pending | Cathode | K | K BQ_STAT_RAW; A CHARGE_LED_A | 0 | 0 | No | No | CAD polarity PASS; supplier LED marking pending |
| D6 | RUN LED, exact accepted part pending | Cathode | K | K DGND; A RUN_LED_A | 0 | 0 | No | No | CAD polarity PASS; supplier LED marking pending |
| D7 | BAT54WS | Cathode band | K | K BQ_STAT_RAW; A CHARGE_STATUS | 0 | 0 | No | No | CAD polarity PASS; supplier identity pending |
| C1 | 47uF/25V low-ESR, exact MPN missing | Positive terminal | + | 1 SERVICE_IN_REV; 2 DGND | 0 | 0 | No | No | CAD polarity PASS; component-level gate BLOCKED |
| J7 | GCT USB4105-GF-A design | A/B contacts per GCT top-view drawing | Alphanumeric, not generic pin1 | All 16 contacts + shell checked; CC1 A5 / CC2 B5 | -90 | -90 | No | No | GCT CAD PASS; JLC centroid/selected model BLOCKED |

## Actual error and local ECO

The old U4 footprint mirrored the lead numbers vertically. New canonical local
coordinates (mm): left 1/2/3/4 at x=-1.35, y=-0.75/-0.25/+0.25/+0.75;
right 5/6/7/8 at x=+1.35, y=+0.75/+0.25/-0.25/-0.75. EP9 remains GND_ISO.
Symbol and net meanings were correct and were not changed. U4 stays (145,42), 0°.
REF and REF_SENSE remain tied at the local REF capacitor, per ADI application.

| Ref | Original XY mm | New XY mm | Native angle old → new |
|---|---|---|---|
| C40 VIN | 149.5,45.2 | 149.5,38.8 | 0 → 0 |
| C41 VREG | 140.5,45.2 | 140.5,38.8 | 180 → 180 |
| C42 VOUT | 140,41 | 140,43 | 180 → 180 |
| C43 REF | 148.8,38.3 | 148.8,45.7 | 90 → -90 |
| C44 BYP | 142,37 | 142,47 | 90 → -90 |
| R40 EN (Bottom) | 148,47.5 | 148,36.5 | 0 → 0 |

The local bypass/enable copper was reflected with the group, then the 5 V input
feed detoured around thermal ground vias. Existing external input/output anchor
points were retained. The comparator reports 50 changed track/via UUID records,
all within the U4 region except the unchanged output-trunk endpoint at (140.8,30).
All 203 footprint pad/net identities remain identical to the baseline. All other
component anchors, board outline, four-layer architecture and BMS/Kelvin routes
remain unchanged. Filled isolation and mounting keepouts pass the domain audit.

## MOS physical versus logical numbering

For Q1/Q4, the custom schematic abstraction uses logical G=1, S=2, D=3.
The footprint repeats logical pad2 on physical SO-8 pins1–3, logical pad1 on
physical pin4, and logical pad3 on physical pins5–8. Physical pin1 is therefore
**not** logical pad1. At native 0°, physical1 is upper-left Source, Gate lower-left.
Both DMP3007LSS and AO4407A use this physical ordering. Do not rotate AO4407A to
put its physical pin1 on logical pad1. This establishes pin compatibility, not
blanket electrical/thermal equivalence of the two MOSFETs.

The owner-selected AO4407A is recorded here, not rejected or silently reverted.
The editable source still names DMP3007LSS-13; before final BOM release reconcile
the accepted sourcing export and document the assembly override explicitly.
Q2/Q3 retain the same logical abstraction with merged physical Drain/EP lands;
their physical 180° opposition preserves common-drain protection topology.

## J7 and CPL

Original GCT USB4105 drawing B4 (18/12/2023), component top view, agrees with the
footprint contact row y=-3.68 and shell stake coordinates x=±4.32,
y=-3.105/+1.075. Contact x positions are checked individually by the script.
Body 8.94 x 7.35 mm; original PCB center (23.675,33), -90° places its mating
edge at board x=20. No evidence supports shifting the physical PCB footprint.

The reported JLC viewer shift remains **cause unresolved** until the selected
JLC/LCSC connector and library reference point are supplied. A body-center origin
is not automatically the same as JLC's placement-model origin. Do not infer a
correction from the rendered body or 3D text. Locate matching physical contacts
in the supplier preview and record a justified translation/rotation if required.

`reports/orientation_positions_NATIVE_NOT_FOR_ASSEMBLY.csv` is a new diagnostic
export, not a JLC CPL. It contains 160 position-eligible footprints, including
items excluded from a factory assembly plan. Native axes are absolute X and
negative KiCad board Y. The verifier checks RefDes coverage, value, footprint,
side, XY and native rotation. No supplier offset or angle correction is guessed.
R107/R108 remain DNP; manual/user-owned exclusions remain mandatory.

## Marking / visual scope

Added U4 upper-left F.Silk dot and F.Fab chamfer; corrected project-library Q1/Q4
physical-pin1 marker and added clear external PCB dots; U1 external pin1 dot;
U9 F.Fab pin1 dot; explicit C1 positive legend. Repositioned selected references
Q1/Q4/D2/D7/C1/U8/U9/U10/J7 without moving components. Bottom visible silk fields
are mirrored. D1/D2/D3 cathode bars correspond to their positive/source nets;
D5/D6/D7 pad1 is cathode. C1 is the only electrolytic-style polarized capacitor
identified in the current PCB inventory.

Actual KiCad copper/fab/silk renders are `reports/orientation_*.png/.svg`.
Grey fab text can overlap pads by design; it is not manufacturing silkscreen.
Critical views inspected include U1/U2/U4/U5/U7/U8/U9, USB, MOSFETs, C1, diode
and LED groups and Bottom. This is not a claim that every hidden reference or
supplier component mark has been accepted. Remaining full-chain scope includes
manual RECOMs, connector mating/pin1 conventions and selected supplier LED/C1
markings. The existing zero minimum silk clearance rule does not establish a
manufacturer-specific nonzero silk-to-mask margin.

## Reproducible tests and limitations

- `tools/audit_physical_orientation.py --negative-controls`: 675 checks PASS;
  rejects U4 mirrored numbering, D3 reversed nets, Q4 gate/source swap and J7 CC
  swap in memory. Uses explicit independent pin/net and package-ID contracts;
  package-ID equality is not complete supplier-MPN qualification.
- `tools/verify_orientation_export.py`: native position parity and bounded ECO
  PASS; six bypass placements changed, all other anchors/pad nets preserved.
  The baseline may be read from Git into tmp; the working PCB is never reset.
- `tools/audit_routing.py --output reports/orientation_domain_audit.json`:
  filled copper, pad/track/via domain separation and six mounting envelopes PASS.
- DRC with refill and schematic parity: zero electrical errors, zero unconnected,
  zero parity findings; **42 library-footprint-copy warnings remain**, not waived
  as proof of identical libraries. No new geometry or silkscreen findings.
- `tools/check_polarity.py`: current diode net/source polarity checks PASS.

The physical-audit script reads fresh KiCad XML at
`tmp/orientation/current_netlist.xml`; generate with `kicad-cli sch export netlist
--format kicadxml -o tmp/orientation/current_netlist.xml R3_power.kicad_sch`.
Run the tools with KiCad's Python. Generate the native CSV using `pcb export pos
--format csv --units mm --side both`; do not treat it as a factory assembly list.
One-shot correction recipes are historical ECO records, not a replacement for
the current routed PCB. Do not replay them on the corrected board.

## Release gates / files to re-upload after closing them

1. Obtain accepted JLC BOM/LCSC export, including AO4407A, C1 and J7. Preserve all
   owner-approved substitutions and all manual/DNP classifications.
2. Finish remaining oriented-part and manufacturer silk-margin audit; qualify
   every selected package against physical lands, not just footprint names.
3. Resolve J7 supplier centroid and all supplier zero-angle conventions; verify
   physical contacts and polarity in fresh Top/Bottom placement previews.
4. Regenerate **one same-revision set**: Gerber ZIP, PTH/NPTH drills, supplier BOM,
   factory-filtered CPL and checksum/revision manifest. Re-run all tests and
   explicitly compare CPL with PCB and the approved assembly plan.
5. Replace the old JLC Gerber, BOM and CPL together. Do not reuse manual viewer
   corrections blindly. Do not order from this audit state.

## Original manufacturer sources

- [ADI ADM7150, pin configuration and package](https://www.analog.com/media/en/technical-documentation/data-sheets/ADM7150.pdf)
- TI: [TPS62132](https://www.ti.com/lit/ds/symlink/tps62132.pdf), [TPS54302](https://www.ti.com/lit/ds/symlink/tps54302.pdf), [TPS7A20](https://www.ti.com/lit/ds/symlink/tps7a20.pdf), [TPS2121](https://www.ti.com/lit/ds/symlink/tps2121.pdf), [BQ25798](https://www.ti.com/lit/ds/symlink/bq25798.pdf), [BQ28Z610](https://www.ti.com/lit/ds/symlink/bq28z610.pdf), [CSD17577Q3A](https://www.ti.com/lit/ds/symlink/csd17577q3a.pdf).
- [STUSB4500](https://www.st.com/resource/en/datasheet/stusb4500.pdf), [ESDAxxxWx](https://www.st.com/resource/en/datasheet/esdaxxxwx.pdf).
- [AO4407A](https://www.aosmd.com/res/datasheets/AO4407A.pdf), [DMP3007LSS](https://www.diodes.com/datasheet/download/DMP3007LSS.pdf), [BAT54WS](https://www.diodes.com/datasheet/download/BAT54WS.pdf).
- [GCT USB4105 mechanical drawing](https://gct.co/files/drawings/usb4105.pdf).
