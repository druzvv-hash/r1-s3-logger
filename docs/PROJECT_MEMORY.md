# R1-S3 Logger — current evidence map

Updated 2026-10-23. Memory branch: `main`; original source anchor
`9f22a65b7efd075ebadc8dae47e0aeff62a2cf8d`. Documentation commits do not change the firmware version.

## Current state / evidence boundary

Pre-memory HEAD 9f22a65b7efd075ebadc8dae47e0aeff62a2cf8d includes the preserved averaging/UI changes. Earlier Oct 23 production build and averaging/panel/chart host tests passed; not newly deployed. Sept 24 deployment remains historical evidence. R1 main retains the old PowerBox baseline; active hardware work is the sibling r3-powerbox-routing worktree, not this main checkout. PowerBox has progressed beyond the September pre-routing baseline. Rev.A
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
- [docs/R1_S3_PLAN.md](../docs/R1_S3_PLAN.md)
- [docs/OTA.md](../docs/OTA.md)
- [GitHub branch memory](https://github.com/druzvv-hash/r1-s3-logger/blob/main/NOTES.md)

## Open issues / next session

Unrelated .gitignore/hardware/KiCad changes remain uncommitted. Keep UART failure cause unresolved; loaded UART/noise/calibration and power-loss OTA acceptance are not inferred.

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
