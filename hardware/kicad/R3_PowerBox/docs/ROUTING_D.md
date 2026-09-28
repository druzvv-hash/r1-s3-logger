# Checkpoint D — interconnect, incomplete ground system

2026-09-28. Continues C, not the pre-routing baseline. Explicit per-net
waypoint recipes in `tools/route_interconnect.py`; no generic autorouter.

All non-ground networks now connected. KiCad reports 112 unconnected ground
findings and 246 warnings. No error-severity findings. No filled planes yet.
Do not fabricate. E must connect and inspect ground returns; F must regenerate
derived schematic/BOM/PDF and repeat electrical/mechanical checks.

## Routing-driven local corrections

- J7 previously faced inward. Official GCT USB4105 drawing puts board/mating
  edge at footprint local Y=+3.675 mm. Anchor is now (23.675,33), 270 degrees,
  facing x=20 board edge. J12/J13, six M3 holes and isolation modules unchanged.
  Source: https://gct.co/files/drawings/usb4105.pdf
- D4 is directly below CC routes. TP31/32 are inline 0.6 mm no-paste pads.
- TP27/28 are 1 mm bottom-side pads on filtered Kelvin endpoints, not long
  branches to remote through-hole test terminals. Force and Kelvin routing
  from A remain unchanged. They are probe pads, not hook terminals.
- F3, D1/FB1, service bypass, mux bypass, pullups and several TPs moved locally
  to enable legal power/control escapes. Recipe records exact coordinates.
  Functional zones retained. TP6/16 now beside their own primary feeds.
- C104 moved locally; U8 ground pin-10/pin-13 fanouts, U9 NTC fanout and C23/24
  ground fanouts reworked to open control escape paths. No schematic net changes.

## Layer/return review required at E/F

Some service/system input and low-current status/sense traces use In1.Cu.
This deviates from an unbroken full-plane ideal, and must not be accepted merely
because DRC passes. Plane continuity, local switching return loops and stitched
same-domain bypass paths require filled-copper inspection. No quiet net was
intentionally routed under the L3 SW lands; inspect all layers at F.

STAT remains raw hardware LED drive plus Schottky-separated 3.3 V logic.
POWER remains Q4 gate-control only; QON remains a separate service input.
I2C, J12/J13 rails/status, USB shielding, NTC and all signal TPs are connected.
Mounting copper audit and pad/track isolation-domain audit report zero findings.
Filled zones are NOT covered by the D pad/track audit.
