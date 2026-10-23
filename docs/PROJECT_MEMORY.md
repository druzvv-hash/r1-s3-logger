## 2026-10-23 — PowerBox now has its own R3 repository

Canonical project: [GLL R3 PowerBox](https://github.com/druzvv-hash/r3-powerbox),
branch **main**, local **C:/Projects/r3-powerbox**. Its README distinguishes Rev.A,
Rev.B candidate and user-reported physical checks. Existing hardware files were
copied byte-for-byte; PowerBox history was filtered with an original/new commit
map. Previously local RevB/manufacturing evidence is now tracked privately.
No circuit change, new hardware test or manufacturing approval is implied.
The old r3-powerbox-routing worktree and R1 branch remain historical references;
do not start new PowerBox development there. This supersedes older location and
local-only status below. See the new repository's docs/MIGRATION_2026-10-23.md.

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
See [dated evidence and limitations](POWERBOX_REVA_USER_CHECKS_2026-10-22.md).
This supersedes any reading of the older audit as saying no physical 12-V
operation was ever reported; its machine-captured 5-V test scope stays unchanged.

# R3 PowerBox Rev.A / Rev.B candidate — current evidence map

Updated 2026-10-23. Memory branch: `fix/r3-powerbox-reva-review1`; original source anchor
`9ad492a7febef3f72f6920bc6350b5c1a50d6bda`. Documentation commits do not change the firmware version.

## Current state / evidence boundary

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


## Read next

- [Agent rules](../AGENTS.md)
- [Current notes](../NOTES.md)
- [Work reports](../WORK_REPORT.md)
- [hardware/kicad/R3_PowerBox/docs/REVIEW1_FIXES.md](../hardware/kicad/R3_PowerBox/docs/REVIEW1_FIXES.md)
- [hardware/kicad/R3_PowerBox/docs/STUSB4500_PD_CONFIG.md](../hardware/kicad/R3_PowerBox/docs/STUSB4500_PD_CONFIG.md)
- [GitHub branch memory](https://github.com/druzvv-hash/r1-s3-logger/blob/fix/r3-powerbox-reva-review1/NOTES.md)

## Open issues / next session

Existing manufacturing/CAD files remain dirty/untracked. This pass commits reviewed memory only; factory source, order status and physical charger/BMS acceptance require separate work.

Check the actual HEAD and dirty state, then read only the relevant detailed
reports. File mtime is not a validation date. A historical PASS is scoped to its
reported source/device/test; a documentation update adds no hardware acceptance.
No automatic access to prior chats or two-way memory synchronization is installed.

## PowerBox / PD evidence locations

PowerBox historical source reports are in the canonical local worktree
C:/Projects/r3-powerbox-routing/hardware/kicad/R3_PowerBox/docs/, especially
PACKAGE_FIT_AUDIT_2026-10-08.md. The local RevB candidate README/verification is
under manufacturing/RevB_PACKAGE_FIX_2026-10-08/. These untracked evidence files
are not guaranteed to exist on GitHub; do not treat a local path as a remote link.
Private Oct 22 REPORT-5V9V12V.uk.txt lives in the preserved GLL-PD-Programmer
package under the 2026-10-22 Codex outputs, and the verified NAS snapshot
2026-10-23_05-28-21. It contains device dumps and must not be copied to public Git.
PD 1.2.0 public-to-authorized-users evidence is docs/VALIDATION.md in the private
GLL-PD-Programmer repository at tag v1.2.0. Its tag/source/binary remain unchanged.
