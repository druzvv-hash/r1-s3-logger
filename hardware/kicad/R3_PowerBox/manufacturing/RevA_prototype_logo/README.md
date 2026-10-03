# R3 PowerBox Rev.A — prototype fabrication export

2026-10-03. Export authorized by owner; NOT production/hardware acceptance.
Source: review branch fix/r3-powerbox-reva-review1, pre-logo commit 5d3da52.
Board SHA256: f1cc618b274fae46e68432f66f089f505c7378a0eb8d68889083c54bba1eaa61

160 x 80 mm nominal, CAD thickness 1.6 mm, four copper layers in order:
F.Cu / In1.Cu / In2.Cu / B.Cu. Material, dielectric stack, copper weight,
finish and fabrication tolerances must be confirmed with the fabricator.
Nine Gerber layers: four copper, two mask, two silk, Edge.Cuts.
Excellon metric absolute coordinates, separate plated/non-plated files;
plated slots included. SVG drill maps and drill report are reference only.
Use the .gbrjob and layer names; do not mistake drill maps for copper layers.
No paste/stencil or assembly procurement approval is included.

Front silk contains a simplified monochrome Garage Logic Lab logo.
Electrical routing, pads, fills, mechanics and isolation are unchanged.
Fresh DRC: zero errors/unconnected/parity, 41 existing footprint-library warnings.

OPEN BEFORE BUILD/POWER: exact MLCC effective-capacitance qualification,
PPTC hot-current limits, factory PD NVM (FIRST POWER 5V ONLY / NON-PD),
INA converter light-load behavior, thermal/noise/switching bench validation.
See docs/REVIEW1_FIXES.md in the source repository. No order has been placed.
