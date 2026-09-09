#pragma once

#include "r3_ble_protocol.h"
#include "r3_time_beacon.h"
#include <stdio.h>

namespace r3_ble {

enum class ReceiveResult : uint8_t {
    Accepted,
    AcceptedTimeInvalid,
    Disconnected,
    Malformed,
    IdentityMismatch,
    BootMismatch,
    CaptureRegression,
    RevisionRejected,
    Duplicate,
    OutOfOrder,
    LocalClockRegression
};

struct ReceivedObservation {
    Beacon beacon;
    uint64_t local_receive_us;
    uint64_t connection_segment;
};

// Single-owner, allocation-free acceptance state. The radio owner must verify
// authenticated encryption, MTU and identity first, and discard notifications
// from an obsolete callback/connection epoch before calling observe(). This
// class cannot authenticate a packet or distinguish callbacks from two links.
// No clock is disciplined and no radio/queue delay bound is inferred.
class Receiver {
public:
    Receiver() : identity_(), accepted_(), tracker_(), segment_(0), malformed_(0),
                 utc_revoked_(false) {}

    // Every authenticated connection gets new sequence history, even if the
    // source boot ID did not change. Counts remain cumulative across links.
    void bind(const Identity& identity) {
        identity_ = identity;
        startSegment();
    }

    // Retain the last evidence for inspection; it is immediately ineligible.
    void disconnect() { tracker_.disconnect(); }

    ReceiveResult observe(const uint8_t* bytes, size_t length, uint64_t receive_us) {
        if (!tracker_.connected()) {
            tracker_.observe(nullptr, 0, receive_us); // lifetime disconnected count
            return ReceiveResult::Disconnected;
        }
        Beacon value = {};
        if (!decodeBeacon(bytes, length, value)) return reject(ReceiveResult::Malformed);
        if (!sameDevice(value.device_id, identity_.device_id))
            return reject(ReceiveResult::IdentityMismatch);
        if (value.boot_id != identity_.boot_id) return reject(ReceiveResult::BootMismatch);

        // Same-source invalid UTC revokes eligibility even if this packet is
        // old/reordered. A valid duplicate cannot restore the sticky latch.
        if (!value.utc_valid) utc_revoked_ = true;
        if (tracker_.hasAccepted() && value.capture_us < accepted_.beacon.capture_us)
            return reject(ReceiveResult::CaptureRegression);

        const uint32_t revision_delta = value.clock_revision - identity_.clock_revision;
        const bool new_revision = revision_delta != 0;
        if (new_revision) {
            if (revision_delta >= 0x80000000u) return reject(ReceiveResult::RevisionRejected);
            if (tracker_.hasAccepted()) {
                const uint32_t previous = accepted_.beacon.sequence;
                const uint32_t delta = value.sequence >= previous ? value.sequence - previous
                    : UINT32_MAX - previous + value.sequence;
                if (delta == 0 || delta >= 0x80000000u)
                    return reject(ReceiveResult::RevisionRejected);
            }
            // There may be no accepted notification yet: a clock correction
            // between identity read and first beacon must not reject forever.
        }

        char line[r3_time::kMaxBeaconBytes + 1];
        const int n = snprintf(line, sizeof(line), "$TMB,%lu,%lu,%u,%lu\n",
            (unsigned long)value.sequence, (unsigned long)value.unix_s,
            value.utc_valid ? 1u : 0u, (unsigned long)value.last_tick_ms);
        if (n < 0 || size_t(n) >= sizeof(line)) return reject(ReceiveResult::Malformed);

        // Check local monotonicity before a revision transition clears history.
        // Let Tracker record this rejection in its existing lifetime counter.
        if (tracker_.hasAccepted() && receive_us < accepted_.local_receive_us) {
            tracker_.observe(line, size_t(n), receive_us);
            return ReceiveResult::LocalClockRegression;
        }
        if (new_revision) {
            identity_.clock_revision = value.clock_revision;
            startSegment();
        }
        const r3_time::ObserveResult result = tracker_.observe(line, size_t(n), receive_us);
        if (result == r3_time::ObserveResult::Accepted ||
            result == r3_time::ObserveResult::AcceptedTimeInvalid) {
            accepted_ = {value, receive_us, segment_};
            utc_revoked_ = !value.utc_valid;
            return value.utc_valid ? ReceiveResult::Accepted : ReceiveResult::AcceptedTimeInvalid;
        }
        if (result == r3_time::ObserveResult::Duplicate) return ReceiveResult::Duplicate;
        if (result == r3_time::ObserveResult::OutOfOrder) return ReceiveResult::OutOfOrder;
        if (result == r3_time::ObserveResult::LocalClockRegression)
            return ReceiveResult::LocalClockRegression;
        return reject(ReceiveResult::Malformed);
    }

    uint64_t segment() const { return segment_; }
    const Identity& identity() const { return identity_; }
    bool connected() const { return tracker_.connected(); }
    bool hasAccepted() const { return tracker_.hasAccepted(); }
    const ReceivedObservation& lastAccepted() const { return accepted_; }
    const r3_time::Counters& counters() const { return tracker_.counters(); }
    // Framing/source/capture/revision rejections; duplicate/out-of-order/local
    // clock rejection counts remain separate in counters().
    uint64_t malformed() const { return malformed_; }
    bool fresh(uint64_t now_us) const { return tracker_.fresh(now_us); }
    bool utcEvidenceEligible(uint64_t now_us) const {
        return !utc_revoked_ && tracker_.utcEvidenceEligible(now_us);
    }

private:
    void startSegment() {
        ++segment_;
        tracker_.beginSegment(segment_);
        accepted_ = {};
        utc_revoked_ = false;
    }
    ReceiveResult reject(ReceiveResult result) {
        if (malformed_ != UINT64_MAX) ++malformed_;
        return result;
    }

    Identity identity_;
    ReceivedObservation accepted_;
    r3_time::Tracker tracker_;
    uint64_t segment_;
    uint64_t malformed_;
    bool utc_revoked_;
};

}  // namespace r3_ble
