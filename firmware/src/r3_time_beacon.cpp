#include "r3_time_beacon.h"

namespace r3_time {
namespace {

DecodeResult readUint32(const char* bytes, size_t length, size_t& pos,
                        char delimiter, uint32_t& out) {
    const size_t start = pos;
    uint32_t value = 0;
    while (pos < length && bytes[pos] >= '0' && bytes[pos] <= '9') {
        if (pos > start && bytes[start] == '0') {
            return DecodeResult::InvalidField;
        }
        const uint32_t digit = static_cast<uint32_t>(bytes[pos] - '0');
        if (value > (UINT32_MAX - digit) / 10u) {
            return DecodeResult::Overflow;
        }
        value = value * 10u + digit;
        ++pos;
    }
    if (pos == start || pos >= length || bytes[pos] != delimiter) {
        return DecodeResult::InvalidField;
    }
    ++pos;
    out = value;
    return DecodeResult::Ok;
}

void addSaturated(uint64_t& value, uint64_t amount = 1) {
    value = amount > UINT64_MAX - value ? UINT64_MAX : value + amount;
}

}  // namespace

DecodeResult decode(const char* bytes, size_t length, Beacon& out) {
    if (!bytes || length < 13 || length > kMaxBeaconBytes) {
        return DecodeResult::InvalidLength;
    }
    static const char prefix[] = "$TMB,";
    for (size_t i = 0; i < sizeof(prefix) - 1; ++i) {
        if (bytes[i] != prefix[i]) return DecodeResult::InvalidPrefix;
    }
    if (bytes[length - 1] != '\n') return DecodeResult::InvalidTerminator;

    Beacon parsed = {};
    size_t pos = sizeof(prefix) - 1;
    DecodeResult result = readUint32(bytes, length, pos, ',', parsed.sequence);
    if (result != DecodeResult::Ok) return result;
    result = readUint32(bytes, length, pos, ',', parsed.unix_s);
    if (result != DecodeResult::Ok) return result;
    if (pos + 1 >= length || (bytes[pos] != '0' && bytes[pos] != '1') ||
        bytes[pos + 1] != ',') {
        return DecodeResult::InvalidTimeFlag;
    }
    parsed.time_valid = bytes[pos] == '1';
    pos += 2;
    result = readUint32(bytes, length, pos, '\n', parsed.last_tick_ms);
    if (result != DecodeResult::Ok) return result;
    if (pos != length) return DecodeResult::InvalidTerminator;
    out = parsed;
    return DecodeResult::Ok;
}

Tracker::Tracker()
    : connected_(false), have_accepted_(false), have_decoded_(false),
      invalid_time_seen_(false), segment_(0), accepted_(), decoded_(), counters_() {}

void Tracker::beginSegment(uint64_t segment_id) {
    connected_ = true;
    have_accepted_ = false;
    have_decoded_ = false;
    invalid_time_seen_ = false;
    segment_ = segment_id;
    accepted_ = {};
    decoded_ = {};
}

void Tracker::disconnect() {
    connected_ = false;
    // Keep evidence inspectable, but it can no longer be eligible/fresh.
}

ObserveResult Tracker::observe(const char* bytes, size_t length, uint64_t receive_us) {
    if (!connected_) {
        addSaturated(counters_.disconnected_packets);
        return ObserveResult::Disconnected;
    }
    Beacon packet = {};
    if (decode(bytes, length, packet) != DecodeResult::Ok) {
        addSaturated(counters_.bad_packets);
        return ObserveResult::Malformed;
    }
    decoded_ = {packet, receive_us, segment_};
    have_decoded_ = true;
    if (!packet.time_valid) invalid_time_seen_ = true;
    if (packet.sequence == 0) {
        addSaturated(counters_.unexpected_sequences);
        return ObserveResult::UnexpectedSequence;
    }

    if (have_accepted_) {
        if (receive_us < accepted_.local_receive_us) {
            addSaturated(counters_.local_clock_regressions);
            return ObserveResult::LocalClockRegression;
        }
        if (packet.sequence == accepted_.beacon.sequence) {
            addSaturated(counters_.duplicates);
            return ObserveResult::Duplicate;
        }
        // R3 skips zero: the sequence ring has UINT32_MAX entries. MAX -> 1
        // is one step, not a missing frame. Forward distances beyond half
        // that ring are treated as old/ambiguous; no source reboot is guessed.
        // last_tick_ms is raw and may wrap independently through zero.
        const uint32_t previous = accepted_.beacon.sequence;
        const uint32_t delta = packet.sequence > previous
            ? packet.sequence - previous
            : UINT32_MAX - previous + packet.sequence;
        if (delta >= 0x80000000u) {
            addSaturated(counters_.out_of_order);
            return ObserveResult::OutOfOrder;
        }
        addSaturated(counters_.missing_sequences, uint64_t(delta) - 1);
    }
    accepted_ = decoded_;
    have_accepted_ = true;
    invalid_time_seen_ = !packet.time_valid;
    addSaturated(counters_.accepted);
    return packet.time_valid ? ObserveResult::Accepted : ObserveResult::AcceptedTimeInvalid;
}

bool Tracker::fresh(uint64_t now_us) const {
    return connected_ && have_accepted_ && now_us >= accepted_.local_receive_us &&
           now_us - accepted_.local_receive_us < kStaleAfterUs;
}

bool Tracker::utcEvidenceEligible(uint64_t now_us) const {
    return fresh(now_us) && accepted_.beacon.time_valid && !invalid_time_seen_;
}

}  // namespace r3_time
