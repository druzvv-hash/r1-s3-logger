# Review1 repair - work in progress, NOT FOR FABRICATION

Base cf7ea7c2a540037fdbbc916575e068ce5bee85fc is retained in history.
Branch: fix/r3-powerbox-reva-review1. Main and A-F history are untouched.
Evidence: IMPLEMENTED / HOST CHECKED only, no physical acceptance.

## Confirmed defects and first ECO

- Custom DIODE pin numbering corrected in all three source libraries: K=1,
  A=2. D1/D2/D3 physical packages rotated 180 degrees and pad nets corrected;
  this preserves the existing rail/return copper at the physical locations.
- U2 EN disconnected, explicitly NC: TPS54302 Rev.C permits floating EN;
  its 7V absolute maximum cannot tolerate the former 2S/VSYS connection.
- R106=1k inserted between USB_VBUS_PROT and U10 VBUS_VS_DISCH. At 12.6V,
  upper-bound discharge current is 12.6mA, below ST's 50mA internal-path limit.
  This is a sensing/discharge branch, never a series system-load resistor.
- C71=4.7uF, C106=1uF: combined upper nominal/tolerance bound 6.84uF at
  +20%, excluding small parasitics. Bulk behind TPS2121 is retained. Actual
  attach/inrush/discharge compliance remains a bench gate; a downstream mux
  is not automatically proof that all downstream capacitance is invisible.
- C89 explicitly 1nF/50V C0G; 2S / 1.5MHz / 1uH retained.
- R96/R97=4.7k. With tr=0.8473*R*C: at 200pF tr=796ns. Use 100kHz initially;
  400kHz requires total bus capacitance <=75pF for 300ns (less with tolerance).
- F2 selected Littelfuse 2920L260/33DR, 2.6A hold/5A trip at20C, 33V,
  2920 SMD. Datasheet rerating: 2.24A@40C, 2.02A@50C, 1.81A@60C,
  1.60A@70C. **2.25A is NOT qualified hot continuous operation.** Preserve
  2.25A as cool-source policy ceiling only; enclosure/F2 thermal validation
  and a lower hot operating envelope are mandatory. This PPTC is not an OVP.
- J7 USB4105-GF-A: GCT gold-flash, tape/reel, default0.95mm shell stake.
  Existing outward orientation is retained.
- FB1 BLM31KN121SN1L replaces the undersized600-ohm family with6A/9mOhm
  class1206. FB6/7 exact ordering suffix BLM31KN601SH1L selected; final
  manufacturer current/temperature confirmation remains on the BOM evidence list.

## Factory NVM hazard - mandatory assembly interlock

ST DS12499 Rev8 factory settings include15V/20V, not the R3 image.
An unprogrammed device must NEVER see a normal PD source: D3 is a13V TVS,
and the mux/other input parts are not designed for a20V operating contract.
Use a verified **5V-only non-PD source**, current limited, for first programming.
Read back all NVM sectors, power-cycle on5V-only, verify5/9/12V PDOs and status
configuration, then and only then permit a PD source. Replacements/rework
repeat this interlock. A board warning is included.

Rev.B may add a qualified VBUS_EN_SNK-controlled input switch. A switch alone
does NOT reject an unwanted factory20V contract: its turn-on qualification
must include approved voltage/window logic, and a connector-side13V TVS would
still avalanche at20V. Do not describe a generic enable switch as a complete fix.

## Charger / passive routing checkpoint (2026-10-03)

Local PCB corrections now have 0 DRC errors, 0 unconnected and 0 schematic
parity findings (41 library-copy warnings, not yet individually re-qualified).
This is an intermediate checkpoint, not final acceptance.

L3 moved from (51,41) to (51,42); the enlarged local bypass/courtyard geometry
limits further movement without another component-placement redesign. C77 and
C81 now sit horizontally beside C80/C86, with explicit short local power
connections and paired ground vias. C100 moved to (47.5,49.4). C87 moved to
(57.2,50.7); its returns no longer use stretched old fanouts. SW under-package
links widened from 0.35 to 0.70mm; PMID/SYS flare from package escape to 0.40mm.
SW1 inner route avoids the relocated STAT via. TI Rev.C Fig8-21 expressly uses
inner-layer SW fanout so same-layer PMID/SYS capacitors can remain closest.
This is a documented exception to the review's blanket top-layer preference,
not a claim that the hot loops are fully optimized or physically validated.

The first over-packed trial failed DRC (shorts and courtyard overlaps). Only
that trial's named charger nets/placements were locally recovered; no board
reset, no rerun of A-F and no changes to main. Follow-up local routes replaced
the stretched capacitor fanouts. The authoritative PCB is the committed board;
the review1_* one-shot scripts are an engineering change log, not a replay chain.

The USB F2 2920 footprint and R106 fit on B.Cu. Allow at least the F2 maximum
1.8mm component height under the board, plus enclosure/assembly clearance.
C23/C24/C40/C41/C42 are 1210 GRM32ER71E226KE15L, not the originally suggested
1206: do not substitute package/MPN on nominal capacitance alone. Their exact
bias/temperature/aging acceptance remains open pending manufacturer curves.
INA FB4/FB5 are configurable 1206 positions; R107/R108 are DNP 2512 preload
positions. No preload value or filter inductance is fixed without measurements.
The previous +3V3_D 0.2mm trunk segment is now 1.0mm.

## Not yet completed in this checkpoint

PCB local routing/DRC following the ECO, charger hot-loop rebuild, bulk/DC-bias
capacitor qualification, configurable INA filtering, semantic abs-max/current
checks, final derived files and parity/isolation/visual validation. Work DRC
findings are visible, not waived. Previous F acceptance is historical only and
does NOT certify this modified work-in-progress PCB.

## Primary evidence

- TI TPS54302 Rev.C: https://www.ti.com/lit/ds/symlink/tps54302.pdf
- ST DS12499 Rev8: https://www.st.com/resource/en/datasheet/stusb4500.pdf
- TI BQ25798 Rev.C: https://www.ti.com/lit/ds/symlink/bq25798.pdf
- Littelfuse2920L, February2025: https://www.littelfuse.com/~/media/electronics/datasheets/resettable_ptcs/littelfuse_ptc_2920l_datasheet.pdf.pdf
- GCT USB4105 drawing: https://gct.co/files/drawings/usb4105.pdf
- Murata component model list: https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-fb-s-2504.ashx?cvid=20250523010505000000&la=en-us

Do not use the independent review's3.9uH recommendation as an RS3 dual-output
reference circuit: its cited EMC context does not establish that application.
