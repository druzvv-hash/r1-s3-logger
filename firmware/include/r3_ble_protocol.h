#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

// R3/R1-S3 BLE time observation, S1 wire version 1. This transports a coarse
// legacy metronome snapshot, not a synchronized clock or an RTC edge. CRC32
// detects damaged frames; it is not authentication. Device ID is canonical
// MAC-order bytes (the leftmost printed octet first), independent of BLE stack
// address storage. Keep the R3 and R1-S3 copies byte-identical.
namespace r3_ble {

static constexpr char kServiceUuid[] = "7e57a100-7a1e-4e54-a930-64e137711031";
static constexpr char kIdentityUuid[] = "7e57a101-7a1e-4e54-a930-64e137711031";
static constexpr char kBeaconUuid[] = "7e57a102-7a1e-4e54-a930-64e137711031";
static constexpr size_t kIdentityBytes = 36;
static constexpr size_t kBeaconBytes = 64;
static constexpr uint16_t kMinMtu = 67;
static constexpr uint16_t kPreferredMtu = 128;
static constexpr uint32_t kUnknownUncertaintyUs = UINT32_MAX;

struct Identity {
    uint8_t device_id[6];
    uint64_t boot_id;
    uint32_t clock_revision;
};

struct Beacon {
    uint8_t device_id[6];
    uint64_t boot_id;
    uint32_t clock_revision;
    uint32_t sequence;     // 1..UINT32_MAX; zero is skipped at wrap.
    uint64_t capture_us;   // CC esp_timer snapshot, not the RTC second edge.
    uint32_t unix_s;
    uint32_t last_tick_ms;
    bool utc_valid;
};

inline bool supportsMtu(uint16_t negotiated_mtu) {
    // Version 1 uses one notification; never truncate or fragment a frame.
    return negotiated_mtu >= kMinMtu;
}

inline bool sameDevice(const uint8_t* lhs, const uint8_t* rhs) {
    return lhs != nullptr && rhs != nullptr && memcmp(lhs, rhs, 6) == 0;
}

namespace detail {
inline uint16_t get16(const uint8_t* p) {
    return uint16_t(uint16_t(p[0]) | (uint16_t(p[1]) << 8));
}
inline uint32_t get32(const uint8_t* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
           (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
inline uint64_t get64(const uint8_t* p) {
    return uint64_t(get32(p)) | (uint64_t(get32(p + 4)) << 32);
}
inline void put16(uint8_t* p, uint16_t value) {
    p[0] = uint8_t(value);
    p[1] = uint8_t(value >> 8);
}
inline void put32(uint8_t* p, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) p[i] = uint8_t(value >> (8 * i));
}
inline void put64(uint8_t* p, uint64_t value) {
    for (unsigned i = 0; i < 8; ++i) p[i] = uint8_t(value >> (8 * i));
}
inline int hexDigit(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
}  // namespace detail

// IEEE CRC32 (reflected 0xEDB88320, init/final xor 0xFFFFFFFF).
inline uint32_t crc32(const uint8_t* bytes, size_t length) {
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < length; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? 0xEDB88320u : 0u);
    }
    return crc ^ UINT32_MAX;
}

// Buffers supplied to encoders must hold exactly the corresponding frame size.
inline void encodeIdentity(const Identity& value, uint8_t* bytes) {
    memset(bytes, 0, kIdentityBytes);
    memcpy(bytes, "R3TI", 4);
    bytes[4] = 1;
    bytes[5] = 1;
    detail::put16(bytes + 6, uint16_t(kIdentityBytes));
    memcpy(bytes + 8, value.device_id, 6);
    bytes[14] = 3;  // R3 source role.
    bytes[15] = 1;  // Coarse legacy beacon capability only.
    detail::put64(bytes + 16, value.boot_id);
    detail::put32(bytes + 24, value.clock_revision);
    detail::put16(bytes + 28, kMinMtu);
    detail::put32(bytes + 32, crc32(bytes, 32));
}

inline bool decodeIdentity(const uint8_t* bytes, size_t length, Identity& out) {
    if (bytes == nullptr || length != kIdentityBytes) return false;
    if (memcmp(bytes, "R3TI", 4) != 0 || bytes[4] != 1 || bytes[5] != 1 ||
        detail::get16(bytes + 6) != kIdentityBytes ||
        bytes[14] != 3 || bytes[15] != 1 ||
        detail::get16(bytes + 28) != kMinMtu ||
        detail::get16(bytes + 30) != 0 ||
        detail::get32(bytes + 32) != crc32(bytes, 32)) return false;
    Identity candidate = {};
    memcpy(candidate.device_id, bytes + 8, 6);
    candidate.boot_id = detail::get64(bytes + 16);
    candidate.clock_revision = detail::get32(bytes + 24);
    out = candidate;
    return true;
}

inline void encodeBeacon(const Beacon& value, uint8_t* bytes) {
    memset(bytes, 0, kBeaconBytes);
    memcpy(bytes, "R3TM", 4);
    bytes[4] = 1;
    bytes[5] = 2;
    detail::put16(bytes + 6, uint16_t(kBeaconBytes));
    memcpy(bytes + 8, value.device_id, 6);
    detail::put16(bytes + 14, uint16_t(2u | (value.utc_valid ? 1u : 0u)));
    detail::put64(bytes + 16, value.boot_id);
    detail::put32(bytes + 24, value.clock_revision);
    detail::put32(bytes + 28, value.sequence);
    detail::put64(bytes + 32, value.capture_us);
    detail::put32(bytes + 40, value.unix_s);
    detail::put32(bytes + 44, value.last_tick_ms);
    detail::put32(bytes + 48, kUnknownUncertaintyUs);
    detail::put32(bytes + 60, crc32(bytes, 60));
}

inline bool decodeBeacon(const uint8_t* bytes, size_t length, Beacon& out) {
    if (bytes == nullptr || length != kBeaconBytes) return false;
    if (memcmp(bytes, "R3TM", 4) != 0 || bytes[4] != 1 || bytes[5] != 2 ||
        detail::get16(bytes + 6) != kBeaconBytes ||
        detail::get32(bytes + 60) != crc32(bytes, 60)) return false;
    const uint16_t flags = detail::get16(bytes + 14);
    if ((flags & 2u) == 0 || (flags & uint16_t(~3u)) != 0 ||
        detail::get32(bytes + 28) == 0 ||
        detail::get32(bytes + 48) != kUnknownUncertaintyUs) return false;
    for (size_t i = 52; i < 60; ++i)
        if (bytes[i] != 0) return false;
    Beacon candidate = {};
    memcpy(candidate.device_id, bytes + 8, 6);
    candidate.boot_id = detail::get64(bytes + 16);
    candidate.clock_revision = detail::get32(bytes + 24);
    candidate.sequence = detail::get32(bytes + 28);
    candidate.capture_us = detail::get64(bytes + 32);
    candidate.unix_s = detail::get32(bytes + 40);
    candidate.last_tick_ms = detail::get32(bytes + 44);
    candidate.utc_valid = (flags & 1u) != 0;
    out = candidate;
    return true;
}

// Parse exactly 17 characters plus NUL, canonical colon-separated MAC order.
// Either hex case is accepted. The destination stays unchanged on failure.
inline bool parseDevice(const char* text, uint8_t* out) {
    if (text == nullptr || out == nullptr) return false;
    uint8_t candidate[6] = {};
    for (size_t i = 0; i < 6; ++i) {
        const int high = detail::hexDigit(*text);
        if (high < 0) return false;
        ++text;
        const int low = detail::hexDigit(*text);
        if (low < 0) return false;
        ++text;
        candidate[i] = uint8_t((high << 4) | low);
        if (i < 5) {
            if (*text != ':') return false;
            ++text;
        }
    }
    if (*text != '\0') return false;
    memcpy(out, candidate, 6);
    return true;
}

// Caller supplies six source bytes and at least 18 destination bytes.
inline void formatDevice(const uint8_t* device_id, char* out) {
    static const char digits[] = "0123456789ABCDEF";
    for (size_t i = 0; i < 6; ++i) {
        out[3 * i] = digits[device_id[i] >> 4];
        out[3 * i + 1] = digits[device_id[i] & 15u];
        if (i < 5) out[3 * i + 2] = ':';
    }
    out[17] = '\0';
}

}  // namespace r3_ble
