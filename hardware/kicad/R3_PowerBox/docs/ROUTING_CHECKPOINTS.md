# Rev.A prototype routing checkpoints

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
