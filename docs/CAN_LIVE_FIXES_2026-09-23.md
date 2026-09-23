# Shared CAN workspace deployment — 2026-09-23

R1 shared CAN assets regenerated from ../GLL CANBox/workspace. Wi-Fi256 batch
negotiation, live-tail start, reconnect guard, endpoint persistence and visible
connection/time state. Token stays memory-only. Existing averaging owner changes
were preserved in the build; this commit stages only CAN assets and this report.

HOST TESTED:88 tests and esp32-s3-usb build PASS. BENCH TESTED: HTTP OTA app0→app1,
new boot/READY and unchanged config/generation. Version0.37-display-average-dev.
Real R1 /can displays122722 records/0 live-ring losses; MCP hardware overflow
remains separately unresolved. Reload keeps endpoint and clears token.
R1 remains connected to R3; CANBox UTC invalid because R3 service adapter absent.
No clock source/role reassignment, SD recording or vehicle test.

Full evidence/deployment boundaries and private log locations:
[CANBox report](../../GLL%20CANBox/docs/CAN_LIVE_FIXES_2026-09-23.md).
