# R1-S3 and R3 ecosystem control

PANEL v0.24 implementation, 2026-09-09. Saved trust, boot reconnect, idle RTC
correction, selected-device control and static CSV v2 provenance are implemented
in the source and covered by host checks. A **[bounded two-board physical bench](ECOSYSTEM_ACCEPTANCE_2026-09-09.md)
passed** for saved permissions, RTC correction, selected control and recovery.
The [earlier S1 bench](BLE_ACCEPTANCE_2026-09-09.md) tested
the preceding volatile-pairing transport; it does not qualify v0.24 enrollment
or control. [Ukrainian instructions](uk/ECOSYSTEM_CONTROL.md) ·
[BLE transport](BLE_LINK.md) · [time architecture](ECOSYSTEM_TIME_SYNC.md).

## Enroll once, choose the permission explicitly

1. Stop R1-S3 recording and wait for file closure. On R3, use its USB console:
   `ble?` checks the service, `ble on` enables it, and `ble pair` opens a
   120-second enrollment window and displays a temporary six-digit PIN.
2. In the R1-S3 **BLE · R3** tab, scan, select the intended R3, enter that PIN
   and connect. Wait for authenticated connection. Discovery names alone are
   not trusted identities.
3. Save the association explicitly. Leave remote recording permission unchecked
   for **time only**; check it before saving to allow that R3 to START/STOP
   R1-S3 recording. Connecting without Save does not enroll an authority for
   subsequent R1 boots.
4. Check the saved association and permission status. On later boots R1-S3
   retries its saved R3 with bounded backoff, authenticates and subscribes again.
   R3 may start first or later. No PIN is stored or automatically replayed.

These commands use the existing owner envelope `BOOT REV BLE <argument>`, with
the current R1 boot and settings revision. The panel supplies the envelope.
All BLE policy/lifecycle actions are available only between recordings.

| BLE argument | Effect |
|---|---|
| `SCAN` | Discover nearby R3 devices; no automatic enrollment. |
| `CONNECT <MAC> <PIN>` | Attempt the explicitly selected authenticated connection. |
| `SAVE` or `SAVE 0` | Save the authenticated, bonded association with time-only permission. |
| `SAVE 1` | Save that association and explicitly allow remote recording control. |
| `ON` | Resume retries to the saved R3 without entering a PIN. Requires a saved association. |
| `OFF` | Disconnect and stop retries for this R1 boot. Keep the saved association; boot reconnect resumes after restart. |
| `FORGET` | Remove R1's saved association and bond. A new explicit enrollment is required. |

BLE Save is separate from **Save settings to EEPROM**. Measurement config v1 and
its external EEPROM slots are unchanged. Authenticated bond keys and a versioned
association policy live separately in NVS, never in exported settings or files.
An unsupported policy does not silently connect: Forget and enroll again.
If trust was erased or a board replaced, revoke stale enrollment on R3 as well
and repeat enrollment. A lost bond never falls back to an old PIN.

## What boot time correction means

R3's RV3028 is the owner-selected authority; R1's DS3231 remains its offline
calendar. After a trusted connection, R1 requests fresh valid R3 time and the
existing I2C owner applies and reads back the RTC while idle. Source read age is
limited to 1,500 ms, request roundtrip to 1,000,000 us and receive-to-application
delay to 1,000,000 us. Source identity, boot, clock revision and connection epoch
are rechecked before application. These limits are **workflow freshness gates,
not a measured UTC accuracy bound**.

Correction waits throughout STARTING, recording, STOPPING and file closure. It
then requests new evidence. R3 reboot or clock-revision change invalidates the
previous current-source confirmation. Invalid R3 UTC is never copied. Manual
RTC setting clears the R3 correction claim. No per-beacon RTC or EEPROM writes
occur; sample deadlines, monotonic timestamps and energy integration stay local.

`rtc_valid` means a usable calendar. `rtc_synced` means the owner confirmed a
coarse RTC correction for the current R3 boot/revision. Neither establishes
precise alignment between samples. The beacon diagnostics retain
`synchronized: false`, `coarse: true`, `uncertainty_us: null`.

## Use R3 as the control panel

Open **`/ecosystem` on the R3 web interface**, using the same R3 address as its
main panel. The page lists up to three enrolled BLE nodes, with selection boxes,
connection/authentication/freshness, RTC state and recording/session results.
It currently controls compatible downstream nodes. **R3's own STM32 recorder
is not yet an entry in this group control; the CAN adapter is not implemented.**

- Select the intended devices. START requires every selected device to be
  connected, authenticated, fresh, permitted for remote control, ready and
  corrected from the current R3 clock. Any failed preflight blocks the whole
  dispatch before queueing. A failure after dispatch can still yield partial
  success; this is not an atomic or simultaneous start.
- START creates a group ID and independent per-device requests/sessions. Queued
  and accepted commands are not proof of recording. Wait for each device's
  actual **recording** state.
- STOP targets the selected device boot and current nonzero session, including
  a locally started session when remote permission is enabled. Local STOP is
  still available, including during STARTING. The SD owner drains buffers and
  verifies closure before reporting **closed**; an error remains an error.
- Link loss and unanswered requests become **unknown**, not stopped or closed.
  Recording continues autonomously. The page does not replay START on reconnect
  or reload, and does not automatically STOP successful peers after a partial
  group failure. Reconcile actual state before another deliberate action.
- Forget/revoke removes that R3 registry association; it does not stop logging.
  R1's local association must also be forgotten to enroll afresh.

Protocol duplicate handling is scoped to the same request ID. A later user
action is a new request, revalidated against the actual session. Old STOP packets
cannot target a new session. Boot changes invalidate old selections.

## Files and qualification

PANEL v0.24 starts native recordings as [CSV schema 2](FILE_FORMAT_V2.md), for
both local and remote Start. Each part carries frozen device/boot/recording
identity, nullable group/coordinator identity and nullable R3 RTC correction
evidence. Local recording can use R3-corrected time without being in a group.
A known calendar can have unknown uncertainty (`null`); this never means zero
error. Rotation repeats the complete evidence. Both current readers retain
schema 1 support; older v1-only readers must reject schema 2 explicitly.

This is static provenance, not an offset/drift fit, raw clock-event stream or
precise multi-file alignment. Those remain S2/S3 work. No CAN compatibility or
three-node physical acceptance is implied.

Host checks cover real C++ serialization and both readers, malformed/stale
provenance, enrollment controls, STARTING Stop, target-parser rejection and UI
pending/remote/unknown outcomes. The [v0.24 bench report](ECOSYSTEM_ACCEPTANCE_2026-09-09.md)
records saved time-only permission with RTC correction and Start denial, explicit
remote permission with actual selected Start/Stop, R3 reboot during uninterrupted
R1 recording, deferred correction until closure, and autonomous R1 reboot while
R3 BLE was unavailable followed by automatic recovery. Verified 50 Hz and
reboot-during-recording files contain 549 and 722 rows without gaps.

This does not qualify three physical nodes, invalid source RTC, hard power cuts,
long-duration operation or precise clock alignment. CAN and R3-local STM32 control
are not implemented. The acceptance report is authoritative for the separate
300 Hz run's download/integrity result; recording counters alone do not prove
file integrity or signal quality. Runtime settings were restored to saved
generation 3 without an EEPROM Save. See the [migration journal](R1_MIGRATION.md).
