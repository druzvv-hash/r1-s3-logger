## 2026-10-23 addendum — physical user checks performed 2026-10-22

**USER-REPORTED, preliminary; not full hardware acceptance.** After U10
programming the owner reported PD 12 V operation, SYS 7.594/7.327 V and outputs
3.3062/4.9965 V. Earlier isolated readings were +5.037/-5.037 V; their chronology
must not be relabelled as a repeat under PD 12 V. Earlier TP5 static 5.0 V and
later with/without-100-ohm-resistor scope observations are recorded separately;
numeric load/ripple values are unavailable in the retrieved text, not invented.
Converter/capacitor interference and difficult ground-contact soldering are
reported physical issues. Load/thermal, power control, charger/BMS, isolation
and mechanical acceptance remain open; U11/C1 explanations remain unverified.
See [dated evidence and limitations](docs/POWERBOX_REVA_USER_CHECKS_2026-10-22.md).
This supersedes any reading of the older audit as saying no physical 12-V
operation was ever reported; its machine-captured 5-V test scope stays unchanged.

## External project memory audit - 2026-10-23

Current handoff: **R3 PowerBox Rev.A / Rev.B candidate**; branch `fix/r3-powerbox-reva-review1`; version **Rev.A frozen + local Rev.B candidate**.
PowerBox has progressed beyond the September pre-routing baseline. Rev.A
prototype source 0d6da576168b8284664dffa865b99ebe71e1d3c4 / release commit
9ad492a7febef3f72f6920bc6350b5c1a50d6bda remains the frozen reference.
The Oct 8 package audit reported a U9 DRZ land mismatch on that frozen source;
its assembly HOLD recommendation superseded the earlier bounded CAM approval.
The separate RevB_PACKAGE_FIX_2026-10-08 candidate was consolidated under
hardware/kicad/R3_PowerBox/manufacturing/ on Oct 9. Its existing report records
DRC 0 errors / 0 unconnected / 0 parity, 39 warnings; ERC 0 errors / 423 warnings.
These are historical HOST CHECKED results, not new runs or factory approval.
RevB is local/untracked; do not reuse RevA CPL for its moved U9, promote it to
Rev.A, or change the paid order. J7 placement and thermal/assembly acceptance
remain unresolved in the retained reports.

Oct 22 private report REPORT-5V9V12V.uk.txt records physical U10 NVM write,
40/40 readback and 5V-only power-cycle/runtime reload for board R3-REVA-001.
Actual active sink profile: 5 V / 1 A, 9 V / 1.5 A, 12 V / 1.5 A; current CRC32
1AFF7140, factory CRC32 1B043764. This differs from older provisional design
currents 3 A / 2 A / 2 A. Candidate 12454B47 was superseded. Preserve the existing
U10 configuration; no repeat programming is needed. This evidence does NOT prove
a physical 9/12 V PD contract, charger/load, BMS or whole-board acceptance.
Oct 23 PD 1.2.0 tests were performed with U10 disconnected and did not rewrite it.


Open work: Existing manufacturing/CAD files remain dirty/untracked. This pass commits reviewed memory only; factory source, order status and physical charger/BMS acceptance require separate work.
Read [the current evidence map](docs/PROJECT_MEMORY.md) and
[dated work reports](WORK_REPORT.md). Older sections below are retained history;
the dated summary above supersedes conflicting status/version/deployment claims.

# Current memory entry point

## 2026-10-09 — RevB consolidated in manufacturing

Single editable location: hardware/kicad/R3_PowerBox/manufacturing/RevB_PACKAGE_FIX_2026-10-08/.
Moved71 files intact from revisions/; verified all hashes. Removed two byte-identical
task-output presentation copies; moved the delivery ZIP intact into delivery_snapshot/.
Root hardware README and manufacturing index point to the current project.
RevA and paid JLC order unchanged. No manufacturing acceptance or new circuit changes.

## 2026-10-08 — Separate RevB package correction candidate saved

Owner authorized fixes in a separate version and explicitly forbade JLC changes.
Project (current location): hardware/kicad/R3_PowerBox/manufacturing/RevB_PACKAGE_FIX_2026-10-08/.
U9 DRZ geometry/fanout fixed; U9 X+0.55mm. U1/U4 EP and Q2/Q3 paste corrected;
universal stencil v2 updated. DRC0 errors/0 unconnected/0 parity,39 library warnings;
ERC0 errors/423 baseline warnings. Original PCB hash unchanged. See revision README.
Regenerated Gerbers are local candidates only; native positions are NOT filtered CPL.
Future JLC upload requires revised140-reference BOM/CPL and placement verification.
No JLC/UI/order/payment actions. Old RevA U9 warning still applies to paid order.


## 2026-10-08 — U9 package rejection: source footprint FAIL, assembly HOLD

Supersedes earlier production-confirmation advice. Full140 factory-reference
screening found U9 DRZ0012A row centres2.70mm versus TI3.80mm and wrong EP.
BQ28Z610DRZR/C157573 identity is not the cause; same-package substitution cannot fix.
U4/U1 thermal lands WARN; Q2/Q3 PCB paste overlaps WARN; J7 placement still open.
Universal stencil B3 copies U9 error, A1/A3 need EP review. See
hardware/kicad/R3_PowerBox/docs/PACKAGE_FIT_AUDIT_2026-10-08.md for bounded evidence.
131 package-screening PASS/8 WARN/1 FAIL; no blanket physical acceptance.
PCB/release/order untouched; no message sent. Factory production state unresolved.


## 2026-10-08 — Paid JLC production files reviewed

Owner reported payment, then inner copper upgrade payment on Oct7. JLC production
metadata now confirms 1 oz outer AND inner / 4 layers / 1.6 mm. Final board160x80;
160x90 includes two5mm rails. Source archive12files matches frozen release.
Stencil431apertures/20patterns retained; factory boundary differences <0.002mm.
See hardware/kicad/R3_PowerBox/docs/JLC_PRODUCTION_REVIEW_2026-10-08.md for bounded
geometry checks, nonfunctional inner-pad removal and limitations. No blocking fab
mismatch found; PCBA J7 placement warning remains separate. No Confirm clicked.
This supersedes earlier local notes saying the order was only in cart/unpaid.


## 2026-10-07 — Universal IC stencil in JLC cart

New package: hardware/kicad/R3_PowerBox/manufacturing/Universal_IC_Stencil_2026-10-07/.
20 individual-IC patterns covering PowerBox and documented R1/R3/CANBox packages;
431 apertures, geometry screening PASS; module land-pattern fit remains unqualified.
Stencil-only U4 EP and CSD17577 drain aperture improvements; source PCB unchanged.
JLC cart: 1 frameless 200x200 mm / 0.10 mm electropolished, $12.19 before shipping,
exact 1:1 paste, production-file review enabled. No checkout/payment. See README,
inventory and order_status in the package; generic FRAM/EEPROM variants need fit check.


## 2026-10-07 — Live JLCONE Top/Bottom review

See hardware/kicad/R3_PowerBox/docs/JLC_LIVE_ORIENTATION_2026-10-07.md.
Critical IC/MOS/diode markers visually agree with RevA, including Bottom D4.
J7 faces correctly but model contacts appear offset left of PCB lands: WARN,
origin/model versus placement cause unresolved, no guessed translation applied.
No blanket 140-component acceptance; no placement edits or order submitted.

## 2026-10-07 — Assembly drafts saved in repository

Current manual-L1 BOM/CPL, manual/DNP CSV, HTML review and stock audit are in
hardware/kicad/R3_PowerBox/manufacturing/RevA_JLC_L1_MANUAL_2026-10-07/.
See that directory's README. Frozen release preserved; drafts are not order acceptance.

## 2026-10-07 — Owner authorized manual L1

Supersedes the L1 disposition HOLD below: user explicitly requested removal.
L1 is excluded from BOTH factory BOM and CPL, and added as MANUAL_POPULATE
to the delivered manual/DNP list. It is required, not DNP. Updated files contain
140 unique references, 90 Top/50 Bottom. All other values remain unchanged.
Sourcing/placement review warnings remain; no CAD/release edits or order.

## 2026-10-07 — JLC sourcing draft, order HOLD

Owner requested BOM/CPL using available JLC parts. Draft is for B Both, 141
positions (91 Top/50 Bottom), assuming the existing two-assembled-board plan.
See hardware/kicad/R3_PowerBox/docs/JLC_SOURCING_2026-10-07.md.
Public JLC catalog checks found sufficient orderable quantity for 140 positions;
L1 XFL4020-222MEC C122469 remains zero stock/orderable. Manual L1 disposition
was asked but has not been selected. Do not silently omit it from assembly.
L2, J7 and R78/R79 changes are proposals, not engineering acceptance. Native
CPL coordinates and rotations preserved. Frozen release and CAD unchanged.
No JLC upload, reservation, order or placement-model acceptance performed.

## 2026-10-07 — Fresh prototype artifacts completed

Frozen source: 0d6da576168b8284664dffa865b99ebe71e1d3c4, review repair branch.
Release: hardware/kicad/R3_PowerBox/manufacturing/RevA_PROTOTYPE_0d6da57/.
Read MANUFACTURING_RELEASE_REVA_PROTOTYPE.md and SHA256SUMS.txt there.
A has 91 Top candidates; B has 141 including 50 Bottom. C1 is manual/not DNP.
Factory LCSC sourcing remains UNRESOLVED; JLC physical placement acceptance is
pending. No order or factory qualification. PCB unchanged by export.

## 2026-10-07 — Prototype release freeze authorization

Owner supersedes export HOLD: J7 centroid is manual JLC alignment, not blocker;
C1 manual populate/not DNP; R107/108 DNP; no substitutions or ordering. Freeze
unchanged corrected PCB, export fresh Gerber/drill and A Top/B Both assembly
from one source SHA. Manufacturing policy is bom/prototype_assembly_policy.json.
Factory counts expected A91/B141; 50 Bottom manual in A, factory candidates in B.
All factory LCSC codes absent remain UNRESOLVED. Source-level CAD PASS is not
JLC library orientation or powered/thermal/EMI qualification. New release
manifest in manufacturing/RevA_PROTOTYPE_<source-sha> supersedes prior HOLD notes.

## 2026-10-07 — C1 exact sourcing identified

Owner selected Panasonic EEE-FK1E470P, catalog EEEFK1E470P = LCSC C178545.
PowerBox bom/C1_sourcing.json is the canonical sourcing decision. Do not use a
generic replacement. JLC PCBA availability/rotation not confirmed: C1 manual
hold, excluded from factory A and B until verified (not DNP). LCSC stock is not
JLC assembly stock. Earlier "C1 MPN unknown" notes are superseded; PCB unchanged.

## 2026-10-07 — U4 checkpoint pushed; Bottom audit continued

Repair checkpoint f7d5015ade2b919d4c04d0292dec8ebfc8cb2c4b pushed to existing
fix/r3-powerbox-reva-review1 branch before continuation. Main untouched.
Fresh fail-closed Bottom inventory verifies 54 footprints (50 parts, 2 DNP,
2 TP); F2/C109 nonpolar; Q1/Q4 physical1 is logical Source pad2, U10 physical1
CC1DB anchor verified. No additional PCB changes/rotations justified.
Full supplier CPL acceptance remains unresolved (C1 exact part, J7 selected
library centroid, accepted sourcing export). Production generation still gated;
do not mark a native-coordinate check as supplier orientation PASS.

## 2026-10-07 — Orientation audit / manufacturing HOLD

Current local review worktree repaired U4 mirrored physical numbering in its
library and PCB; bounded U4 bypass reroute, six bypass component moves only.
203 pad/net inventories preserved; 160 native position rows verified. DRC zero
errors/unconnected/parity, 42 library-copy warnings; domain audit PASS and 675
critical pin/net/order checks PASS with four rejected negative controls.
This does NOT close supplier orientation: accepted JLC LCSC/MPN export, C1 exact
part and J7 supplier centroid are missing. AO4407A is owner-selected for Q1/Q4;
physical G/S/D compatibility checked, source still DMP pending explicit sourcing
record. No guessed rotations/substitutions. Full release remains BLOCKED.
Old Gerber ZIP and quote A/B files obsolete after U4 ECO: do not use/upload.
Authority: PowerBox docs/JLC_ORIENTATION_FINAL_AUDIT.md. No new production exports
or push. User review2 preserved. Never replay one-shot routing ECO scripts.

The earlier bottom-component stop below was superseded by owner-authorized A/B
quote comparison: 92 Top versus 142 Top+Bottom intended placements, R107/108 DNP.
Only partial prices were observed; no complete PCBA quote or order resulted.

## 2026-10-06 — Economic approval, explicit inventory stop

Owner approved top factory/bottom manual but requires stopping for bottom parts
beyond C74/C75. Fresh unchanged-board inspection finds 48 additional non-DNP
parts, plus R107/R108 DNP and TP27/28 pads. Full list in PowerBox JLC quote report.
Stopped before generating/uploading assembly files; await inventory approval.

## 2026-10-06 — JLCONE partial quote

Owner's installed JLCONE uploaded Gerber: correct 160x80/4L. Five PCB,
1.6mm/1oz outer+inner/HASL lead = $49.97 before shipping/tax. Two assembled
selectable, three bare. Economic both-side disabled; full PCBA quote blocked
by missing audited CPL and exact assembly/MPN mapping. No order/cart submission,
no substitutions. PowerBox docs/JLC_QUOTE_2026-10-06.md has evidence/screenshots.
Chrome file-permission blocker below is now historical; continue via JLCONE.

## 2026-10-06 — JLC dry-run blocked before upload

Owner requested 5 PCB / 2 PCBA / 3 bare, no ordering or substitutions.
Revision/ZIP/BOM preflight passed at 0aeaea7; no CPL found, BOM lacks complete
MPN/assembly mapping and contains bottom-side parts. Chrome upload requires
user enabling extension file-URL access. No real quote or order obtained.
Resume from docs/JLC_QUOTE_2026-10-06.md under PowerBox, not default website prices.

## 2026-10-03 — Logo and owner-authorized prototype Gerbers

Added F.SilkS Garage Logic Lab artwork only; all existing board records remain
identical to 5d3da52. Prototype Gerber/drill ZIP and partial GLB exported locally.
See PowerBox docs/BRANDING_AND_3D.md. DRC 0 errors/0 unconnected/0 parity, 41
existing warnings. Export authorization supersedes earlier no-export restriction,
NOT qualification gates or ordering approval. No remote push in this work item.
Missing 3D bodies must not be interpreted as mechanical clearance. Owner review2
untracked file preserved unchanged. Schematics/BOM unchanged.

## 2026-10-03 — PowerBox Review1 CAD repair, fabrication blocked

Active worktree `C:/Projects/r3-powerbox-routing`, branch
`fix/r3-powerbox-reva-review1`, based on `cf7ea7c2a540037fdbbc916575e068ce5bee85fc`.
Main and A-F history untouched. Pushed schematic checkpoint ce12ca9 and charger
checkpoint 653dcbf; final verification commit contains this record (use Git SHA).
Authority: `hardware/kicad/R3_PowerBox/docs/REVIEW1_FIXES.md` and Review1 reports.
D1-D3 mapping, U2 floating EN, discharge resistor, 33V F2, local power copper,
capacitor footprints, common-bus ST VSYS supply, conservative ILIM corrected.
ST factory NVM first power MUST be 5V-only/non-PD before 5/9/12V programming.
Unknown-source clamp ~0.30A nominal replaces unsafe tolerance assumptions of
the former nominal 0.50A divider; confirmed source ceilings remain unchanged.
DRC0errors/0unconnected/0parity, 41 identified library-copy warnings; ERC0errors
with explicit generator-warning ledger. Semantics/negative-controls/isolation,
filled mounting envelopes, unchanged mechanics/Kelvin all host checked.
NOT bench tested. Exact MLCC DC-bias qualification and PPTC hot-current envelope
remain blockers; INA filter/preload DNP bench-selectable, no Y-cap added.
Never replay historical review1 mutation recipes or A-F on the routed PCB.
New recipe guard prevents ordinary replay. Schematic generator then arranger
only on fresh source output. No production Gerbers, order or main merge.
Shared owner manual updated on separate local docs branch in lily-logger-r3,
commit 22d1641; no unrelated remote push. Firmware policy is not deployed code.

## 2026-09-28 — Routing F complete, prototype only

Active worktree `C:/Projects/r3-powerbox-routing`, branch
`routing/r3-powerbox-reva`. D/E were pushed at `b42e73f` before final cleanup.
F: all nets connected; DRC 0 errors, 43 explicit library-copy warnings,
0 schematic parity issues; ERC 0 errors/412 existing generator warnings.
1343 segments/337 vias. Actual filled isolation/mounting audit and exact
schematic pin/net parity PASS. Main remains untouched. Final F commit is the
commit containing this entry; use git log rather than an invented self-SHA.
Canonical scope/limitations: `hardware/kicad/R3_PowerBox/docs/ROUTING_F.md`.
Do not rerun earlier routing/placement generators: routed PCB is authoritative.
C75 alone moved during F to fix SW2 bootstrap projection below I2C/NTC;
zone outlines, holes, B2B and other E placement/routes preserved, aside from
six redundant dangling objects and audited local bootstrap/PROG escapes.
L3 fixed SRP7028A-1R0M; firmware must keep 1.5 MHz. U11 remains DNP reservation.
No bench, enclosure, thermal or EMC acceptance; no production Gerbers/order.

## 2026-09-28 — Routing checkpoint E

All nets connected after domain planes and thermal copper. DRC 0 errors,
0 unconnected, 156 warnings; actual filled-copper corridor/mounting audit passes.
Continue F cleanup, derived-file regeneration and final branch push.

## 2026-09-28 — Routing checkpoint D

All non-ground interconnects connected; 112 ground findings remain for E.
No DRC error-severity findings; no planes yet. Continue E/F automatically.
See PowerBox docs/ROUTING_D.md for exact local corrections and pending return review.

## 2026-09-28 — Routing checkpoint C

Independent pre-isolation feeds and secondary/LDO local rails routed on top of B.
283 unconnected, no planes; no DRC electrical/geometric errors. Continue D/E/F.
Canonical continuation details: PowerBox docs/ROUTING_CHECKPOINTS.md.

## 2026-09-28 — Routing checkpoint B

Local primary buck routing added on top of A, preserving all A copper.
319 unconnected, no planes; no present DRC electrical/geometric errors.
Continue C/D/E/F, not a final board. See PowerBox docs/ROUTING_CHECKPOINTS.md.

## 2026-09-28 — Routing continuation, checkpoint A

Continue on `routing/r3-powerbox-reva`, never main. A0 is retained in Git;
checkpoint A adds shunt force/Kelvin, BMS gate/cell/NTC and charger local routes.
352 unconnected findings remain; no planes yet. This is NOT a finished board.
Detailed scope/exceptions: PowerBox `docs/ROUTING_CHECKPOINTS.md`. Follow A with
B/C/D/E/F in the same session. The A recipe refuses to run after leaving A0,
so it cannot silently erase later routing. SW2 moved locally to (85,78) to
free gauge fanout; connectors, mounting, isolation anchors remain unchanged.

## 2026-09-28 — PowerBox routing branch A0 (incomplete)

Latest owner request authorizes prototype routing from `1ccbc857938f1d36dbe252c1533ed0361289e0a1`.
Work is isolated in `C:/Projects/r3-powerbox-routing`, branch
`routing/r3-powerbox-reva`; canonical main and its unrelated dirty files are
not modified. Baseline branch: `baseline/r3-powerbox-pre-routing-1ccbc85`.
Only A0 partial charger/positive battery routing exists: 126 segments / 54
vias, 403 unconnected DRC findings, no ground pours, Kelvin/shunt NOT routed.
Eight pre-existing barrier pad intrusions and wrong-domain filter/TP/RUN
placement were corrected. Never repeat the older "isolation verified" claim
without the independent domain audit and negative-control DRC test.
Continuation and evidence: `hardware/kicad/R3_PowerBox/docs/ROUTING_CHECKPOINTS.md`.
This is NOT a routed release, not completed checkpoint A, and not suitable
for fabrication. Placement generator now refuses to erase existing tracks.

## 2026-09-28 — R3 PowerBox mechanical/interconnect baseline

FINAL PRE-ROUTING / NOT ROUTED: PowerBox now has six 3.2 mm NPTH M3 holes
with 8 mm four-layer keepouts, optional DNP J12 primary 2x8 and J13 isolated
2x5 generic 2.54 mm THT interfaces, and a dimensioned future-R3 envelope.
Exact coordinates/pinouts are in
`hardware/kicad/R3_PowerBox/docs/R3_BOARD_TO_BOARD_INTERFACE.md`. Use 15 mm
stack spacing: U3/U6 are 11.1 mm high, so 12 mm is conditional on upper-board
cutouts. Latest validation: 199 footprints including 6 PCB-only holes, 0
tracks/0 vias, ERC 0 errors/412 generator warnings, and zero clearance,
copper-edge, drill, annular, hole or courtyard DRC errors. Do not route until
the documented programming, thermal, enclosure, header/socket and bench gates
are closed.

## 2026-09-28 — R3 PowerBox KiCad workspace

FINAL PRE-ROUTING / NOT ROUTED: the canonical editable PowerBox source is
`hardware/kicad/R3_PowerBox/tools/generate_hierarchical.py`; generated KiCad,
PDF, BOM and reports are committed under the same project. The approved board
is 160 x 80 mm with 191 placed footprints, four copper layers, DIRTY -> PRIMARY
-> ISOLATION -> CLEAN zoning and a 3.0 mm all-layer functional-isolation
corridor. The architecture is 2S Li-ion -> BQ28Z610 -> BQ25798/STUSB4500 ->
switched `VSYS_MAIN` -> existing digital and isolated ADS/INA supplies.

Normal user power uses Q4 `DMP3007LSS-13`; BMS, PD and charging remain alive
when R3 is off. QON is a separate service/ship wake input. Raw BQ25798 STAT and
3.3 V `CHARGE_STATUS` are isolated by BAT54WS; J11 is the primary-only panel
interface. Latest checks: schematic PDF 11 pages, ERC 0 errors / 408 generated
library-grid warnings; critical PCB DRC geometry categories are zero; PCB has
0 tracks and 0 vias. Do not begin routing or order hardware until the blockers
in `docs/VERIFICATION.md` are closed: PD/BMS programming, Q2/Q3 and PPTC thermal
validation, TPS54302 at 6 V, RS3/INA light-load behavior, enclosure connector
clearance and approval of the functional-isolation rule.

## 2026-09-24 — shared session files and BLE resilience

R1 0.38 / CANBox 0.6.5 / R3 CC 0.2.1 deployed; STM32 CM7 LFN/UTC update
ST-LINK verified. R1/CANBox share UTC/group basenames and continue through BLE
loss; explicit offline STOP reconciles original session on reconnect. Hardware
R1/R3-controller tests PASS with no CAN frames; R1 finalized file integrity PASS.
Actual FatFs host test validates creation/modification fields and LFN. STM32
recording awaits ADS131 development (owner clarified), not yet ECO1 group member.
Earlier R1 HTTP outage cause unresolved; final short download PASS. No overnight
or load qualification. Viewer reader updated; running server needs restart.
[Contract, evidence, deployment and limits](../GLL%20CANBox/docs/SESSION_RESILIENCE_2026-09-24.md).

## 2026-09-23 — shared owner manual

Created the Ukrainian ecosystem manual with topology, entry points, workflows,
troubleshooting and evidence limits. Update it alongside user-visible changes.
Documentation only; no new build, firmware deployment or hardware acceptance.
[Manual](../lily-logger-r3/docs/manual/README.uk.md).

## 2026-09-23 — R3 primary CANBox integration verified

R3 now controls R1 and CANBox together and provides coarse UTC. R1 firmware
unchanged. Group START/STOP, saved R1 fallback and return to R3 passed;
25/25 post-return fresh/time samples, not precision acceptance. Canonical report:
../lily-logger-r3/docs/CANBOX_CONTROL.md. Existing averaging owner edits preserved.

## 2026-09-23 — CAN Live update deployed

Shared CAN assets deployed by OTA alongside existing0.37 owner changes.
88 tests/build PASS; real UI122722/0 live-ring losses, not hardware losslessness.
R1↔R3 unchanged; CANBox UTC invalid/service adapter missing.
See [deployment report](docs/CAN_LIVE_FIXES_2026-09-23.md).

## 2026-09-22 — shared CAN workspace

0.36-can-live-dev deployed via native COM9 to verified active app1 at 0x490000;
READY, generation 6. CAN tab and `/can`, preserving 0.35 OTA/timezone. Canonical
assets: ../GLL CANBox/workspace; contract: ../GLL CANBox/docs/CAN_WORKSPACE.md.
BLE service-only; browser traffic directly over CANBox USB/Wi-Fi. 88 tests/build
PASS; real R1-hosted CAN page + CANBox Wi-Fi 60 s, 12/12 concurrent BLE/time
samples PASS while idle. No loaded CAN/TX qualification. Fallback mode enabled.

## Memory checkpoint — 2026-09-21

### Current state and evidence
BENCH TESTED within the bounded 2026-09-21 report: 0.35-ota-dev deployed, browser OTA app0 -> app1; local display offset saved at +120, EEPROM generation 6. Do not assume live IP/COM/firmware remain unchanged.

### Canonical references
- [docs/R1_S3_PLAN.md](docs/R1_S3_PLAN.md)
- [docs/DEVICE_UI_AND_TASKS.md](docs/DEVICE_UI_AND_TASKS.md)
- [docs/FILE_FORMAT_V2.md](docs/FILE_FORMAT_V2.md)
- [docs/UART_DIAGNOSTICS.md](docs/UART_DIAGNOSTICS.md)
- [docs/RATE_BENCHMARK.md](docs/RATE_BENCHMARK.md)
- [docs/OTA.md](docs/OTA.md)
- [docs/R5_FEATURE_MIGRATION.md](docs/R5_FEATURE_MIGRATION.md)

### Negative knowledge / do not repeat
UART/CP210x: cleaning and cable changes did not prove a root cause; keep cause unresolved, see UART_DIAGNOSTICS. Native USB is a separate path; see CANBox stability report for core affinity evidence. Do not equate 300 Hz clean transport with analog accuracy, or a closed directory enumeration with a held SD transfer. Do not replace R5 tools with a reduced viewer and claim feature parity.

### Open work
Automatic timezone/DST and shared display-zone propagation remain IDEA; only R1 fixed local offset is deployed. Extend OTA fault/power-loss qualification, loaded UART isolation and noise/calibration qualification. Encoder remains a stub. Unified viewer work stays in lily-viewer.

### Dependencies
R3 time/control authority, CANBox fallback control, lily-viewer file readers; TTGO is an OTA/network reference only.

Shared time/control contract: [R3 ECOSYSTEM_CONTROL](../lily-logger-r3/docs/ECOSYSTEM_CONTROL.md). Read the sibling notes before changing it. A shared local timezone remains a requirement, not a completed cross-device feature.

---

# R1-S3 ideas and continuity

Read before changes and revisit at scope/milestone changes.

- [Engineering plan](docs/R1_S3_PLAN.md): acquisition, PSRAM buffering, SD block writer, UI and migration.
- [Migration history](docs/R1_MIGRATION.md): historical implementation and validation.
- [Work reports](WORK_REPORT.md): current dated work, tests, deployment and remaining tasks.
- [Ecosystem time](docs/ECOSYSTEM_TIME_SYNC.md): R3 Control Center is the preferred clock; R1 runs autonomously without it.
- R3's sibling `NOTES.md` contains ecosystem ideas and hardware evidence; review relevant entries rather than assuming all features are already implemented in R1.

## 2026-09-21 owner requirements

- Expose manual calendar entry and browser-clock fallback when valid R3 time is absent.
- Preserve authenticated Control Center priority; never move RTC during recording.
- Maintain separate project work reports; preserve existing ideas and notes.

## 2026-09-21 shared Wi-Fi

Use TTGO-style saved station networks and mDNS, keeping the R1 AP as a recovery
path. Credentials belong in private bootstrap/NVS, never notes or Git history.
Review WORK_REPORT.md for actual deployment and LAN validation.

## 2026-09-21 unified operator time

Owner requirement: every device must show the same synchronized local calendar
clock, including device screens, web panels, file lists, recording filenames and
viewer timelines. Operators must not have to mentally convert UTC. R3 Control
Center supplies the preferred clock AND the shared display timezone; standalone
manual/PC setup supplies the fallback. Do not choose each browser's timezone
independently. Keep canonical UTC/sample timing internally for cross-device
alignment and backward compatibility, and store the recording's timezone/offset
so historical display remains stable after travel or daylight-saving changes.
Existing UTC recordings must not be reinterpreted as local timestamps.
This requirement is recorded; cross-device timezone propagation is not yet
implemented. See WORK_REPORT.md.

R1-only implementation: 0.34-local-time-dev uses the existing saved offset for
UI/OLED/new filenames; PC sync refreshes that offset. Automatic DST and shared
R3 timezone distribution remain deferred. See docs/uk/TIME_SETTINGS.md.

R1 0.35 includes browser OTA (/update); see docs/OTA.md and the physical acceptance
in WORK_REPORT.md. Keep OTA idle-only and preserve storage/acquisition ownership.
