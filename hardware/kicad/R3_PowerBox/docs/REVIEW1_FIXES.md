# Review1 repair - CAD checkpoint, NOT FOR FABRICATION

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

## Final CAD checkpoint (2026-10-03)

IMPLEMENTED / HOST TESTED only. Schematic/PDF/BOM regenerated from SKiDL plus
the explicit arranger, never a baseline PCB generator. 203 footprints,
1747 track/via objects and 14 filled zones. No main merge or production output.
The final commit is the commit containing this record; consult Git for its SHA.

Additional verified electrical corrections:

- STUSB4500 VSYS now uses +3V3_D, C109=1 uF/10 V local bypass. ST DS12499
  section 2.2.4 explicitly pulls SCL/SDA down if both supplies are absent;
  grounding VSYS therefore broke the approved common I2C bus on battery-only
  operation. USB-side VDD/dead-battery negotiation is retained. Battery-only,
  system-OFF/USB-ON and detach bus behavior still need powered validation.
- ILIM R76/R77 is now 28.7k/10k, 0.1%, rather than 243k/100k. Nominal
  0.300 A at REGN=4.8 V; adverse REGN=5.2 V, resistor tolerance and 1.5 uA
  leakage estimate 0.446 A. This does not include unspecified ADC/low-current
  regulation errors. Confirmed limits stay 1.35/2.25/1.80/1.80 A. Full R3
  batteryless boot from unknown 5 V is NOT guaranteed. Firmware is policy,
  not implemented/deployed MCU code in this repository.
- U10 VSYS exposed a genuine ERC power-driver issue after passive L1.
  A power flag was added at the physical +3V3_D source; no IC pin type was
  weakened. The arranger explicitly places/connects that flag.

Routing evidence:

- USB power trunk >=1 mm except the edge/M3 channel: two actual parallel
  0.9 mm B/In2 tracks, tied by paired vias. Short connector/mux/QFN escapes
  are explicitly listed in the graph report, not hidden by nominal net classes.
- Charger VBUS/PACK_POS transitions now use pairs of 0.70/0.30 mm vias.
  SW1/SW2 use paired vias and 0.70 mm inner copper; PMID/SYS bulk routes flare
  to 0.8 mm after short package escapes. +3V3_D trunk is 1 mm.
- Extending the path audit through connector/FET/shunt feeds found a 0.50 mm
  F3-to-Q4 bridge. That single 1.74 mm segment is now 0.80 mm; Q4 topology and
  position unchanged. Battery positive/negative force, common-drain and PACK_POS
  paths also pass the configured geometry tests, not a 5 A thermal qualification.
- C20 10 uF now on B.Cu immediately behind the U2 VIN area, C21 100 nF
  on F.Cu at VIN, with explicit short power link. C20 ground reaches the
  primary plane through its local via; still inspect loop impedance on hardware.
- Native charger view reviewed against TI Rev.C Fig8-21: local C80/C86,
  nearby C77/C81 and C100/C87, local EP/return vias and inner SW fanout.
  L3 is closer but not claimed equivalent to the TI EVM or fully optimized.
  No measured switching overshoot, EMI or thermal acceptance exists.
- Exact baseline comparison preserves all J1/J2/J3/J4/J7-J13, H1-H6,
  U3/U6 geometry, board/zone outlines, shunt pickups and cell-sense copper.
  No selected I2C/CC/NTC/cell/Kelvin trace projects over SW track copper.
- D1/D2/D3 pad1-cathode orientations and outward-facing USB opening checked
  against actual pad/net coordinates and native plots. This is not an assembly
  inspection of real parts.

### Acceptance results and warning ledger

| Test | Result / evidence |
|---|---|
| DRC + schematic parity | 0 errors, 0 unconnected, 0 parity findings; `reports/review1_work_drc.json` |
| DRC warnings | 41 library-copy mismatches; each footprint UUID already present in F; not waived electrical errors |
| ERC | 0 errors, 423 warnings: 211 off-grid endpoint + 212 symbol-copy artifacts |
| ERC accounting | `review1_verification.json` records each warning; includes added symbols, remapped diode pin UUIDs and newly reported C101 generated-symbol artifact; not a claim all 423 existed verbatim in F |
| Exact bidirectional pin/net parity | 550 schematic nodes, 552 PCB pads including NC; `review1_net_parity.json` |
| Polarity / selected abs-max / widest copper paths | PASS; `review1_polarity.json`, `review1_abs_max.json`, `review1_current_paths.json` |
| Semantic negative controls | reversed D3, EN-to-VSYS and deliberately thinned 3V3 network all rejected |
| Isolation/mounting filled copper | zero intrusions; `review1_domain_audit.json`; separate mounting audit PASS |
| Isolation negative control | scratch track/via/pad produce all 3 expected forbidden-item findings |
| Mechanics / Kelvin / SW projection | `review1_verification.json`, `review1_projection.json` PASS |

The current-path check uses actual pad/track/via contacts, a widest-path search
and connected parallel vias on both layers. It excludes filled-zone shortcuts.
It tests selected source-to-load paths, not every branch, trace ampacity or
IPC-2152 thermal rise. Thinning just one redundant segment did not fail because
an alternate qualifying path existed; the negative control therefore thins the
whole tested rail. This is expected path behavior, not a global min-width test.

### Intentionally unresolved fabrication / bench gates

1. **Exact MLCC effective capacitance is NOT closed.** Selected 22 uF/25 V
   GRM32ER71E226KE15L fits the 1210 footprints. ADI Table2 requires >7 uF
   effective CIN/CREG/COUT over conditions, ESR 0.001-0.2 ohm. A nominal label
   is insufficient. For 10% tolerance, X7R -15% and an illustrative additional
   5% aging allowance, bias retention must exceed 43.8% to retain 7 uF.
   This is an acceptance threshold, NOT measured retention. Obtain a dated
   exact-MPN Murata SimSurfing curve/export at each actual VIN/VREG/VOUT and
   5 V U2 output condition, then qualify tolerance/temperature/aging. Official
   spec/model lists confirmed nominal/package; curve endpoints returned errors
   in this session. Distributor estimates were not substituted as authority.
   U2 transient/loop behavior with two biased caps also remains unmeasured.
2. F2 thermal/current envelope and board copper/via temperature rise. 2.25 A
   is a cool maximum only; hot continuous use is not approved. Confirm FB6/7
   manufacturer temperature-current table for the exact SH1 suffix before purchase.
3. First-power 5 V-only programming/readback, validated 5/9/12 V contracts,
   detach/status behavior, mux inrush and source-current limits. POWER_OK3
   alone is not live attach proof. Unprogrammed boards are not safe on arbitrary PD.
4. RS3 light load/rail balance/ripple: FB4/FB5 0R/FB/L options and R107/R108
   DNP preload are deliberate tuning positions. No inductance or preload is
   approved before spectrum and INA851 shorted-input noise testing. No Y-cap
   was added and no intentional isolation crossing exists.
5. U2 6 V dropout/startup, ADM7150 noise/stability, charger full-load thermal
   and overshoot, 5 A battery/shunt/FET heating, NTC/protection recovery,
   BMS/gauge commissioning, enclosure/stack access and EMC remain bench gates.
   U11 remains only a DNP space reservation, NOT active secondary OV protection.

### Reproduction and negative knowledge

Use KiCad10 Python for PCB checks, Python/SKiDL for schematic generation.
Run `generate_hierarchical.py` then `arrange_schematic.py` once on fresh output;
export netlist, `sync_review1_metadata.py`, PDF/BOM/ERC, refill + DRC, audits.
Do not run historical A-F or `review1_*` mutation recipes on this board.
Mutation recipes now refuse ordinary execution: they record trial ECOs, not
an idempotent reconstruction pipeline. Current routed PCB is authoritative.

Failed local PD/C109 fits produced shorts/courtyard clashes and were rejected
by DRC; final alert routing uses a local In1 detour, retaining live PM bus.
KiCad requires attaching a new footprint to BOARD before Flip; the contrary
order crashed without saving. Exact parity caught the missing C109 afterward.
Zone fills must be invalidated before saving after net/footprint changes and
refilled before acceptance; stale fills previously reassigned a nearby via.
The PDF visual pass moved footer-conflicting labels/components on the drawing
only. No electrical error or unexpected new DRC warning was suppressed.

## Primary evidence

- TI TPS54302 Rev.C: https://www.ti.com/lit/ds/symlink/tps54302.pdf
- ST DS12499 Rev8: https://www.st.com/resource/en/datasheet/stusb4500.pdf
- TI BQ25798 Rev.C: https://www.ti.com/lit/ds/symlink/bq25798.pdf
- Littelfuse2920L, February2025: https://www.littelfuse.com/~/media/electronics/datasheets/resettable_ptcs/littelfuse_ptc_2920l_datasheet.pdf.pdf
- GCT USB4105 drawing: https://gct.co/files/drawings/usb4105.pdf
- Murata component model list: https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-fb-s-2504.ashx?cvid=20250523010505000000&la=en-us

Do not use the independent review's3.9uH recommendation as an RS3 dual-output
reference circuit: its cited EMC context does not establish that application.
