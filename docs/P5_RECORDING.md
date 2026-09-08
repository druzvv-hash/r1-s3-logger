# P5 — sessions on microSD

PANEL v0.18 connects timed INA228 acquisition to the existing PSRAM FIFO and the
microSD owner. Recording starts only with an explicit START. The panel provides
Start/Stop, state, file path, elapsed time, saved-row and byte counts, net Wh/Ah,
queue occupancy/high-water/overflow and maximum write/sync latency. OLED shows the
recording state. Closing the browser does not issue STOP.

## Ownership and admission

Core 1 acquisition runs at priority 3. It copies a 32-byte raw sample to the SPSC
FIFO without formatting, allocation or storage calls. The existing core 1 SD task
runs at priority 1 and now owns both recording and downloads. Core 0 retains the
web/UART transports and browser live preview. There is no second independent SD
writer and the UI does not consume the recording FIFO.

START copies applied configuration, revision, saved generation, sensor identity
and actual ADC register readback into an immutable session. UTC comes from a fresh
read of DS3231, anchored to the monotonic clock with 1.1 s declared uncertainty;
it is not resynchronized within a session. Unknown UTC requires the existing
explicit `allow_unknown_utc` policy. The first implementation requires a positive
saved generation; an unsaved applied profile can still be recorded with its full
config payload/hash and the last saved generation.

Admission also requires an appropriate gap threshold, allocated buffers, readable
card, reserve free space and no existing download/directory session. The storage
owner checks transfer admission, avoiding a race between START and a queued file
request. A rejected START leaves the existing transfer intact. Settings, Save,
clock and diagnostic commands are rejected throughout STARTING/RUNNING/STOPPING,
before any acquisition pause. All SD read operations, including CLOSE, are rejected
while recording owns the card. STOP ends production at a conversion boundary,
then the SD owner drains the FIFO before finalizing.

The quick rate control raises `max_gap_us` to at least two sample periods when
needed. It does not reduce a larger explicit threshold. At 10 Hz, the original
40 ms threshold would correctly mark every 100 ms interval as a gap and suppress
integration. START rejects thresholds no longer than one period; profiles edited
manually must choose a larger value. This changes only the applied RAM profile
until the owner explicitly chooses Save.

## Buffers and writes

The existing applied queue budget controls PSRAM allocation: 64 KiB by default,
2048 samples. The stopped lifecycle can reallocate after an explicit budget change;
allocation failure preserves the old pool and refuses START. Indices and staging
reset only with producer and consumer quiescent. There is no silent internal-RAM
fallback for the FIFO. Output staging remains 8192 bytes in internal DMA-capable
RAM. A row leaves the raw FIFO only after the serializer retains all its bytes.

Full blocks drain through checked POSIX `write` on ESP-IDF's mounted FAT VFS.
Short/zero writes latch failure without replaying an accepted prefix. The writer
closes a checkpoint group before each configured flush interval (default 1 s),
drains the unpadded tail, and checks `fsync`. Free space is checked before START,
after sync and before rotation; accepted writes consume a cached budget above the
configured reserve. This is bounded buffering, not a claim of power-loss durability.

## Files, integrity and totals

New sessions use `/records/r1s3_<utc-or-0>_<random64>_0000.part`, created exclusively.
No existing file is opened for overwrite. The content follows the unchanged
[R1S3 CSV v1 contract](FILE_FORMAT.md): full interpretation metadata/config hash,
raw and calibrated values, monotonic timestamps, quality flags, metadata CRC32,
checkpoint CRC32 and final SHA-256. Generated build provenance includes the exact
Git commit and dirty-source marker; credentials do not enter metadata.

Raw records are timestamped when conversion-ready is observed, before register
readback. The storage task computes engineering values and trapezoidal, sign-split
Wh/Ah using the frozen configuration. Invalid readings and gaps never add energy;
incomplete totals stay marked. No time before the first or after the last sample
is extrapolated. Screen filtering does not affect recorded values.

STOP drains, writes END, syncs and checks close before renaming `.part` to `.csv`.
Only then does the panel report READY / file saved. Rotation uses the configured
size (default 1 GiB), leaving space for final controls. Each new part carries the
previous complete-file SHA-256, the same session/config/time anchor, continued
sequence and totals. A failure leaves ERROR and the `.part` file. If the last sync,
close or rename fails, that file may already contain an intact END; it is still
not published as a successfully saved `.csv`. No automatic retry, erase or recovery
rewrite is performed. Queue overflow also stops recording with an explicit error.

## Validation and remaining limits

Host tests execute the firmware serializer and feed its output into both the
independent P1 decoder and current production viewer. They cover valid/unknown UTC,
sign crossings, invalid/saturated samples, sequence gaps, checkpoints, rotated part
hashes/totals, empty sessions, interrupted prefixes, short-write/sync faults and
configuration revision mismatch. SHA-256 is checked against empty, `abc` and
million-`a` vectors. Buffer tests also cover stopped resize and allocation failure.

The physical acceptance below uses USB, the existing low-side 150-microohm shunt
and the owner's nominal 3 A / 3 V load. It does not establish reference accuracy.
Raw captures and downloaded files remain under ignored `data/recording-tests/`.

### Bench acceptance — 2026-09-08

| Test | Stored rows | Files / bytes | Result |
|---|---:|---|---|
| 50 Hz, actual browser Start/Stop/download | 537 | 1 / 115,337 | Clean; all rows verified |
| 10 Hz, mobile quick-rate control, 200 ms gap threshold | 68 | 1 / 16,846 | Clean; integration enabled |
| 100 Hz, approximately 59 s, 1 MiB rotation threshold | 5878 | 2 / 1,235,957 | Clean; both parts verified |

The 100 Hz parts contain 4978 and 900 rows. Both were downloaded in full and
validated by the independent contract reader and current viewer. The complete-file
SHA link and trapezoidal integration across the rotation boundary also pass. There
were no invalid samples, missed periods, sequence gaps or FIFO overflows. FIFO
high-water was 35 of 2048 samples; maximum write was 94.627 ms and sync 64.901 ms.
Final session totals were 0.146422971401 Wh and 0.0489173170579 Ah. These measured
SD stalls demonstrate why acquisition and block writing need separate tasks.

Browser desktop Start/Stop/download and mobile quick-rate/Start/Stop/download pass;
the desktop rendering rate averaged 59.90 FPS during 50 Hz recording. Screenshots
were inspected. Rejected Apply, diagnostic, duplicate START and file operations did
not pause acquisition. START during an open directory failed without destroying
the existing directory session, which then closed normally.

An initial 10 Hz test retained the old 40 ms maximum gap. Its 82 rows were valid,
but all 81 intervals were explicitly marked gaps and totals stayed zero, as the
contract requires. That finding led to the quick-control adjustment and START
guard described above. The subsequent 10 Hz mobile test uses 200 ms. An early test
helper also had to wait for the next published snapshot after asynchronous START;
its stale ERROR observation was not an SD failure.

The final host suite has 51 passing tests. Normal and service builds pass; only
normal is used on the board. Upload continues to need retries on the existing USB
link; verified flash writes do not establish that transport as permanently fixed.
Tests restore the original 50 Hz / 40 ms-gap applied profile and saved generation
3. No EEPROM Save, calibration change, clock write or card formatting is performed.

Pending physical acceptance: card full/removal, power-cut/FAT recovery, long-duration
recording, memory stress and phone-to-AP transfer. Local encoder hardware/menus,
remaining-time estimates and multi-part viewer navigation remain later work.
Each rotation file already opens individually in the viewer; richer R5 analysis
features are still tracked separately.
