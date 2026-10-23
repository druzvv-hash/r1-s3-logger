## External project memory audit - 2026-10-23

Documentation-only continuity repair requested by the owner. Read repository
memory, actual Git branch/status/history and the linked technical evidence.
Updated AGENTS milestone obligations, current NOTES, README entry point and
docs/PROJECT_MEMORY.md; preserved older reports and unrelated working files.
Pre-memory source/branch anchor: `9ad492a7febef3f72f6920bc6350b5c1a50d6bda` / `fix/r3-powerbox-reva-review1`.

Evidence reconciliation: PowerBox has progressed beyond the September pre-routing baseline. Rev.A
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


Validation in THIS task: memory-file presence, Git tracking/branch comparison,
new-link and documentation diff checks; final commit/push and NAS SHA-256 results
are recorded in EXTERNAL_PROJECT_MEMORY_AUDIT.md. Runtime/build/bench results
quoted above are from the named prior reports, not rerun here. No firmware,
device configuration, hardware access, orders or deployment changed.
Remaining work: Existing manufacturing/CAD files remain dirty/untracked. This pass commits reviewed memory only; factory source, order status and physical charger/BMS acceptance require separate work.

# r1-s3-logger — work reports

## 2026-10-09 — Consolidated RevB repository location

Owner requested one repository location visible under manufacturing. Moved the
entire71-file RevB project from revisions/RevB_PACKAGE_FIX_2026-10-08 to
manufacturing/RevB_PACKAGE_FIX_2026-10-08; before/after SHA256 equality checked for
every moved file. Moved the original task delivery ZIP intact into its delivery_snapshot/
folder; removed two task-output copies only after exact hash equality with repository
README/closeup. Updated entry-point documentation and current memory paths; preserved
historical reports and all RevA archives. Refreshed the current checksum manifest.
Project-local library paths use KIPRJMOD and continue resolving after the move.
No PCB geometry, schematic semantics, BOM, CPL, JLC order or payment changes.
No new DRC/bench acceptance claimed for this file-organization task.

## 2026-10-08 — Separate RevB package correction candidate

Created revisions/RevB_PACKAGE_FIX_2026-10-08 as an independent KiCad project with
local libraries and schematics. Corrected U9 DRZ copper/EP/fab and shifted origin
X+0.55mm to retain left fanout; rerouted six right-side fanout elbows. Enlarged/
reshaped U1/U4 EP with windowed paste; removed Q2/Q3 same-drain aperture overlaps.
Updated project-local footprint assignments and universal stencil A1/A3/B3/C2.
Regenerated Gerbers/drills, reference positions and stencil ZIP. Preserved RevA.

Initial pad-only movement caused local shorts; not accepted. Relocated footprint
and rerouted fanout until DRC0 errors/0 unconnected/0 schematic-parity issues,
39 preexisting library mismatch warnings. ERC0 errors/423 baseline warnings.
All pad-net/reference sets retained; only U9 position changes; all sides/angles
retained. Source RevA SHA256 remains b97675a2f1d249f53b645572c5bd6f37c896afa56bb287ec21101c447e56bb48.
Full-board paste intersection screening confirms Q2/Q3 correction; only intentional
J7 duplicate power/ground pads remain. Closeups visually inspected. No thermal or
physical qualification; remaining J7 placement and Q1/Q4/SW1 vendor checks recorded.

Owner explicitly requested no JLC changes: none performed. Candidate does not fix
already paid RevA order. Filtered factory BOM/CPL must be regenerated before later
upload because U9 origin and footprint names changed. No manufacturing approval.


## 2026-10-08 — Component package audit after JLC U9 rejection

Compared all140 factory BOM references to actual embedded copper geometry and
saved selected-part catalog metadata.134 signatures match installed KiCad pads;
six custom references inspected separately. Read primary TI/ADI/ST/GCT/Bourns/
E-Switch drawings. U9 confirmed source land-pattern defect:2.70mm row separation
instead of3.80mm; incorrect EP. U4/U1 EP proportions/size and Q2/Q3 original paste
overlap require engineering review; J7 XY pattern fits but placement warning remains.
131 bounded PASS,8 WARN,1 FAIL. Q1/Q4/SW1 independent drawing review incomplete,
explicitly WARN. No fresh live-order identity verification or thermal/bench tests.

Created per-reference HTML/JSON report and same-scale U9 comparison in task outputs;
canonical technical report PACKAGE_FIT_AUDIT_2026-10-08.md includes Ukrainian owner
actions. Superseded prior CAM-only approval advice; universal B3 shares source error.
Verified board SHA256 unchanged. No BOM/CPL/CAD/release/production order edits,
messages, payments or confirmation clicks. Manufacturer download timeouts and
threaded PDF rendering were bypassed with bounded curl and serial local rendering;
some exact vendor drawings remain unverified, not silently accepted.


## 2026-10-08 — Paid JLC production files reviewed

Owner reported payment, then inner copper upgrade payment on Oct7. JLC production
metadata now confirms 1 oz outer AND inner / 4 layers / 1.6 mm. Final board160x80;
160x90 includes two5mm rails. Source archive12files matches frozen release.
Stencil431apertures/20patterns retained; factory boundary differences <0.002mm.
See hardware/kicad/R3_PowerBox/docs/JLC_PRODUCTION_REVIEW_2026-10-08.md for bounded
geometry checks, nonfunctional inner-pad removal and limitations. No blocking fab
mismatch found; PCBA J7 placement warning remains separate. No Confirm clicked.
This supersedes earlier local notes saying the order was only in cart/unpaid.


## 2026-10-07 — Universal IC stencil created and added to JLC cart

Read active project inventory and hardware declarations, excluding duplicate PowerBox
backups and donor snapshots. Cross-checked package families with primary manufacturer
references (linked in package README). Created an independent 200x200 mm KiCad stencil
layout from 11 embedded PowerBox patterns plus 9 library patterns for R1/R3/CANBox.
ADS131M08 includes both package alternatives. FRAM generic 208mil and EEPROM SO8 are
explicit fit-check variants, not recovered module CAD. Unidentified module chips excluded.

Geometry screening found source CSD17577 paste-window overlap; trimmed two right drain
windows in the stencil only. Windowed U4 EP and removed its original paste aperture.
Final 431 apertures: no polygon intersections/containment; minimum gap 0.14 mm and
area ratio 0.778 at 0.10 mm. Rendered and visually reviewed SVG. Verified source PCB
SHA256 unchanged. This is HOST CHECKED geometry, not physical paste transfer acceptance.

Uploaded paste/outline-only ZIP to owner's JLCONE and added 1 frameless electropolished
0.10 mm stencil to existing cart, $12.19 excluding shipping. Verified Product Details:
custom 200x200, Top, qty1, exact paste1:1, production-file confirmation. Base Dimension
field still reads380x280 alongside correct Custom size200x200; check final factory CAM
outline. Disabled automatic production-file confirmation. No checkout/order/payment.
Cart screenshots retained only in local task outputs, not project memory. Package README,
Ukrainian use instructions, map, reproducible source, geometry and cart status are under
manufacturing/Universal_IC_Stencil_2026-10-07. Frozen release and unrelated edits preserved.


## 2026-10-07 — Read-only live JLC orientation review

Inspected owner's JLCONE Component Placements in 2D, both sides and magnified
critical regions, against frozen CAD renders and pin/net orientation audit.
Critical IC, MOSFET and diode markers visually agree; Bottom D4 direction agrees.
J7 contact row appears left of PCB lands; exact correction/cause unresolved.
Recorded bounded findings in docs/JLC_LIVE_ORIENTATION_2026-10-07.md and five
screenshots in reports/jlc_live_orientation_2026-10-07. Passive groups received
overview checks, not independent enumeration of all JLC placements. No rotations,
translations, source/export edits, order or payment; left J7 enlarged for review.

## 2026-10-07 — Assembly deliverables copied into repository

On owner request, saved the five current deliverables in manufacturing/
RevA_JLC_L1_MANUAL_2026-10-07 under hardware/kicad/R3_PowerBox. Verified all
copies against local outputs by SHA256; added README and canonical report link.
No changes to frozen release, CAD or unrelated owner files; no commit or push.

## 2026-10-07 — L1 moved to manual assembly on owner request

Updated both delivered factory CSVs to remove only L1. Added L1 to the manual/
DNP CSV as MANUAL_POPULATE, and updated the HTML and validation snapshot.
Independent CSV re-read confirmed exact equality to prior tables minus L1,
140 unique matching references, 90 Top/50 Bottom and manual L1 disposition.
Remaining sourcing/placement warnings persist; no CAD or frozen-release edits.

## 2026-10-07 — JLC BOM/CPL sourcing draft checked

Read the supplied JLC recognition workbook and frozen RevA assembly source.
Created two CSV drafts and a full 141-row HTML review in the Codex task outputs.
Independently re-read CSVs: 141 unique references, BOM/CPL reference parity,
quantity 1 per position, 91 Top/50 Bottom and all native XY/rotation values PASS.
Compared against frozen XLSX and verified source PCB SHA256. Previewed both
CSV table renders. Public JLC component metadata checked on 2026-10-07; 62
selected codes cover 140 positions with enough orderable stock for two boards.
L1 remains unavailable. Stock is not reserved and process losses must be
rechecked in the actual order. Proposed substitutions and TS-divider sensitivity
are documented in docs/JLC_SOURCING_2026-10-07.md and the HTML review.
No CAD/frozen-release modifications, order, upload, model alignment acceptance,
or electrical/thermal qualification. Existing unrelated untracked files preserved.

## 2026-10-07 — Fresh prototype package generated

Source 0d6da576168b8284664dffa865b99ebe71e1d3c4 pushed on repair branch.
Fresh Gerbers/drills, 5 assembly/manual XLSX workbooks and source manifest generated
from that frozen state. Saved workbooks re-imported and every cell compared;
all five previews visually checked. Native CPL parity includes reference, side,
XY, angle, footprint, MPN and LCSC. A91/B141; no automatic substitutions.
All factory LCSC codes unresolved; C1 exact C178545 is manual/not DNP.
DRC 0 errors/0 unconnected/0 parity findings, 42 warnings; ERC 0 errors/423
warnings. Polarity, physical mapping, Review1 regressions and isolation PASS.
Release directory disables Git text conversion to preserve hashed raw bytes.
Removed only temporary dependency junction; dependency target untouched.
Old quote/user-review files excluded. No JLC visit, order or further CAD edit.

## 2026-10-07 — Prototype manufacturing source freeze

Confirmed 9ee68f9 and no tracked uncommitted CAD changes in same review worktree.
User explicitly permits prototype export with J7 manual placement alignment and
C1 manual/not DNP. No schematic/PCB changes performed. Fresh DRC: zero errors,
zero unconnected/parity, 42 known library-copy warnings. Fresh ERC: zero errors,
423 accounted warnings (212 symbol mismatch, 211 off-grid). Review1 checker now
accepts explicit release report inputs and compares warnings with U4 checkpoint,
not outdated pre-U4 warning inventory; mechanics/Kelvin checks still independent.
Physical/bottom/native-position/current-path/absolute-rating/polarity/domain/
mounting/branding checks and semantic/isolation negative controls passed.
Historic A-F baseline preservation scripts are stage-specific, superseded by
Review1 and U4 bounded-ECO comparisons, not replayed on the repaired design.
Added frozen-source export recipe and A/B assembly policy. Output remains
prototype-only with unresolved sourcing and mandatory manual JLC review.

## 2026-10-07 — Exact C1 catalog match

Searched hyphenated and normalized owner MPN. Panasonic and LCSC identify
EEEFK1E470P, C178545, 47uF/25V FK 6.3x5.8mm body; LCSC lists 6.1mm maximum
seated height. Public LCSC page showed 10,915 stock; no reservation or purchase.
Direct JLC page unavailable and no verified JLC assembly stock/zero-angle found.
Saved sourcing JSON and updated audit: no substitute; manual hold/exclude factory
A/B until assembly verification, not DNP. No PCB/schematic/production file edits.

## 2026-10-07 — Continued audit and requested Git checkpoint

Committed all scoped U4 repair/source/report/render changes as f7d5015 and pushed
existing review branch before further edits. Unrelated quote files and owner
review2 remain outside the commit. Added Bottom classification/physical-anchor
audit: PASS for 54 Bottom footprints, F2 PPTC and C109 ceramic nonpolar, all
visible Bottom fields mirrored, DNP R107/R108 preserved. Exact physical anchors
verified for Q1/Q4 (logical2 Source), U10, C1 positive and D4 pad1.
Re-ran physical mapping (675 PASS, four negative controls rejected) and native
position/ECO parity PASS. No new routing or component placement changes.
Repeated original-ST PDF download routes timed out; no fabricated graphical
polarity approval. Detailed audit records remaining supplier-dependent gates.
No production ZIP/BOM/CPL generated because requested complete orientation PASS
is not established; unknown MPNs remain unresolved rather than substituted.

## 2026-10-07 — U4 physical correction and bounded orientation audit

Read the pasted final-audit request and current review worktree, not routing
baseline. Confirmed U4 local physical pin ordering was vertically mirrored.
Corrected project .kicad_mod and embedded footprint; reflected six bypass/enable
components and local copper, retained U4 origin and external trunk anchors.
Initial input-feed reflection crossed thermal ground vias (7 DRC findings);
detoured local feed and refilled. Final DRC zero errors/unconnected/parity, 42
library-footprint mismatch warnings. Domain/corridor/mounting audit has no issues.
Added physical marker/reference repairs without moving critical devices.

Added independent critical pin/net/symbol/order contracts: 675 checks PASS; four
in-memory fault injections rejected. New native coordinate export verified for
160 position-eligible references; 203 footprints preserve pad/net identities.
Only C40–44/R40 anchors changed; 50 changed copper UUID records are local to U4
plus its retained output anchor. Initial comparator hit KiCad's via GetWidth
API assertion; stopped and corrected via/track overload use, then PASS.
GCT original drawing confirms J7 CAD contacts/shell/center; no guessed shift.
Supplier BOM/centroid absence remains unresolved, as does exact C1 selection.
AO4407A user selection documented; no unapproved substitute or BOM rollback.

Saved actual KiCad renders, DRC, inventory, domain and export audit reports and
docs/JLC_ORIENTATION_FINAL_AUDIT.md. Old fabrication/quote files explicitly marked
obsolete. No new manufacturing release while acceptance gates fail; no order,
remote push, main modification or claim of hardware acceptance. Read-only ST PDF
download timed out; don't claim its unavailable graphical check passed.
Shared owner manual receives the same HOLD notice. Work is local and incomplete
at the supplier-data gate; no reliable elapsed-time/resource total was captured.

## 2026-10-06 — Bottom assembly stop condition verified

Read current PCB using pcbnew: 54 bottom footprints, 50 non-DNP components
including C74/C75, 2 DNP preload resistors, 2 test pads. Enumerated 48 additional
parts in JLC quote report. User's explicit stop condition applies; no assembly
file generation/upload, circuit/placement edit or order. First diagnostic JSON
serialization failed on KiCad UTF8 footprint string; rerun with ordinary
reference/value/DNP fields succeeded. Current HEAD remains 0aeaea77.

## 2026-10-06 — JLCONE continuation, partial PCB quote

Used installed JLCONE on owner request. Uploaded previously verified ZIP;
confirmed 160x80mm/4L, 5 PCB, 1.6mm. Selected inner 1oz matching outer 1oz:
PCB $49.97 ($7.90 board+$25 engineering+$17.07 inner copper). HASL lead default.
2-unit PCBA selection available, but Economic both sides disabled. Reached
BOM/CPL upload gate; no assembly files or substitutions uploaded/accepted.
Shipping widget $23.21 has unverified destination, not Czech delivered quote.
Captured five screenshots and retained native app at BOM/CPL page. No order,
cart submission, payment, PCB edits or remote push. Scope decision needed for
bottom assembly and exact sourcing before defensible total PCBA price.

## 2026-10-06 — JLC quotation preflight and browser blocker

Read current memory and checked HEAD/status. Verified Gerber ZIP manifest,
board export hash, 4 layers/1.6 mm and 197 BOM references/values against PCB.
Found no CPL; no complete factory/manual or exact-part mapping in current BOM.
Opened JLC calculator and attempted authorized ZIP upload; browser extension
denied file access. Stopped without changing browser permissions, ordering,
substituting parts or reporting default prices as an R3 quote. Saved screenshot
and detailed dry-run report. User review2 untouched; no source/PCB edits or push.

## 2026-10-03 — Logo / prototype fabrication / 3D

Added reproducible monochrome native logo group, no electrical edits. Initial
placement conflicted with J13 silk; corrected and repeated DRC: zero errors,
zero unconnected/parity, only 41 historical library-copy warnings. Token-level
board comparison proves all pre-existing records unchanged. Generated nine
Gerbers, separate PTH/NPTH drills/maps, manifest/ZIP, partial GLB and native 3D
preview. Render command initially rejected unquoted negative angle; positive
quoted camera angle succeeded. KiCad model export reports missing library bodies;
no fabricated mechanical acceptance. Export README retains qualification gates.
No ordering, main change or remote push. Owner review2 file not modified.
Shared owner workflow updated in sibling manual; see BRANDING_AND_3D.md.

## 2026-10-03 — PowerBox independent review repair

IMPLEMENTED / HOST TESTED only. Started from owner-authoritative clean cf7ea7c,
created fix/r3-powerbox-reva-review1, preserved review input (ba8c09e), pushed
schematic/component correction ce12ca9 and local charger checkpoint 653dcbf.
Final verification/source/generated/docs commit contains this entry. No main
changes, no rewritten A-F history, no baseline regeneration, no Gerbers.

Corrected physical D1-D3 mapping, unsafe U2 EN, ST discharge path, USB PPTC
voltage rating, local capacitance/footprints, I2C pull-ups and exact parts.
Reworked charger/U2/USB local copper, paired high-current transitions, preserved
Kelvin/mechanics/isolation. Extended full battery/feed graph identified a
0.50 mm F3-to-Q4 bridge; widened only that segment to 0.80 mm, DRC remained clean.
ST datasheet exposed a battery-only common-bus
blocker (unpowered SCL/SDA pulldowns): supplied VSYS from +3V3_D and added C109.
Recomputed ILIM with leakage/REGN tolerance: 28.7k/10k0.1%, nominal0.30A.
Added polarity, selected abs-max, actual widest copper-path/parallel-via checks
and deliberate-fault tests. Regenerated schematic/PDF/BOM/ERC and native plots.
All electrical DRC/parity/unconnected errors zero, 41 visible historical
footprint-copy warnings. ERC warning ledger retains generator artifacts,
including newly reported C101 generated-symbol warning; no hidden electrical waiver.

Failures and recovery: overly compact local charger/PD trials failed DRC and
were corrected locally, not by board reset. KiCad Flip-before-Add crashed;
parity caught the unsaved capacitor, then Add-before-Flip repaired it. Stale
zone fills can reassign nearby vias; invalidate/refill before audits. Guarded
all one-shot trial recipes against ordinary replay. A single deliberately
thinned redundant trace still had an alternate valid path; negative control
now thins the full tested rail and correctly fails. Documentation records
what these checks do NOT establish.

Open: exact-MPN effective MLCC capacitance could not be validated from the
accessible manufacturer curve data; selected MPN is not purchasing approval.
F2 2.25A hot continuous operation not qualified. Factory PD NVM interlock,
startup accuracy/attach/inrush, charger/SW thermal/EMI, 6V U2 operation,
INA light-load noise and battery protection require powered validation.
Detailed evidence/next actions: hardware/kicad/R3_PowerBox/docs/REVIEW1_FIXES.md.
Shared owner manual updated/committed locally in lily-logger-r3 (22d1641),
isolated docs branch; no firmware changes or unrelated remote publication.

Resources: KiCad10 CLI/Python, SKiDL, manufacturer datasheets, native vector
plots and PDF rendering. No subagents, generic autorouter, bench instrument
or hardware tests used. Accurate full-session elapsed time/token/cost records
are unavailable here; no numerical resource claim is inferred from commit times.

## 2026-09-28 — Routing D/E preservation and F completion

IMPLEMENTED / HOST CHECKED only. D/E commits were pushed to
`routing/r3-powerbox-reva` at `b42e73f` before the requested final cleanup.
Continued that PCB without regeneration/reset or rerunning A-E. Finished F:
0 unconnected, 0 DRC errors, 43 visible library-copy warnings, 0 schematic
parity findings; ERC 0 errors/412 known generator warnings. 1343 track segments,
337 vias. Main/canonical dirty worktree not modified.

Removed six redundant dangling objects, cleaned silk and library metadata,
corrected a verified SW2-bootstrap projection under I2C/TS with C75 local move
and branch/PROG-escape changes. All other E placement, zone boundaries and
routes retained. Exact change/net/mechanical/Kelvin/domain audits saved.
Filled-copper isolation/mounting audits and intentional isolation-negative
control pass. Kelvin pickup is separate from force copper, not length matched.
Regenerated schematic/PDF/BOM/ERC; fixed omitted DNP flags in the SKiDL drawing
pipeline; L3 exact MPN SRP7028A-1R0M recorded with 1.5 MHz firmware constraint.
Native top/bottom/inner/isolation images and 11-page PDF reviewed.

Failures/recovery: KiCad SWIG track-container lifetime caused a process crash
before saving; keeping the container alive fixed it. First local bootstrap
candidate failed DRC near PACK_POS and was corrected before acceptance.
An arranger-only rerun on already-arranged sheets is not supported (J1 key
lookup failed); ran the schematic-only generator then arranger successfully.
No PCB generator was invoked. Final DRC has no short/clearance/hole/silk findings.

Evidence and open hardware gates: `hardware/kicad/R3_PowerBox/docs/ROUTING_F.md`.
This is Rev.A prototype routing, not production-ready or powered acceptance.
Final branch commit/push contains this record; no main merge or PCB/BOM order.

## 2026-09-28 — Routing checkpoint C

HOST CHECKED: independent ADS/INA filters, RS3 secondary splits, INA bipolar
filters and clean LDO local loops. Source net mapping unchanged, prior copper
retained. Some SIP-local bypass/filter parts moved to B.Cu to avoid module-body
courtyard conflicts. 523 segments / 162 vias; 283 unconnected, 83 dangling vias,
175 silk warnings. No present electrical/geometric DRC errors; independent
isolation and mechanical/net audits pass. Native copper plots inspected.
Planes/thermal/final return and bench acceptance remain open. Continue D/E/F.

## 2026-09-28 — Routing checkpoint B

HOST CHECKED local U1/U2 routes: SW/VIN/output/feedback/SS/PG/BOOT plus ground
stubs and U1 thermal vias. Local unrouted placements adjusted, A copper retained.
420 segments / 123 vias. DRC: 319 unconnected, 57 dangling vias, 180 silk
warnings, zero present electrical/geometric errors. Domain/net/mechanical
audits pass; native plots inspected. No planes/complete return or bench
validation. C/D/E/F follow automatically on the routing branch only.

## 2026-09-28 — Routing checkpoint A continuation

IMPLEMENTED / HOST CHECKED ONLY. Started from owner-specified A0, not the
pre-routing board. Added BAT_NEG force/shunt fanout, separate pad-origin
SRP/SRN filters, gauge VSS/PBI/cell/NTC/gate paths, charger VAC/PROG/BATP/TS/
ILIM/SDRV local routing. SW2 relocated locally; all J/H/module anchors retained.
Only five A0 segments and one BTST2 via replaced to unblock charger fanout.
Kelvin front-layer no-pour regions protect the shunt-side sense stubs.
No source net changes; no routing on main. 343 tracks / 101 vias, 352 remaining
unconnected findings, 42 dangling ground vias awaiting E, 181 silk warnings.
No present clearance/short/edge/hole/drill/annular/courtyard violations.
Independent isolation audit and mechanical/net invariant checks PASS with
the explicitly documented SW2 exception. Native copper plots inspected.
Remaining return/thermal/plane and complete connectivity checks are NOT passed.
Continue B-F; current evidence is in PowerBox reports/routing_checkpoint_A_drc.json.

## 2026-09-28 — R3 PowerBox routing A0, partial checkpoint

IMPLEMENTED / HOST CHECKED ONLY. Created isolated routing worktree/branch from
the owner-specified main SHA and a baseline branch. Canonical main's unrelated
dirty work was not touched. No electrical schematic/net assignment changed.

Independent audit disproved the prior isolation-clear assertion: eight pad
boxes intruded into x=121..124 and additional primary/secondary components
were placed in the wrong domain. Corrected those positions while preserving
all connector/mounting/module anchors and upper-board envelope. Added a named
disallow rule plus a scratch-only deliberately bad track/via/pad test; all
three failures are detected. Original rule-area-only miss: cause unresolved.

Explicit non-autorouter recipes add initial BQ25798 switching/bypass/bulk and
Q2/Q3 positive-force paths: 126 segments / 54 through vias. C74/C75 are on
the underside per TI's layout example. Intermediate DRC found local overlaps,
power-bus/ground-via conflicts and a J10 NPTH conflict; these were fixed before
the checkpoint. Remaining: 403 unconnected findings, 35 dangling vias and
211 silk warnings; zero present clearance/short/edge/hole/drill/annular/
courtyard errors. ERC: 0 errors, 412 inherited symbol/grid warnings.

This is A0, not completion of requested checkpoints A-F. Shunt force/Kelvin,
cell/gate networks, remaining power/control/B2B routing, planes, thermal and
final cleanup are still open. No production Gerbers or acceptance claim.
See `hardware/kicad/R3_PowerBox/docs/ROUTING_CHECKPOINTS.md` for reproduction,
exact next work and evidence; new copper views are explicitly marked incomplete.

## 2026-09-28 — R3 PowerBox mechanical and B2B pass

Added six electrically floating 3.20 mm NPTH M3 holes with project-local 8 mm
all-copper-layer keepouts, DNP J12 primary 2x8 and J13 isolated 2x5 generic
2.54 mm THT stacking interfaces, a dimensioned `Dwgs.User` upper-board
envelope and reproducible top/side mechanical views. Existing Micro-Fit cable
interfaces, user power controls, zones and 3 mm isolation corridor remain.

The final placement has 193 electrical footprints plus six mechanical holes,
0 tracks and 0 vias. KiCad checks report ERC 0 errors/412 known generator-grid
warnings and zero clearance, copper-edge, hole, drill, annular or courtyard
geometry errors. Visual review covered all 11 schematic PDF pages. U3/U6 are
11.1 mm high, making 15 mm the recommended stack; 12 mm needs upper-board
cutouts. Routing remains blocked by the pre-existing programming/bench/thermal
gates plus final enclosure, M3 and header/socket mechanical selection.

## 2026-09-28 — R3 PowerBox KiCad capture

Created and advanced `hardware/kicad/R3_PowerBox` to a final pre-routing
checkpoint. The editable SKiDL source now generates a root plus ten functional
sheets covering 2S battery/BQ28Z610 protection, BQ25798 NVDC charging,
STUSB4500 USB-C PD, service-input muxing, user load switching, TPS62132/TPS54302,
separate ADS and INA primary filters, RS3E/RS3 isolation, ADM7150/TPS7A20 clean
rails, connectors and test points. `DGND` and `GND_ISO` remain distinct.

Closed the final UI/control correction: Q4 `DMP3007LSS-13` switches
`VSYS_PROT` to `VSYS_MAIN` while BMS/PD/charging remain upstream; SW1 is normal
latching power and SW2 is separate QON service. D5 remains on REGN/raw
`BQ_STAT_RAW`; BAT54WS isolates the 3.3 V `CHARGE_STATUS` logic. J11 exports
panel power/control/I2C/status without shared onboard LED-anode nets or GND_ISO.
The conservative status LOW is <=0.72 V, below STM32H755 and ESP32-S3 limits.

Validation with KiCad 10.0.0 and SKiDL 2.3.0: PDF export PASS and all 11 pages
visually inspected; ERC 0 errors / 408 generated library-grid warnings. BOM and
logical net map regenerated. The 160 x 80 mm four-layer preliminary placement
contains 191 footprints, no courtyard overlap, 0 tracks and 0 vias. DRC has zero
clearance, copper-to-edge, drill-range and annular-width findings; remaining
items are expected unrouted connections and silkscreen cleanup. No Gerbers,
routing, procurement, assembly, power-up, thermal, ripple, EMC, isolation or
load acceptance was performed. Exact routing blockers remain recorded in
`hardware/kicad/R3_PowerBox/docs/VERIFICATION.md`.

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

Added CAN tab, embedded `/can`, PC bridge route and generated common assets from
../GLL CANBox/workspace. BLE remains service/control/time only. Browser directly
uses CANBox USB/Wi-Fi; no CAN payload relay through R1. Version 0.36-can-live-dev.
Preserved OTA, timezone and linked-recording implementation.

HOST TESTED: build and 88 Python tests PASS (PlatformIO Python with pyserial).
BENCH TESTED: native COM9 flash/hash to verified active app1 0x490000; subsequent
STATE 0.36/READY/generation 6. Real R1-hosted `/can` + CANBox Wi-Fi: rejected wrong
token, 60 s live/status without stale UI, clean disconnect. Concurrent R1 BLE:
12/12 connected/fresh/clock synced; fallback mode enabled. Zero CAN frames seen.
No physical TX, loaded traffic or new analog accuracy qualification. No R3 flash.
Canonical protocol, LED wiring and limits: sibling docs/CAN_WORKSPACE.md and
CAN_WORKSPACE.uk.md. Evidence stays private in CANBox/local; secrets not committed.

Append dated entries with scope, changes, validation, limitations, deployment and next steps. Do not include credentials or claim unperformed tests.

## 2026-09-21 — reporting established

Created this project-specific report at the owner's request. Existing notes and
history remain authoritative; this entry does not claim a retrospective code or
hardware audit. No firmware was deployed and no project functionality changed
as part of this reporting setup.

## 2026-09-21 — Control Center clock priority and local time UI

Request: make the R1 clock configurable with R3 Control Center priority and manual
fallback; consult existing ideas and maintain independent project reports.

Changes:
- Added Overview date/time controls: explicit browser clock or local calendar
  entry, timezone display and conversion to UTC. Invalid dates and spring DST
  gaps are rejected; repeated autumn times use the browser's earlier occurrence.
- Fresh authenticated valid R3 UTC (under 5 seconds old) prevents manual RTC
  writes in both UI and firmware, including legacy serial commands. CANBox is
  not treated as R3 time authority. Disconnect/invalid/stale R3 allows fallback.
- Existing recording guard and RTC readback remain. Only the already validated
  ecosystem owner path bypasses the local-clock priority guard; it still cannot
  change time while recording. Manual changes invalidate old R3 provenance,
  allowing existing automatic synchronization to resume when R3 returns.
- Accepted 9-digit Unix timestamps for the supported year-2000 RTC range.
- Version: 0.32-time-dev; no EEPROM schema or recording format change.
- Read R1 engineering/time plans and sibling R3 NOTES.md. Added R1 NOTES.md links,
  owner time instructions and shared C:/Projects/AGENTS.md continuity rules.
- Created independent WORK_REPORT.md files in seven active Git repositories;
  archive/snapshot directories were excluded. Other repositories received only
  their reporting file, not functional changes.

Validation:
- Production PlatformIO build PASS: RAM 87,556 bytes; Flash 1,202,421 bytes.
- RTC priority host test PASS: executes actual admission functions against mocked
  hardware; freshness boundary, authentication, CANBox exclusion, recording lock,
  epoch bounds and absence of write/provenance side effects on rejected commands.
- Time browser fixture PASS: local-to-UTC, DST gap, no implicit write, authority
  and recording locks, mobile width. General panel and BLE browser fixtures PASS.
- Nine panel/API/bundle host tests and two BLE trust/protocol tests PASS.
- Updated the old BLE fixture assembly to include INA/chart modules and use the
  stable tab selector; it previously failed before exercising any BLE controls.
- git diff --check PASS.

Deployment: built locally, not uploaded to a board; no physical RTC/radio test,
commit or GitHub push in this work session. Next: deploy to an identified idle R1
and test manual set/readback, R3 reconnect priority and power-cycle RTC retention.

## 2026-09-21 — requested deployment of time controls

Identified R1-S3 on native USB COM9 by MAC 90:e5:b1:cd:55:74 and PANEL
0.31-canbox-dev response. Recorder was READY with saved settings generation 5.
Built/uploaded esp32-s3-usb 0.32-time-dev successfully; flash hash verified.
Native build: RAM 87,356 bytes, Flash 1,187,985 bytes.

Three post-boot STATE responses confirmed 0.32-time-dev, READY, advancing samples
and RTC, ADC OK, TICK OK and zero I2C errors. Full configuration and EEPROM
generation matched pre-upload state. No TIME or EEPROM Save command was sent.
R3 time authority was unavailable during this check; physical R3 priority and
manual time write/readback remain separate acceptance tests. No Git commit/push.

## 2026-09-21 — shared LAN Wi-Fi, TTGO-style connection

Request: access R1 while phone/PC stays on the home network; provision known Wi-Fi
profiles. Read TTGO README/main.cpp and R3 NOTES.md. The inspected notes did not
contain home credentials; used the owner's saved Windows WLAN profiles instead.

Implemented AP+STA, three NVS profile blobs, 20-second nonblocking profile retry,
mDNS r1-s3-7455.local, LAN status/links and primary-network UI configuration.
Network writes run on the network task, with recording/download checks at both
queue admission and execution. Existing AP remains available. Fixed SD download
redirect to use the incoming interface's local IP instead of always the AP IP.
No OTA or captive portal was added. TTGO functional code was not modified.

Provisioned TP-Link_CC06, dlink_DWR-932_4280 and iPhone. Secret bootstrap header is
Git-ignored; credentials are absent from public docs and station status. NVS is
separate from measurement settings. Private seeded firmware must not be published.

Validation/deployment:
- LAN browser fixture and existing panel browser checks PASS; nine host panel/API
  checks PASS. Verified mobile layout and removed obsolete AP-only UI text.
- Built/flashed final 0.33-lan-dev via native USB COM9; image hash verified.
  RAM 89,796 bytes; Flash 1,219,625 bytes.
- R1 joined TP-Link_CC06 while PC stayed on the same network. Both
  http://192.168.0.149/ and http://r1-s3-7455.local/ worked.
- Real Chrome page showed advancing samples on one boot, zero I2C errors and no
  page errors over a bounded 15-second observation. SD directory listing passed.
- Downloaded an existing 735,865-byte CSV through the LAN redirect on port 81;
  Content-Length matched. SHA-256:
  c4dd33c702b56b1967f739f6ec1ece9b6a8744d2e9ed12facf5f52aca564bf9d.
  This is a transport check, not renewed measurement-file validation.
- After the final cosmetic reflash, automatic reconnect worked, READY returned,
  measurement configuration and saved generation 5 matched baseline, and the
  HTTP-served page matched the generated asset byte-for-byte.

Limits: alternate hotspots, router-loss recovery, profile changes through the
physical UI, phone acceptance and long-term BLE/Wi-Fi coexistence are not yet
qualified. RSSI varied roughly -71 to -82 dBm. No measurement settings, RTC or
recordings were changed; no Git commit/push was performed.

## 2026-09-21 — requested Git synchronization

Set RTC from PC using the visible UI button; UI confirmed RTC UTC written and verified. R3 time was unavailable, recorder idle. Audited the five outgoing CANBox commits and current time/LAN work for known WLAN secrets; ignored bootstrap/data remain excluded. Committing and pushing to the existing origin/main as requested. Previous build and targeted tests are recorded above.

## 2026-09-21 — unified local operator time requirement

Reviewed the reported two-hour discrepancy and current time/display code.
The R1 live clock explicitly renders UTC, whereas RTC input and directory dates
use browser local time. Existing display_utc_offset_min is not used for these
views; recording session names explicitly use UTC Z. The ecosystem contract
currently synchronizes UTC, without a shared operator timezone.
Recorded the owner requirement in NOTES.md: one shared local display convention
from the Control Center, persistent fallback, recording-time timezone provenance,
and compatible canonical timestamps. No firmware, RTC, recording or remote
repository was changed in this requirement review. Implementation and hardware
validation across R1, R3, CANBox and viewer remain outstanding.

## 2026-09-21 — R1 local operator time implemented

Deployed 0.34-local-time-dev on R1 native USB COM9. UI live clock and manual
calendar now use saved display_utc_offset_min rather than mixing UTC and browser
local time. PC time button applies/saves its current offset when different, then
sets RTC; existing priority/recording locks remain. OLED header now shows local
HH:MM:SS. New recording names include local calendar and explicit numeric offset;
random identity suffixes remain. Directory parser accepts both new offset names
and legacy UTC names; new names preserve their original local date after an
offset change. Existing CSV canonical UTC and config snapshot remain compatible;
recorded config already carries display_utc_offset_min. Other devices/viewer
were not modified.

Validation: nine serializer/contract/viewer roundtrip tests PASS, including
positive/negative offset, leap-day rollover and unknown time. Nine panel tests
PASS; browser fixture passed local conversion, legacy/new filename recognition,
priority/recording locks and mobile layout. Production build/upload PASS with
hash verification (RAM 89,796; Flash 1,220,093 bytes). Actual visible UI PC-time
button saved generation 6 and offset +120; full config comparison showed ONLY
that field changed. UI displayed 18:08:30 local; RTC was within one second of PC
in a sequential HTTP comparison, TICK OK, zero I2C errors. OLED time rendering
compiled/deployed but not visually observed. No new physical SD recording was
created; filename serialization was host-tested. Browser fixture ran in Prague;
no cross-timezone physical browser test claimed.

Limit: fixed saved offset, not automatic DST; update from PC at seasonal change.
Historical UTC-named files have no filename offset and use current R1 display
offset. Canonical CSV times remain UTC; viewer display work is deferred as asked.

## 2026-09-21 — browser OTA delivered

Read TTGO src/main.cpp as reference; no TTGO edits. Added authenticated /update
page with progress, same-origin/header validation, bounded exact image length,
S3 header check and standard Update verification before slot activation. R1
owner pauses acquisition only after excluding active/linked recording and taking
the SD request gate; releases on failure. Added Wi-Fi panel link and OTA guide.
USB bootstrap deployed 0.35-ota-dev, RAM 90,012 bytes, Flash 1,235,577 bytes.

Validation: nine panel host tests PASS; production build and USB upload/hash PASS.
Physical HTTP bench: missing authentication 401; foreign Origin, invalid header,
and truncated image rejected without reboot; owner resumed. Real Wi-Fi firmware
upload succeeded, verified app0 -> app1 and new boot ID, READY. Full configuration
and EEPROM generation preserved. Additional actual file OPEN lease blocked OTA;
lease closed afterward. A short test recording also blocked OTA while continuing
RUNNING, then STOP finalized it and returned READY. That SD file is a guard test,
not measurement qualification. An initial exhausted directory-list test did not
hold a lease (expected auto-close); the subsequent file OPEN exercised the guard.

Limits: browser form itself not manually uploaded in this bench; matching HTTP
multipart endpoint was exercised. Power loss, unhealthy-image rollback and hostile
LAN isolation are not qualified. See docs/OTA.md for authentication boundary and
firmware selection. No ArduinoOTA IDE protocol added. Existing trusted-LAN model
retained; credentials/images remain outside Git.

## 2026-09-21 — external-memory audit and bootstrap

### Request / Context
Establish durable project context without copying chat transcripts. Reviewed
existing entry documents, relevant reports, repository status and recent commits.

### Changes
Added/linked bootstrap and concise evidence-aware project memory. Existing
technical history, owner notes and unsuccessful approaches retained.

### Validation
Documentation-only audit: local reference existence and Git change scope checked.
No new build, host runtime, browser, bench, hardware acceptance or vehicle test.
Previously reported evidence remains attributed to its original source/scope.

### Result / Limitations
A new task can enter via AGENTS -> NOTES -> relevant WORK_REPORT/docs. This is
not a full code re-audit; contradictory old dates/version banners require the
linked newer report and current code. Private raw evidence may be local-only.

### Failed / rejected approaches
Rejected copying entire histories or turning backup/snapshot folders into active
projects. See NOTES for project-specific negative knowledge.

### Deployment / Next
Documentation only; no device changes. Workspace audit at
C:/Projects/PROJECT_MEMORY.md records repository classification and commit status.
Maintain checkpoints after substantial work; resolve the open tasks in NOTES.
