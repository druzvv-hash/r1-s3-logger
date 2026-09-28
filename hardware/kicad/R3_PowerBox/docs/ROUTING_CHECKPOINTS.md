# Rev.A prototype routing checkpoints

## Current status: F routed prototype, not production-ready

D/E were committed and pushed before F at `b42e73f52d1e8538079f944b93870e21eaef7fe8`.
F continues that exact copper. No earlier routing recipe or PCB generator was
rerun. Final evidence/limitations are in `ROUTING_F.md`; historical checkpoint
counts below describe their respective commits, not the current board.

| Checkpoint | Commit / result |
| --- | --- |
| A0 | `2b4bb5e9568fd3ed68e13147868de63d9654c6fa`, starting intermediate board |
| A | `4fed7b328fe3f52b9201013b1988913a9c660c6d`, battery/BMS/charger locals |
| B | `e28cc551cb03bcb958b2d4dc5e7dc65117e721fd`, primary bucks |
| C | `543b85faf09133c03d7adfbf37dc448e01271e6b`, isolation/clean locals |
| D | `24a4931`, interconnect; all non-ground networks connected |
| E | `b42e73f`, planes/thermal; zero unconnected |
| F | Commit containing this record: final cleanup, audits, derived files |

Branch remains `routing/r3-powerbox-reva`; main unchanged.

## Checkpoint C: independent pre-isolation and clean rails

Continued from B without removing prior copper. Independent ADS/INA input
filters are connected with paired feed vias. Their capacitors/FBs are on the
underside to fit adjacent to the SIP terminals without occupying module-body
courtyards. No common post-filter rail was introduced. Raw secondary splits,
INA positive/negative filtering and local ADM7150/TPS7A20 loops are routed.
U4 capacitors were placed by actual pin function; short local REF/REF_SENSE,
BYP/VREG and input/output links remain in the clean domain. R40 is on B.Cu.

523 segments / 162 vias. DRC: 283 unconnected, 83 dangling vias awaiting
planes, 175 silk warnings. No electrical/geometric errors; independent
barrier/domain audit and pin/mechanical invariants PASS. No copper objects in
x=121..124. Native C plots inspected. Ground planes/thermal/complete return
verification are deferred to E, not claimed complete. Continue D automatically.

## Checkpoint B: local primary converters

Continued from A without deleting any A copper. U1/U2 rotated locally so their
SW pins face the inductors; local bypass/output/feedback/BOOT parts compacted.
Explicit SW, VIN, output, VOS/FB and SS/PG-local connections added. C10 and U2
BOOT/feedback components are on the reverse side. No net/schematic changes.
VSYS_MAIN distribution and output-to-connectors/filters remain for C/D;
ground vias and thermal plane continuity remain for E. This is local converter
routing, not a powered or accepted board.

DRC: 319 unconnected, 57 dangling vias, 180 silk warnings; zero present
electrical/geometric errors. 420 track segments / 123 vias. Independent domain
audit and net/mechanical invariants PASS; all A corridor/mounting restrictions
retained. Native plots inspected, reports/R3_power_B_*.png. Continue C immediately.

## Checkpoint A continuation (supersedes A0 status below)

A0 `2b4bb5e9568fd3ed68e13147868de63d9654c6fa` was the starting board.
Added 2.5 mm inner BAT_NEG force path and symmetric three-via shunt force
fanouts. The sense traces originate within the shunt pads; no DGND sense via
exists before R95. Two named front-layer no-pour regions prevent pour bypass.
Local SRP/SRN differential filter/gauge paths, VC1/VC2 filters, VSS/PBI, CHG/DSG
EVM network and battery NTC paths are routed. Filtered-net test-point stubs and
I2C remain for D; ground force return closes with the planes at E.

BQ25798 local VAC, BATP, PROG, SDRV, TS and ILIM routes are added. Controls,
USB/input distribution and global SYS links follow in subsequent checkpoints.
Five A0 segments and the BTST2 via were replaced because their original
locations blocked legal PROG/BATP escapes. Other A0 copper is retained.
The local BAT pin escape uses a short In1.Cu island (54,50 to 57.5,53); this
is a documented local layer exception, NOT a split of the primary ground domain.
Review ground continuity around it after fill at E.

Unrouted local components were compacted; SW2 moved from (72,78) to (85,78)
because its original pads blocked the gauge fanout. J1-J13, H1-H6, U3/U6,
Q4/SW1, outline and stacking envelope have unchanged coordinates.
Some local filters are now on B.Cu; assembly/rework access remains required.
Cell sense lines use the lower quiet perimeter, not charger SW area; their
length and coupling still require the filled-return-path review. The Kelvin
pair is not yet claimed length matched or finally validated with planes.

DRC: 352 unconnected; 42 dangling ground vias pending planes; 181 silk warnings.
Zero present clearance, short, edge, hole, drill, annular or courtyard errors.
Independent domain audit: zero issues. Net/mechanical invariants PASS with the
explicit SW2 relocation. No filled planes, thermal or fabrication acceptance.
PCB minimum width is 0.13 mm as authorized; routes use 0.20 mm except the
0.15 mm BATP escape between bootstrap capacitor lands. Via rules unchanged.

L3 candidate checked against original Bourns PDF: SRP7028A-1R0M, 1 uH,
11 A Irms / 22 A Isat, 10 mOhm maximum DCR at 25 C. Package 7.3 x 6.6 mm,
2.8 mm nominal height, matches the existing family footprint. This closes the
package feasibility question; source/BOM freeze and switching/thermal budget
are still to be recorded before final F. Datasheet PDF page 1 visually inspected
using the PDF skill: https://www.bourns.com/data/global/pdfs/SRP7028A.pdf

Reproduction: at A0 run tools/continue_routing.py with KiCad Python. It loads
the A0 Git board, never the pre-routing baseline; it refuses later HEADs.
Subsequent stage scripts must use the committed A board, not rerun A.
Native plots: reports/R3_power_A_*.png. DRC: reports/routing_checkpoint_A_drc.json.
Proceed directly to B, then C/D/E/F; this is an intermediate checkpoint.

## Current status: A0 / PARTIAL / NOT FOR FABRICATION

Date: 2026-09-28. Baseline: `1ccbc857938f1d36dbe252c1533ed0361289e0a1`.
Work branch: `routing/r3-powerbox-reva`. Baseline reference:
`baseline/r3-powerbox-pre-routing-1ccbc85`.

The user has authorized prototype routing. Historical instructions saying
"do not route" are superseded by this authorization, not by hardware acceptance.
This checkpoint is **not completed checkpoint A**, and does not satisfy the
requested final zero-unconnected validation. Main is not replaced by this
incomplete board.

| Checkpoint | Actual state |
| --- | --- |
| A: charger + battery/BMS | Partial A0: local charger copper and positive battery path only |
| B: primary converters | Not started |
| C: isolation + clean rails | Placement/domain repair only; no routing |
| D: control/B2B | Not started |
| E: planes + thermal | Not started; some local vias reserved/connected on one layer |
| F: final cleanup | Not started |

## Baseline defects found before routing

Independent physical audit found eight pad bounding boxes inside x=121..124:
C35.2, C60.1/.2, C34.1/.2, FB3.1/.2 and C33.1. Also FB4, FB5 and C61
were on the primary side despite carrying isolated rails, while R105 and TP15
were on the isolated side despite carrying primary nets. The historical
pre-routing DRC summary was therefore insufficient evidence of isolation.

These components and nearby secondary filter passives were moved to the
correct electrical domain. All J1-J13 coordinates, H1-H6, U3/U6, SW1/SW2,
Q4, board outline and future-upper-board envelope are unchanged.
Electrical pin/net assignments are unchanged for every footprint.

The existing rule area is now named `ISOLATION_CORRIDOR`, with an additional
explicit disallow rule for tracks, vias, pads and zones. A disposable negative
control puts one track, one via and TP15 in the corridor: KiCad reports all
three as forbidden. No deliberately bad object is present in the actual PCB.
The cause of the older rule-area-only DRC missing the baseline pads has not
been isolated; do not rely on that old report. Retain both the independent
domain audit and the negative-control test.

## Copper actually implemented

- BQ25798 PMID/SYS 0.1 uF bypasses close to pins 29/25, with a local pin-27
  return. Bulk capacitor banks have explicit top-layer buses.
- VBUS local bypass/bulk and BAT bypass connections; REGN local bypass.
- SW1/SW2 use top necks, paired through vias under U8 and short In2.Cu links
  to L3. C74/C75 are on B.Cu, with separate bootstrap loops.
- Q2/Q3 source fanouts and shared drain copper. Positive battery and PACK_POS
  force paths use B.Cu, mostly 2.5 mm with 1.2 mm local fanouts.
- All 54 vias use 0.30 mm drill / 0.70 mm copper diameter. Bypass ground via
  drills are outside capacitor solder lands. No filled-via-in-pad process is
  assumed for those bypasses.
- No ground/power pours yet. No generic autorouter or automatic net-path
  search was used: `tools/route_reva.py` contains explicit pad/waypoint recipes.

The board currently contains **126 segments and 54 vias**. Do not interpret
these counts as completed rails: charger control, negative battery return,
shunt sensing, FET gates and many other connections are still open.

## Checks and evidence scope

- `reports/routing_checkpoint_A0_drc.json`: zero clearance, shorting,
  copper-to-edge, hole-clearance, hole-to-hole, drill-range, annular-width,
  internal-footprint-clearance or courtyard errors; **403 unconnected
  findings remain**. This is NOT DRC PASS for a completed board.
- Other findings: 35 dangling vias (pending planes/thermal completion),
  107 silk-over-copper, 93 silk-overlap and 11 silk-edge warnings.
- `reports/routing_checkpoint_A0_erc.json`: 0 errors / 412 existing generated
  symbol/grid warnings. Schematic/netlist were not redesigned.
- `reports/routing_domain_audit.json`: zero current pad/track domain or
  corridor findings. There are no copper zones to inspect yet.
- `reports/routing_baseline_domain_audit.json` preserves the original failure.
- `reports/routing_isolation_negative_control.json`: deliberate track/via/pad
  violations detected. Scratch board is under ignored `tmp/` only.
- `reports/routing_invariants.json`: all net assignments and fixed mechanics
  unchanged; DGND and GND_ISO remain distinct; four copper layers.

The DRC run is geometry/connectivity checking, not proof of current capacity,
transient stability, EMI, isolation certification or manufacturing readiness.
Schematic/PCB parity warnings from the baseline generator are still an open
separate issue; this report does not waive them.

## Thermal and return-path review

TI's BQ25798 layout example explicitly uses inner-layer switch links and
bottom bootstrap capacitors. This is the reason for the local layer choice;
it does not turn In2.Cu into a general switch-node routing layer.

For a first-order 35 um copper estimate, a 40 mm long, 2.5 mm wide trace is
about 8 mOhm at 20 C (about 0.20 W at 5 A). This is a resistance estimate,
NOT an IPC thermal/current qualification. Actual finished copper weight,
neck lengths, connectors, vias and hot resistance still require review.

Local ground connections exist, but **complete return-path review is open**
because the force return, ground planes and Kelvin routes are not complete.
The Q2/Q3 shared-drain vias do not yet provide a validated heat-spreading
network. Do not power or fabricate this partial layout.

## Exact next work, preserving the requested order

1. Finish checkpoint A: BAT_NEG_RAW force return/R93; independent pad-origin
   SRP/SRN Kelvin pair; VC1/VC2 and VSS/PBI/NTC local loops; CHG/DSG gate
   networks; remaining charger local connections. Keep sense copper separate
   from force copper and prevent future DGND pours from bypassing the Kelvin
   pickup. A two-terminal net name alone does not establish Kelvin topology.
2. Close L3 exact MPN versus the existing Bourns SRP7028A land pattern before
   accepting the final switching layout. The baseline value remains
   `1.0uH >=6A / MPN TBD`; no replacement was silently selected.
3. DRC and visual return-loop review, then checkpoint A commit.
4. Continue the user's priority order: USB/PD, system path, primary converters,
   independent pre-isolation branches, secondary/LDO rails, control and B2B.
5. Only then planes/thermal copper, filled-zone isolation audit, complete
   connectivity and final silkscreen cleanup.

PD/BMS programming, TPS54302 operation at 6 V, RS3 light-load behavior and
thermal/charging tests remain prototype bench validations, not silently
accepted results. No production Gerbers have been made.

## Reproduction

Use KiCad 10's bundled Python for `route_reva.py --from-baseline`,
`audit_routing.py`, `verify_routing_invariants.py`, and
`test_isolation_rule.py`. The explicit `--from-baseline` option overwrites
only this branch's PCB with the recorded recipe; do not use it over new manual
work unless that work has first been committed and included in the recipe.
`generate_preliminary_placement.py` now refuses to overwrite a board containing
tracks/vias. Native plots are made with `export_routing_views.py` and are
clearly labelled A0 / incomplete.

## Sources reviewed

- [TI BQ25798 Rev.C](https://www.ti.com/lit/ds/symlink/bq25798.pdf),
  section 8.4, figure 8-21, RQM0029A land-pattern drawing. The PDF skill was
  used for visual inspection of the original layout and package drawings.
- [KiCad 10 rule documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html),
  `intersectsArea` and `disallow` constraints.
