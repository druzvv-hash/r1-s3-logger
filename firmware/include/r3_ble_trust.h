#pragma once
#include "r3_ble_protocol.h"
#include "ecosystem_protocol.h"

// Public association policy only. NimBLE stores secret bond keys separately in
// NVS; neither this record nor external EEPROM ever stores a pairing PIN.
namespace r3_trust {
constexpr size_t kBytes = 24;
struct Policy { uint8_t peer[6] = {}; uint8_t addressType = 0; bool remote = false; };
inline void encode(const Policy& p, uint8_t* out) {
    memset(out, 0, kBytes); memcpy(out, "R1BP", 4); out[4] = 1;
    out[5] = p.remote ? 1 : 0; out[6] = p.addressType;
    memcpy(out + 8, p.peer, 6);
    r3_ble::detail::put32(out + 20, r3_ble::crc32(out, 20));
}
inline bool decode(const uint8_t* b, size_t n, Policy& out) {
    if (!b || n != kBytes || memcmp(b, "R1BP", 4) || b[4] != 1 ||
        b[5] > 1 || b[6] > 1 || b[7] ||
        r3_ble::detail::get32(b + 20) != r3_ble::crc32(b, 20)) return false;
    for (size_t i = 14; i < 20; ++i) if (b[i]) return false;
    Policy value; memcpy(value.peer, b + 8, 6);
    value.addressType = b[6]; value.remote = b[5] != 0; out = value; return true;
}
inline bool fresh(uint64_t now, uint64_t stamp, uint32_t ttlMs) {
    return ttlMs && ttlMs <= 5000 && stamp <= now && now - stamp <= uint64_t(ttlMs) * 1000;
}
inline bool commandForConnection(const ecosystem::Frame& frame, uint64_t beganUs, uint64_t nowUs) {
    return beganUs && frame.stamp_us >= beganUs && ecosystem::commandFresh(frame, nowUs);
}
inline bool timeReplyEligible(const ecosystem::Frame& f, uint64_t request,
                              uint64_t sentUs, uint64_t receiveUs) {
    return f.kind == ecosystem::Kind::TimeReply && request && f.request == request &&
        f.stamp_us == sentUs && receiveUs >= sentUs &&
        receiveUs - sentUs <= uint64_t(ecosystem::kTimeRoundTripMaxMs) * 1000 &&
        f.detail <= ecosystem::kTimeSourceAgeMaxMs && (f.flags & ecosystem::RtcValid) &&
        f.value_us >= 946684800000000ULL && f.value_us < 4102444800000000ULL;
}
} // namespace r3_trust
