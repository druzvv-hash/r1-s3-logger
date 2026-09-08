#include "recording_buffer.h"
#include <cstring>

namespace recording {
uint32_t capacityForBytes(uint32_t bytes) {
    uint32_t count = bytes / sizeof(Sample);
    if (!count) return 0;
    uint32_t capacity = 1;
    while (capacity <= count / 2) capacity *= 2;
    return capacity;
}

bool SampleRing::attach(Sample* slots, uint32_t capacity, uint32_t initialCursor) {
    if (!slots || !capacity || (capacity & (capacity - 1)) || capacity > 0x40000000u)
        return false;
    slots_ = slots;
    capacity_ = capacity;
    write_.store(initialCursor, std::memory_order_relaxed);
    read_.store(initialCursor, std::memory_order_relaxed);
    highWater_.store(0, std::memory_order_relaxed);
    overflows_.store(0, std::memory_order_relaxed);
    return true;
}

bool SampleRing::tryPush(const Sample& sample) {
    if (!slots_) return false;
    const uint32_t w = write_.load(std::memory_order_relaxed);
    const uint32_t used = w - read_.load(std::memory_order_acquire);
    if (used >= capacity_) {
        const uint32_t lost = overflows_.load(std::memory_order_relaxed);
        if (lost != UINT32_MAX) overflows_.store(lost + 1, std::memory_order_relaxed);
        return false;  // Keep unread samples, do not overwrite oldest.
    }
    slots_[w & (capacity_ - 1)] = sample;
    write_.store(w + 1, std::memory_order_release); // Publish only after copying.
    if (used + 1 > highWater_.load(std::memory_order_relaxed))
        highWater_.store(used + 1, std::memory_order_relaxed);
    return true;
}

bool SampleRing::peek(Sample& sample) const {
    if (!slots_) return false;
    const uint32_t r = read_.load(std::memory_order_relaxed);
    if (r == write_.load(std::memory_order_acquire)) return false;
    sample = slots_[r & (capacity_ - 1)];
    return true;
}

bool SampleRing::consume() {
    const uint32_t r = read_.load(std::memory_order_relaxed);
    if (!slots_ || r == write_.load(std::memory_order_acquire)) return false;
    read_.store(r + 1, std::memory_order_release);
    return true;
}

uint32_t SampleRing::queuedApprox() const {
    const uint32_t r = read_.load(std::memory_order_acquire);
    const uint32_t used = write_.load(std::memory_order_acquire) - r;
    // A third observer can see a consumer/producers' interleaving. Bound telemetry.
    return used > capacity_ ? capacity_ : used;
}

bool BlockBuffer::attach(uint8_t* bytes, size_t capacity) {
    if (!bytes || !capacity || capacity % 512) return false;
    bytes_ = bytes;
    capacity_ = capacity;
    used_ = written_ = 0;
    accepted_ = completeWrites_ = 0;
    fault_ = WriteFault::None;
    return true;
}

bool BlockBuffer::append(const uint8_t* data, size_t size) {
    if (fault_ != WriteFault::None || (!data && size) || size > freeBytes()) return false;
    if (size) std::memcpy(bytes_ + used_, data, size);
    used_ += size;
    return true;
}

bool BlockBuffer::drain(ByteSink& sink, bool includeTail) {
    if (fault_ != WriteFault::None) return false;
    if (!pending() || (!includeTail && used_ < capacity_)) return true;
    const size_t requested = pending();
    const size_t n = sink.write(bytes_ + written_, requested);
    if (n > requested) {
        fault_ = WriteFault::InvalidCount;
        return false;
    }
    accepted_ += n;
    written_ += n;
    if (n != requested) {
        // A prefix may already be on SD. Latch fault, retain unwritten bytes and
        // refuse automatic retry (which could duplicate an already written prefix).
        fault_ = WriteFault::ShortWrite;
        return false;
    }
    used_ = written_ = 0;
    ++completeWrites_;
    return true;
}
}  // namespace recording
