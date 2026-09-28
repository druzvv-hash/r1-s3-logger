# F: final routed Rev.A prototype checkpoint

Evidence level: IMPLEMENTED / HOST CHECKED. Not bench tested, not production-ready.
Date: 2026-09-28. Branch: `routing/r3-powerbox-reva`; main unchanged.

## Preservation and exact changes

D/E were pushed at `b42e73f52d1e8538079f944b93870e21eaef7fe8` before F.
F loads the current PCB only. It does not regenerate a PCB from a schematic,
baseline or earlier checkpoint. Zone/keepout boundaries, all mechanical/B2B
coordinates and all E placements except C75 remain unchanged.

- Removed five redundant one-layer vias (+5V_INA, PACK_POS, +3V3_D, SCL,
  SDA) and one 4 mm dangling POWER_CTRL tail. Connectivity remains complete.
- Moved conflicting footprint legends to fabrication layers; retained readable
  board-level power, battery, domain, CHG/RUN, connector and pin-1 markings.
  Edge connector references formerly outside the PCB are now on-board.
- Found a real cross-layer projection defect not detected by ordinary DRC:
  SW2's B.Cu bootstrap branch passed beneath I2C/TS fanout. C75 moved from
  B.Cu (54,53.8) to (54.8,51.8); its two bootstrap branches were shortened/
  rerouted, and adjacent PROG via moved from (54.4,52.8) to (54.4,53.1).
  This is the only F component relocation. All other E copper is retained
  except the six redundant objects. Exact UUID changes are in the audit.
- No selected I2C/CC/BMS-cell/BMS-current/NTC trace projects across any of the
  four SW-track networks after this fix. This is a track-projection test,
  not a complete 3D magnetic/capacitive coupling simulation.
- Fixed missing library nicknames/datasheet fields in the PCB without replacing
  any footprint geometry. Marked six mounting holes PCB-only. Schematic/PCB
  exact pin/net parity passes. Fixed SKiDL's omitted KiCad DNP flags for U11,
  J5/J6/J12/J13 in the editable drawing pipeline, preserving intended assembly.
- Regenerated schematic, PDF, BOM and ERC. TP27/28 are bottom 1 mm sense probe
  pads; TP31/32 are inline 0.6 mm no-paste CC pads. No long CC or Kelvin TP stub.

## Electrical/geometry acceptance

1343 segments / 337 vias / 14 filled zones / 199 footprints.
DRC: 0 errors, 0 unconnected, 0 schematic parity findings. No clearance,
short, copper-edge, hole-to-copper, drill, annular, courtyard, silk or dangling
findings. 43 `lib_footprint_mismatch` warnings remain visible: the embedded PCB
copies contain reviewed routing/land-pattern and legend edits relative to their
named library sources. Do not bulk-update footprints from the stock libraries.
These are explicit prototype library-synchronization exceptions, not electrical
clearance waivers. A future library release should capture board-specific copies.
Inherited project checks still ignored (unchanged in F): missing courtyard,
track endpoint not centered on via, tuning-profile geometry, footprint filter
match and footprint component-type match. Therefore "0 errors" means the
configured electrical/geometric rules, not every optional KiCad diagnostic.
ERC: 0 errors, 412 generator-origin warnings (206 embedded symbol mismatch,
206 off-grid label endpoint). No newly waived electrical rule.

Actual filled polygons and all conductive pad/track/via envelopes are checked
against x=121..124 mm and six 8 mm mounting squares: zero intrusions.
DGND and GND_ISO remain distinct. Negative-control track/via/pad test detects
three isolation violations on a scratch board only.

## Kelvin and return review

R93 has separate 0.20 mm F.Cu pickups rooted inside each shunt pad, and three
force vias on each terminal. No-pour rules prevent a front DGND pour from
bypassing the SRN pickup before R95. Force copper is separate from filtered
sense routing. C94/U9 sense paths are below the charger region; TP27/28 are
local filtered-node probes. Aggregate filtered-net lengths including branches:
SRP 16.121 mm, SRN 19.697 mm. They are **not a length-matched differential pair**;
these low-bandwidth current-sense nets require offset/noise checks on hardware.

Same-domain ground fills/stitches provide interlayer returns. In1 is not an
ideal uninterrupted single polygon: documented low-current routing creates
three primary fill outlines connected through other layers/stitches. No floating
copper islands retained. The secondary B.Cu void near the output fanout has
same-domain return on other layers; do not claim an uninterrupted L4 plane.
Visual return review and DRC cannot establish conducted/radiated EMI performance.

## Thermal and magnetics

Preserved Q2/Q3 common-drain spread of about 33 mm2 on each outer layer and
three interlayer vias. Q4 has separate source/drain outer-layer copper and
five local thermal/current vias. U1, U7, U8 local return/cap-bank vias and
ADM7150 two additional ground/thermal vias remain. U2 has no exposed pad;
existing ground fanout and domain copper provide heat spreading. All thermal
copper stays within its electrical domain.

R93 10 mOhm dissipates 10/109/250 mW at 1/3.3/5 A. Selected Q2/Q3 pair
9.6 mOhm at datasheet 4.5 V gate condition gives 9.6/104.5/240 mW at those
currents before hot-RDS derating. Q4 15 mOhm planning resistance gives
15/60/163 mW and 15/30/49.5 mV at 1/2/3.3 A. These are component estimates,
not measured junction temperatures; enclosure and hot copper remain bench gates.

L3 now fixed to **Bourns SRP7028A-1R0M**: 1 uH +/-20%, 11 A Irms,
22 A Isat, maximum 10 mOhm DCR at 25 C; existing 7.3 x 6.6 x 2.8 mm family
footprint. R75=6.04 kOhm sets 2S/1.5 MHz at POR. TI Rev.C 8.2.2.2 requires
1 uH at 1.5 MHz and 2.2 uH at 750 kHz: firmware MUST retain PWM_FREQ=0.
At 12 V to 6 V, 0.8 uH tolerance corner and nominal 1.5 MHz, ideal buck
ripple is about 2.5 App. Even a conservative 5 A average yields about
6.25 A peak / 5.05 A RMS, below the component ratings. This does not permit
exceeding the existing USB/input/charger power budget. 5 A DC winding loss is
0.25 W at 25 C DCR, about 0.35 W with a 1.4 hot-resistance planning factor;
core loss and temperature require measurement. Frequency tolerance adds margin
requirements but is nowhere near the 22 A saturation rating in this budget.

Sources: [TI BQ25798 Rev.C](https://www.ti.com/lit/ds/symlink/bq25798.pdf),
[Bourns SRP7028A](https://www.bourns.com/data/global/pdfs/SRP7028A.pdf).
Original PDFs were read; no distributor/module schematic used as authority.

## Open validation, not hidden routing completion claims

- RS3 dual-output light-load balance/ripple/preload decision remains a bench gate.
- TPS54302 regulation/startup at 6 V under intended load and transients.
- Program/read back BQ28Z610 chemistry/protection and STUSB4500 PDOs; validate
  safe charger limits at unknown/5/9/12 V, reset and watchdog recovery.
- Battery absent startup, charge while main OFF, source removal/supplement,
  BMS fault/recovery, Kelvin offset/noise, thermal rise and EMI.
- Final fabricator stackup/copper weight and thermal assessment, physical
  connector/latch access, enclosure and 15 mm stack test fit.
- U11 remains a DNP footprint-space reservation, NOT independent OV protection.
- Export/migrate modified embedded footprints before a library/production release.

No PCB/BOM order or production Gerbers. Native views are `reports/R3_power_F_*`.
Final commit is the commit containing this record; Git log is authoritative.
