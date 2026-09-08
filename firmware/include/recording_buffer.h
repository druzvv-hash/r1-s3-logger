#pragma once

#include <atomic>
#include <stddef.h>
#include <stdint.h>
#include <type_traits>

namespace recording {
// RAM transport only, never dump this struct to a file. P5 serializes CSV v1.
// Raw presence is independent of quality: absent evidence is not numeric zero.
struct Sample {
    uint64_t seq;
    uint64_t t_us;
    int32_t vshunt_raw;
    uint32_t vbus_raw;
    int16_t temp_raw;
    uint8_t quality;       // FILE_FORMAT.md bits 0..4
    uint8_t raw_present;   // bit 0 shunt, 1 bus, 2 temperature (internal only)
    uint32_t config_revision;
};
static_assert(sizeof(Sample) == 32, "Update the queue memory budget with Sample");
static_assert(std::is_trivially_copyable<Sample>::value, "Queue copies value samples");
static_assert(ATOMIC_INT_LOCK_FREE == 2, "Queue needs lock-free 32-bit indices");

// One producer, one consumer, task context with PSRAM cache available.
// Keep this control object in internal RAM. Only the slots live in PSRAM.
class SampleRing {
public:
    // Attach/reset only while BOTH owners are quiescent. Memory stays caller-owned.
    // initialCursor supports sequence-wrap validation; normally zero.
    bool attach(Sample* slots, uint32_t capacity, uint32_t initialCursor = 0);
    bool tryPush(const Sample& sample);  // Never waits; false on full/unprepared.
    bool peek(Sample& sample) const;    // Consumer only; does not free the slot.
    bool consume();                    // Consumer only, after downstream acceptance.
    uint32_t capacity() const { return capacity_; }
    uint32_t queuedApprox() const;     // Telemetry only; not a reservation.
    uint32_t highWater() const { return highWater_.load(std::memory_order_relaxed); }
    uint32_t overflows() const { return overflows_.load(std::memory_order_relaxed); }
private:
    Sample* slots_ = nullptr;
    uint32_t capacity_ = 0;
    std::atomic<uint32_t> write_{0}, read_{0}, highWater_{0}, overflows_{0};
};

// Largest power-of-two slot count fitting the exact applied queue_bytes budget.
uint32_t capacityForBytes(uint32_t bytes);

class ByteSink {
public:
    virtual ~ByteSink() = default;
    virtual size_t write(const uint8_t* data, size_t size) = 0;
};
enum class WriteFault : uint8_t { None, Unprepared, ShortWrite, InvalidCount };

// Sole recorder-owner byte staging, normally 8192 internal DMA-capable bytes.
// Append never calls storage. Full blocks drain explicitly; a timed flush/STOP
// drains the tail without padding. Sync/checkpoints/finalization belong to P5.
class BlockBuffer {
public:
    // Only while owner is quiescent; intentionally resets all state.
    bool attach(uint8_t* bytes, size_t capacity);
    bool append(const uint8_t* data, size_t size); // All or nothing, no hidden flush.
    bool drain(ByteSink& sink, bool includeTail = false);
    size_t pending() const { return used_ - written_; }
    const uint8_t* pendingData() const { return bytes_ ? bytes_ + written_ : nullptr; }
    size_t freeBytes() const { return capacity_ - used_; }
    uint64_t acceptedBytes() const { return accepted_; } // Not power-loss durability.
    uint32_t completeWrites() const { return completeWrites_; }
    WriteFault fault() const { return fault_; }
private:
    uint8_t* bytes_ = nullptr;
    size_t capacity_ = 0, used_ = 0, written_ = 0;
    uint64_t accepted_ = 0;
    uint32_t completeWrites_ = 0;
    WriteFault fault_ = WriteFault::Unprepared;
};
}  // namespace recording
