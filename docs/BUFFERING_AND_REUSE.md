# PSRAM FIFO and block writer foundation

2026-09-08, CONFIG v0.13 source. Owner requested reuse of suitable buffering and block-write designs, use of the installed 16 MB PSRAM, and an encoder stub until the hardware arrives. This stage supplies tested primitives and boot-time memory preparation, not a completed acquisition/recording pipeline.

## Evidence and selection

Current integration: [v0.18 session recorder](P5_RECORDING.md) connects these
primitives to acquisition, stopped buffer resizing, SD writes and Start/Stop.
The remaining sections preserve the original v0.13 foundation review.

Donors were inspected read-only; the implementation is adapted to INA228 and the existing CSV v1 contract, without copying old hardware constants, credentials or binary layouts.

| Donor | Reused idea | Change for R1-S3 |
|---|---|---|
| `Logger_Analysis/Projects/bekup/main21_12_3STAB.cpp`, `flushLogBuffer` / `appendToLogBuffer` | 8192-byte output staging | Never clear bytes without checking the write count; no storage calls from acquisition |
| `Logger_Analysis/Projects/21_01_26/main.cpp`, `ring_push`, `sd_flush_outbuf`, `log_task` | PSRAM ring, separate network core, accumulated SD writes, measured write duration, timed sync/rotation | Original producer and SD consumer run consecutively in one task. Use separate prioritized tasks; replace volatile indices with acquire/release atomics. Do not import ADS Block64 or its custom XOR checksum |
| `Logger_Analysis/Projects/T2CAN_sniffer_fw_01/src/drivers/twai_rxbuf_psram.c` | Explicit PSRAM capability allocation, queue telemetry | No silent internal-RAM fallback on this confirmed PSRAM board. Use task-context SPSC copying instead of copying PSRAM records while holding a critical-section spinlock. No live reset of queue indices |
| `lily-logger-r3/firmware/stm32/CM7/Core/Src/sd_filelog.c`, lines near 7076/7119 | Checked write result and byte count, independent checked sync, raw sequence/loss evidence | Keep these correctness rules; do not port STM32 DMA/cache plumbing, ADS timing or R3 file layout |

Exact donor SHA-256 at review:

```text
R1 STAB: 1d0edfc54f643a21b107ef2b3a71ed473151b79f182681db0b43e943f958441f
S3 Jan21: 2dc98f577582cc20ce154195bd6be457aa0fcb6e0ea61d7cfabb346b8f1e13c8
T2CAN FIFO: cb4a9ded94640ec4918bee42cf88fc723b757973a0d7877f8fb5c9a4b4ae9b44
R3 filelog: fe513abf1c67132159c37b42de05c69d161bc1bf9c750d7c4f0a47de7486f751
```

## Pipeline and memory budget

```text
Core 1 acquisition -> numeric Sample FIFO in PSRAM
                   -> Core 1 lower-priority recorder / frozen config
                   -> CSV v1 serialization + checkpoints
                   -> 8 KiB internal staging -> checked microSD write/sync
Core 0 local/web UI <- independent snapshots / bounded live preview
```

The FIFO is single-producer/single-consumer; the UI never consumes it. Each **32-byte** RAM sample carries 64-bit sequence and monotonic microseconds, decoded raw shunt/bus/temperature, quality, raw-presence mask and config revision. Calibration and CSV/UTC text formatting happen outside the acquisition producer using the session's frozen configuration. The RAM struct is not a persisted binary format. Existing file/config schemas remain unchanged.

`queue_bytes` already has a 64 KiB default and 1 MiB maximum. Preserve the applied value and EEPROM rather than changing it invisibly. Allocate the largest power-of-two slot count that fits this budget and report actual allocated bytes. A non-power-of-two budget is rounded down; it is never exceeded.

| FIFO payload | 32-byte slots | Empty-buffer capacity at 50 Hz | At 100 Hz |
|---|---:|---:|---:|
| 64 KiB (current default) | 2048 | 40.96 s | 20.48 s |
| 256 KiB (configurable) | 8192 | 163.84 s | 81.92 s |
| 1 MiB (current schema maximum) | 32768 | 655.36 s | 327.68 s |

These are arithmetic capacities if the consumer stops, not measured throughput or supported stall guarantees. Occupied slots reduce the remaining reserve; a producer that itself misses acquisition deadlines is not rescued by a larger FIFO. Pending PSRAM data is lost on power removal. Do not defer normal writes until the FIFO fills or increase flush intervals simply because PSRAM is large.

Memory placement is explicit:

- FIFO payload: `MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT`.
- SD staging: **8192 bytes** with `MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA | MALLOC_CAP_8BIT`.
- Queue indices, counters, task stacks, driver state and short-lived acquisition data: internal RAM. No PSRAM work from ISR context or while flash cache is disabled.

Allocation failure is a visible preparation failure, not a smaller buffer or internal-RAM fallback. Current `prepareMemory` runs once at boot, releases an incomplete allocation on failure and does not resize an already prepared FIFO. P4/P5 must add the stopped/owners-quiescent reconfiguration lifecycle before changing queue budgets can affect an active runtime. Until then, the startup allocation is preparation only.

For this Arduino 2.x / ESP-IDF 4.4 generation, use an internal DMA-capable staging buffer; do not assume that S3 hardware support implies this driver generation can directly DMA PSRAM. See [Espressif external-RAM restrictions](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-guides/external-ram.html). This allocation does not claim the current Arduino SD API uses zero-copy DMA.

## Queue and write invariants

- Producer copies a complete sample, then publishes the write index with release ordering. Consumer acquires it before reading. Consumer releases a slot only after downstream acceptance. No malloc, String formatting, SD operation or waiting in `tryPush`.
- Full FIFO rejects the new item, preserving unread data. `overflows()` counts rejected push attempts (saturating u32), not an independently inferred count of lost sensor conversions. P4 will attempt once per opportunity, latch the recording fault and preserve sequence/gap evidence. High-water and occupancy are diagnostics; occupancy is approximate during concurrency.
- `peek` is repeatable; `consume` is explicit. Do not consume a row until the recorder has retained all encoded bytes or its owned pending-row state. A serializer may split a row across byte blocks; it must track progress before releasing the raw sample.
- `BlockBuffer::append` is all-or-nothing and never performs storage I/O. Drain full 8 KiB blocks normally; explicit timed flush/STOP drains an unpadded tail. CSV content and ordering remain exact. An 8 KiB application write does not guarantee a single physical SD transaction or alignment after a variable-length header.
- Short/zero write latches a fault. Count only the accepted prefix; retain the remaining suffix and refuse implicit retries/new appends. An invalid oversized write count is a separate fault. Never replay an already accepted prefix or silently clear buffered samples after a failed write.
- Byte staging and CSV **checkpoint groups** are different layers: P1 normally uses up to 256 rows per checkpoint group; an 8 KiB write may contain part of a group or several control records. Timed sync should close a short checkpoint group before syncing, so the recoverable prefix is current. P5 will check sync failures, finalization, SD space and rotation; the byte helper does not implement them.
- `acceptedBytes` means bytes accepted by the sink API, not crash-proof media persistence. Existing CRC/checkpoint/END semantics remain authoritative; never emit a clean END on storage or queue failure.

## Delivered and remaining

Delivered: encoder action interface with no-hardware stub; portable `SampleRing` and `BlockBuffer`; ESP capability allocator; boot-time reservation/status. Host tests execute the same C++ implementation with concurrent owners, counter wrap, repeated peeks, backpressure, every short-write cut in a 512-byte block, exact multi-block/tail output, and allocation failure at each pool. The fake allocator verifies capability flags, not physical ESP RAM.

Pending P4/P5: GPIO encoder adapter, real UI dispatch, pinned acquisition/recorder tasks, ready/timestamp sampling, measured PSRAM stress/cadence under OLED/network load, CSV serializer, actual SD sink and checked sync, START/STOP, power-cut/SD-full acceptance. Normal firmware still runs the diagnostic measurement loop and creates no recording files at boot. See [task/UI contract](DEVICE_UI_AND_TASKS.md) and [plan](R1_S3_PLAN.md).

Validation in this stage: all 35 host tests and both normal/service firmware builds passed. The concurrent test transferred 400,000 samples in order; short-write tests exercised every cut from 0 through 511 accepted bytes. COM5 enumeration succeeded but opening the port failed with Windows error 31; v0.13 was not uploaded. Physical PSRAM allocation/stress and real SD stall behavior are therefore not yet verified for these new modules.
