# R3 PowerBox Rev.A PROTOTYPE manufacturing release

Date: 2026-10-07. Branch: fix/r3-powerbox-reva-review1.
Final manufacturing source commit: `0d6da576168b8284664dffa865b99ebe71e1d3c4`.
PCB SHA256: `b97675a2f1d249f53b645572c5bd6f37c896afa56bb287ec21101c447e56bb48`.
All manufacturing files were generated from the same final source commit.
Release/report commit is subsequent and does not modify the source PCB.

## Validation

{
  "DRC_errors": 0,
  "DRC_warnings": 42,
  "unconnected": 0,
  "parity": 0,
  "ERC_errors": 0,
  "ERC_warnings": 423,
  "release_review1_verification.json": "PASS",
  "review1_current_paths.json": "PASS",
  "review1_abs_max.json": "PASS",
  "review1_polarity.json": "PASS",
  "orientation_physical_audit.json": "PASS",
  "orientation_export_audit.json": "PASS",
  "orientation_bottom_audit.json": "PASS"
}

Warnings: 42 library-copy footprint mismatches; 423 ERC generator/library
warnings (212 lib_symbol_mismatch, 211 endpoint_off_grid). Individually accounted
in reports/release_review1_verification.json, no suppressed electrical errors.
Current paths, Kelvin preservation, mounting/isolation and negative controls PASS.
Orientation PASS means CAD physical mapping/native CPL parity. JLC component
library visual acceptance remains manual, not a claim of factory qualification.
D4: machine verified / visual JLC confirmation pending.

## Assembly

A TOP ONLY: 91 intended factory positions. B BOTH SIDES: 141 (91 Top + 50 Bottom).
Five PCB / two PCBA / three bare is the intended ordering configuration, not an order.
Manual common: C1, F1, J1, J10, J11, J2, J3, J4, J8, J9, U3, U6.
DNP: J12, J13, J5, J6, R107, R108, U11. PCB test points/mounting holes excluded as PCB features.
A additionally requires all 50 Bottom parts manually; B includes them as candidates.
C1 — MANUAL_POPULATE, NOT DNP — Panasonic EEE-FK1E470P / LCSC C178545.
No automatic substitutions. Missing MPN/LCSC is UNRESOLVED, not a generic purchase
approval. All factory LCSC identifiers remain unresolved in this source state;
resolve exact matches before authorizing placement. Q1/Q4 use the owner-selected
AO4407A assembly override; logical pad1 is Gate, physical package pin1 is Source.

## Required JLC review before order

J7 USB-C: verify and manually align component body to PCB pads/edge in JLC
Component Placements before order. Do not change PCB geometry solely to compensate
JLC library centroid. Visually align contact row, mechanical tabs and PCB edge;
small manual X/Y correction is expected/allowed by owner.
Check every polarized component and both sides against physical pins/polarity,
not model text. Verify layer order F.Cu/In1.Cu/In2.Cu/B.Cu, 160x80mm, 1.6mm,
1oz copper target, manufacturing stackup and 2 assembled + 3 bare quantities.
Drill maps/reference native position CSV are not factory CPL uploads.
Resolve UNRESOLVED sourcing without substitutions and preserve manual/DNP list.

## Prototype limits

Powered, thermal, effective MLCC capacitance, PPTC derating and EMI validation
remain ahead. First STUSB4500 NVM programming power: 5V-only/non-PD. INA light-load
behavior remains a bench check. This is NOT production-qualified hardware.
No JLC visit/order/payment occurred during release.

## File hashes (SHA256)

| File | SHA256 |
|---|---|
| .gitattributes | `705fd4d6451a31d36b3df7de96f83f30ac976c9b4a6d1e51671d8e2f33e2d0da` |
| assembly_file_validation.json | `cbbe9116865c2a4e56e380bfbe49fe44df45c4c07ceb6b5193a7d52153d7863c` |
| assembly_source.json | `b52b5ae80990bf05819b88c73bdc21ac11030b5c68c66a3a3f811bcb0d311285` |
| fabrication/drill_report.txt | `cedcb1bd97bfbacbd65bdc6a1ccb03d7721ad13cd39ae34c6a9eb0edf0c7d1fd` |
| fabrication/R3_power-B_Cu.gbl | `99a9fdb1dc7c9c68f9daa5a726dd5c2dc1cd1d52b885076bf17abb13da705647` |
| fabrication/R3_power-B_Mask.gbs | `c6f0a652236fe3e542beb9e2210b06ce4f5b76ac4db0009dbe52908bb13a4ba6` |
| fabrication/R3_power-B_Silkscreen.gbo | `b229d644bc9934a788569ac5b1c58287a80591c9fe97d43823e9b7968d6b017d` |
| fabrication/R3_power-Edge_Cuts.gm1 | `a5672409cf47bb660a3d785cfb4cbe91fe9e57b09ad491138a3b312b9180d8ec` |
| fabrication/R3_power-F_Cu.gtl | `7e74f80f139bbe645fdc81ad5dc08f25f4484e546255112fb44d470ef2cb42b9` |
| fabrication/R3_power-F_Mask.gts | `c95ce9068803750ba2d4bb384746f70acd6c7a8cca932b546cb3e34116696151` |
| fabrication/R3_power-F_Silkscreen.gto | `527b4e142da8436a3a091d885907202f739fe529905aeacbece350c3bae68eee` |
| fabrication/R3_power-In1_Cu.g1 | `9e44096198deeca6184759b198277f26a458c6c55d94f14f80a9f3575f593a78` |
| fabrication/R3_power-In2_Cu.g2 | `349f1d9cf0531d296a26108b74bf28e3be7eb577c2c488b92ebf1b60e8ce69f2` |
| fabrication/R3_power-job.gbrjob | `45133e61abeb5349e320d47d4279f3930489ad17446bd1bf35eb23deeccbab95` |
| fabrication/R3_power-NPTH-drl_map.svg | `fda71954a1bbe4a8b78879dfc06e1f9f80ccfce4b042c32b28dfa3f7e3247407` |
| fabrication/R3_power-NPTH.drl | `de54244ba865e2c3c1e593c3fb8eb6961e941cd13bc3ac068de44c625d2e2bda` |
| fabrication/R3_power-PTH-drl_map.svg | `851d8a5e2c0e3a84116af14d277e38c01549572e31975fadf9486ed499833547` |
| fabrication/R3_power-PTH.drl | `a4ab83ac167022cc7f4c54012711956e517bc35cc6c47dd303484e1dd2b67ddc` |
| native_positions_reference.csv | `045b4e652ff52e843319639beafe01f029f79900f65ca5418b803cb2647fccc5` |
| R3_PowerBox_RevA_PROTOTYPE_0d6da57_Gerbers.zip | `0d0960112404bd0991ae1a76a58a08b57d0a459e3da870220145117ef693db39` |
| R3_RevA_A_TOP_BOM.xlsx | `3ea3a2a555d4990d934a0d110adb11a0c1367ee60668cf16a50a34951b99fc24` |
| R3_RevA_A_TOP_CPL.xlsx | `d29c08910df78f63cb9c166b76dc31b7a40344df6e7910fa3f92bf7665f12cdf` |
| R3_RevA_B_BOTH_BOM.xlsx | `ce6088ad6e84e49abb4a3c2b36dc5634a3b6c1b200c61ce8382af2218da0fd5a` |
| R3_RevA_B_BOTH_CPL.xlsx | `7b2b794cf7a90e7739e79f31f01c3af26c8b5cee6dddec87b0dea03c2111c60d` |
| R3_RevA_MANUAL_DNP_BOM.xlsx | `3097a851b0642c218b37bec1803885e513c1d97524168fb3c4ddcbd414a20648` |
