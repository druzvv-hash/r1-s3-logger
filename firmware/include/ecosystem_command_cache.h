#pragma once
#include "ecosystem_protocol.h"

namespace ecosystem {
struct Receipt {
    bool used = false;
    Frame command = {}, result = {};
    uint64_t expiresUs = 0;
};
inline bool sameCommand(const Frame& a, const Frame& b) {
    uint8_t left[kFrameBytes], right[kFrameBytes];
    encode(a, left); encode(b, right);
    return memcmp(left, right, sizeof(left)) == 0;
}
// At capacity reject rather than evict live requests: otherwise a duplicate
// START can be executed again after flooding the deduplication cache.
class CommandCache {
public:
    static constexpr size_t kCapacity = 8;
    enum class Admission { New, Replay, Conflict, Full };
    struct Decision { Admission admission; Receipt* receipt; };
    Receipt* find(uint64_t request) {
        for (auto& item : items_) if (item.used && item.command.request == request) return &item;
        return nullptr;
    }
    Receipt* vacant(uint64_t nowUs) {
        for (auto& item : items_) if (!item.used || nowUs > item.expiresUs) return &item;
        return nullptr;
    }
    // Caller first verifies sender, boot, connection, framing and expiry.
    // Reserve before semantic readiness/permission checks, so a rejection is
    // just as immutable as an accepted operation for this request's lifetime.
    Decision admit(const Frame& frame, uint64_t nowUs) {
        if (auto* item = find(frame.request))
            return {sameCommand(item->command, frame) ? Admission::Replay : Admission::Conflict, item};
        const uint64_t expiry = frame.stamp_us + uint64_t(frame.ttl_ms) * 1000;
        auto* item = overflowUntilUs_ && nowUs <= overflowUntilUs_ ? nullptr : vacant(nowUs);
        if (!item) {
            // We cannot retain unlimited rejected IDs at capacity. Fail closed
            // for uncached requests until every overflow rejection has expired;
            // repeated attempts extend that fence to their own wire expiry.
            if (expiry > overflowUntilUs_) overflowUntilUs_ = expiry;
            return {Admission::Full, nullptr};
        }
        *item = {}; item->used = true; item->command = frame;
        item->expiresUs = expiry + 10000000;
        return {Admission::New, item};
    }
    void reset() { for (auto& item : items_) item.used = false; overflowUntilUs_ = 0; }
    Receipt* begin() { return items_; }
    Receipt* end() { return items_ + kCapacity; }
private:
    Receipt items_[kCapacity];
    uint64_t overflowUntilUs_ = 0;
};
} // namespace ecosystem
