#pragma once

#include <stddef.h>
#include <stdint.h>

// Portable groundwork only: no radio, RTC write, sample-clock adjustment or UTC
// offset estimate. The existing R3 emitter sends this line over CCTX UART;
// a future BLE transport must explicitly frame and deliver complete lines.
namespace r3_time {

static constexpr size_t kMaxBeaconBytes = 40;
static constexpr uint64_t kStaleAfterUs = 5000000ULL;

struct Beacon {
    uint32_t sequence;
    uint32_t unix_s;
    bool time_valid;
    uint32_t last_tick_ms;
};

enum class DecodeResult : uint8_t {
    Ok,
    InvalidLength,
    InvalidPrefix,
    InvalidField,
    Overflow,
    InvalidTimeFlag,
    InvalidTerminator
};

// Exact current R3 wire order: $TMB,seq,unix_s,valid,last_tick_ms\n
// Canonical unsigned decimal only, no whitespace/signs/leading zeroes/CR/NUL.
// Length includes LF; no terminating NUL is needed. On failure out is unchanged.
// time_valid=false is valid evidence, not a decoding error.
// Zero sequence is decoded as raw uint32 evidence, but Tracker rejects it:
// the current R3 counter runs 1..UINT32_MAX and skips zero when wrapping.
DecodeResult decode(const char* bytes, size_t length, Beacon& out);

struct Observation {
    Beacon beacon;
    uint64_t local_receive_us;
    uint64_t connection_segment;
};

struct Counters {
    uint64_t accepted;
    uint64_t bad_packets;
    uint64_t duplicates;
    uint64_t out_of_order;
    uint64_t missing_sequences;
    uint64_t unexpected_sequences;
    uint64_t disconnected_packets;
    uint64_t local_clock_regressions;
};

enum class ObserveResult : uint8_t {
    Accepted,
    AcceptedTimeInvalid,
    Malformed,
    Disconnected,
    Duplicate,
    OutOfOrder,
    UnexpectedSequence,
    LocalClockRegression
};

class Tracker {
public:
    Tracker();

    // Caller assigns a distinct segment ID for each connection/reconnection.
    // This resets sequence/freshness history, preserving lifetime counters.
    // No source reboot is inferred: the legacy packet has no boot/session ID.
    void beginSegment(uint64_t segment_id);
    void disconnect();

    // Single-owner API, not thread-safe. receive_us must use the same local
    // 64-bit monotonic clock throughout a segment. No allocation or waiting.
    ObserveResult observe(const char* bytes, size_t length, uint64_t receive_us);

    bool connected() const { return connected_; }
    bool hasAccepted() const { return have_accepted_; }
    bool hasDecoded() const { return have_decoded_; }
    const Observation& lastAccepted() const { return accepted_; }
    const Observation& lastDecoded() const { return decoded_; }
    const Counters& counters() const { return counters_; }

    // Duplicates, malformed and out-of-order packets never refresh this age.
    bool fresh(uint64_t now_us) const;

    // Eligibility to consider the evidence, NOT a synchronized-clock claim.
    // Any decoded invalid-time packet on this connection revokes eligibility
    // until a newer, accepted valid-time packet arrives. The old wire format
    // supplies no authentication, UTC accuracy or radio/queue delay bound.
    // Never equate receive_us with the remote second/tick or timestamp samples
    // from this alone. Preserve raw observations for later clock mapping.
    bool utcEvidenceEligible(uint64_t now_us) const;

private:
    bool connected_;
    bool have_accepted_;
    bool have_decoded_;
    bool invalid_time_seen_;
    uint64_t segment_;
    Observation accepted_;
    Observation decoded_;
    Counters counters_;
};

}  // namespace r3_time
