# R3 / R1-S3 BLE link — S1

Implementation contract, 2026-09-09. **Hardware acceptance is pending.**
This document describes the implemented transport and its limits, not a measured
clock synchronization result. [Architecture](ECOSYSTEM_TIME_SYNC.md) ·
[Ukrainian owner instructions](uk/BLE_LINK.md).

R3 is a Bluetooth LE GATT peripheral/server. R1-S3 is a central/client that
selects one R3 and receives its coarse time-metronome observations. Both builds
pin `h2zero/NimBLE-Arduino@1.4.3`. R3 starts advertising on boot; R1-S3 starts
with BLE selection disabled. Existing R3 UART `$TMB` transmission is retained.

## Connecting the instruments

1. Open the R3 USB console and send `ble?` to inspect status. `ble on` enables
   advertising if it was disabled. `ble pair` returns the current device address
   and six-digit PIN through this console only; ordinary `ble?` excludes the PIN.
2. Stop any R1-S3 recording and wait for the file to close. In its panel, open
   **BLE · R3**, press **Знайти R3**, and select the R3 address. A manual address
   can also be entered. Discovery is a five-second scan, capped at six devices.
3. Enter the current R3 PIN and press **Підключити**. The PIN field clears on
   submission. Wait for authenticated connection and fresh beacon status.
4. **Вимкнути BLE** cancels the selected connection and automatic retries.
   Starting another scan also disconnects the current peer and clears the
   retained PIN. Discovery never chooses a new peer automatically.

These panel actions use the existing owner command envelope with current
R1 boot and settings revision: verb `BLE`, argument `SCAN`, `CONNECT <address>
<six-digit-PIN>`, or `OFF`. They are STOP-only; configuration races are rejected
by the owner. UI callbacks never operate the radio directly.

Selection and PIN are **volatile**, not EEPROM or browser settings. During the
same R1/R3 boot pair, unexpected link loss retries the selected peer with delays
of 1, 2, 4 and then at most 8 seconds. Each new link authenticates and subscribes
again. R3 reboot creates a new boot ID and PIN: obtain it with `ble pair`, select
R3 and connect again. R1 reboot requires selection and PIN entry again.

Keep pairing output, actual device addresses, local panel access tokens and
other bench identifiers out of public logs. No literal bench values belong in
this document or test fixtures.

## Authentication and storage

The pair uses LE Secure Connections with passkey authentication, encryption and
a 16-byte encryption key. Build flags prohibit legacy pairing and persistent
NimBLE storage in both repositories:

```ini
-DMYNEWT_VAL_BLE_SM_LEGACY=0
-DMYNEWT_VAL_BLE_STORE_CONFIG_PERSIST=0
```

Runtime configuration requests authentication and Secure Connections with
bonding disabled. R3 is display-only (PIN available on its console); R1 accepts
the entered PIN. There is **no persistent bond or CCCD subscription state**;
CCCD enables notifications for the current link and must be written again after
reconnection. No BLE keys or subscription state are written to NVS by this path.

Advertised names aid discovery; they do not authenticate a source. After link
authentication, R1 validates the protected identity against the selected device
ID, wire version and capability. Notifications require an authenticated link
and matching device/boot identity. CRC32 detects frame damage and is not a
replacement for link authentication.

## Wire contract

The identical `r3_ble_protocol.h` in both firmware trees is the source of truth.
S1 uses little-endian integers; the six device-ID bytes use printed MAC order.

| GATT item | UUID | Value |
|---|---|---|
| Service | `7e57a100-7a1e-4e54-a930-64e137711031` | R3 coarse time observations |
| Identity | `7e57a101-7a1e-4e54-a930-64e137711031` | Protected read, exactly 36 bytes |
| Beacon | `7e57a102-7a1e-4e54-a930-64e137711031` | Protected read and authenticated notification, exactly 64 bytes |

The preferred ATT MTU is 128; the minimum is **67** (64-byte value plus the
three-byte notification overhead). S1 sends exactly one whole beacon per
notification. A smaller negotiated MTU is rejected; there is no fragmentation
or truncation fallback. The readable beacon remains empty until R3 has an actual
metronome observation. Notifications, not repeated reads, drive R1 tracking.

| Frame | Fields by byte offset |
|---|---|
| Identity, 36 bytes | 0: `R3TI`; 4: version 1; 5: type 1; 6: u16 length; 8: device ID[6]; 14: role 3; 15: capability 1 (coarse only); 16: u64 boot ID; 24: u32 clock revision; 28: u16 minimum MTU; 30: reserved zero[2]; 32: CRC32 of bytes 0–31 |
| Beacon, 64 bytes | 0: `R3TM`; 4: version 1; 5: type 2; 6: u16 length; 8: device ID[6]; 14: u16 flags (bit 0 UTC valid, bit 1 coarse required); 16: u64 boot ID; 24: u32 clock revision; 28: u32 sequence; 32: u64 CC capture µs; 40: u32 Unix seconds; 44: u32 legacy tick ms; 48: u32 uncertainty µs; 52: reserved zero[8]; 60: CRC32 of bytes 0–59 |

CRC is reflected IEEE CRC32 (`0xEDB88320`, initial/final XOR `0xFFFFFFFF`).
Uncertainty is always `UINT32_MAX`, meaning **unknown**, not zero. Sequence runs
1 through `UINT32_MAX` and wraps to 1. Unknown flags, versions, lengths, nonzero
reserved bytes, bad CRC and zero sequence are rejected.

## A received snapshot is not clock lock

The payload wraps the existing R3 metronome snapshot with identity, boot,
revision, capture and integrity fields. Its CC `capture_us` is the software
snapshot publication time, **not the RV3028 second edge**. The integer RTC
second and legacy `last_tick_ms` retain their original coarse semantics.
R1 captures its own monotonic receive time on notification entry, before queueing.
BLE scheduling, source polling and queue delays are not calibrated by S1.

R1 starts a new tracking segment on connection/reconnection and on an accepted
forward clock-revision change. It rejects wrong identities, stale connection
epochs, capture regressions and invalid frames; sequence gaps, duplicates and
out-of-order packets are counted. An accepted beacon is fresh for less than five
seconds. Invalid source UTC revokes UTC eligibility. Freshness and source UTC
validity are separate from relative-clock accuracy.

Panel state deliberately reports `synchronized: false`, `coarse: true` and
`uncertainty_us: null`. A fresh authenticated beacon displays:
**“Маяк отримано; точність синхронізації ще не визначена”**. It does not display
LOCKED. Diagnostics include source boot, clock revision, segment, sequence,
age, negotiated MTU, received/missing/malformed/duplicate/reordered counts,
queue drops and successful connections/reconnections. JSON u64 values remain
decimal strings; they must not be converted through JavaScript `Number`.

S1 does not estimate offset or drift, discipline either clock, set DS3231 time,
write EEPROM settings, modify sample deadlines/timestamps, or add synchronization
records to CSV schema 1. BLE loss leaves autonomous recording running. RAM-only
observations do not make an SD file synchronized. Versioned file evidence,
clock exchange, error bounds and the R3 CC-to-STM32 DRDY bridge belong to S2/S3.

## Ownership and acceptance still required

R3's time owner enqueues bounded snapshots to an eight-entry queue; its core-0
BLE worker publishes them. R1's core-0 worker manages discovery, authentication,
subscription and retries. Its notification callback captures time and copies
bounded frames into a 12-entry queue without waiting. Acquisition/I2C and the
sole SD writer retain their current ownership and PSRAM sample FIFO.

R1 builds only the central/observer roles with one client connection. Its
allocation-free `r3_ble::Receiver` owns frame acceptance and time-evidence state.
`CONFIG_BT_NIMBLE_MEM_ALLOC_MODE_EXTERNAL=1` selects the ESP-IDF-supported external
PSRAM allocation mode for NimBLE host pools. Before radio initialization, R1
requires `psramFound()` and a largest free PSRAM block of at least 128 KiB. This
is a conservative headroom guard, not a measured minimum BLE memory requirement.
RTOS task stacks, controller memory and DMA buffers remain in internal RAM;
external host pools do not remove the need to qualify internal heap and stacks.

Host validation on 2026-09-09: `python -m unittest tests.test_r3_ble_protocol
tests.test_r3_ble_receiver tests.test_r3_time_beacon -v` passed all **11 tests**.
These cover shared wire bytes, strict decoding, receiver identity/boot/revision
handling, invalid UTC, sequence wrap/reconnect and the legacy tracker. They run
without radios and do not establish physical link stability or synchronization
accuracy. Hardware acceptance remains pending.

Qualification must cover correct/wrong PIN, identity/version/MTU rejection,
disconnect/reconnect and both device reboots; beacon continuity and invalid UTC;
Wi-Fi coexistence, R1 recording at 1/50/300 Hz, R3 acquisition load, queue drops,
heap/stack, sample gaps and SD latency. R3 notification-attempt counters count
host enqueue attempts, not delivery acknowledgements. Compare receiver sequences
and losses. Record measured results separately before calling S1 accepted.
