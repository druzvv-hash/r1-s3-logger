#pragma once

// Ecosystem control v1. This extension does not alter the strict S1 time frames.
// Explicit little-endian serialization: never transmit a C++ structure layout.
#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace ecosystem {
constexpr char kUpstreamUuid[] = "7e57a103-7a1e-4e54-a930-64e137711031";
constexpr char kDownstreamUuid[] = "7e57a104-7a1e-4e54-a930-64e137711031";
constexpr size_t kFrameBytes = 96;
constexpr uint16_t kMinimumMtu = 99;
constexpr uint32_t kCommandTtlMs = 5000;
constexpr uint32_t kStatusFreshMs = 3000;
constexpr uint32_t kTimeRoundTripMaxMs = 1000;
constexpr uint32_t kTimeSourceAgeMaxMs = 1500;

enum class Kind : uint8_t { Hello = 1, Status = 2, Command = 3, Result = 4,
                            TimeRequest = 5, TimeReply = 6 };
enum class Op : uint8_t { None = 0, Start = 1, Stop = 2, Query = 3 };
enum class Phase : uint8_t { Unknown = 0, Idle = 1, Starting = 2,
    Recording = 3, Stopping = 4, Closed = 5, Error = 6, Rejected = 7, Accepted = 8 };
enum Flag : uint32_t { RemoteAllowed = 1u, Ready = 2u, RtcValid = 4u, RtcSynced = 8u };
enum class Detail : uint32_t { None = 0, Invalid = 1, Expired = 2,
    WrongBoot = 3, WrongSession = 4, NotReady = 5, Permission = 6,
    Busy = 7, QueueFull = 8, Conflict = 9, Storage = 10, Clock = 11,
    LinkLost = 12, Unsupported = 13 };

struct Frame {
  Kind kind = Kind::Status;
  Op op = Op::None;
  Phase phase = Phase::Unknown;
  uint8_t sender[6] = {};
  uint8_t target[6] = {};
  uint64_t sender_boot = 0;
  uint64_t target_boot = 0;
  uint64_t request = 0;
  uint64_t session = 0;
  uint64_t group = 0;
  // Status: sender monotonic time. Command: echo of target Status stamp.
  // TimeRequest/Reply: requester's monotonic send time, echoed unchanged.
  uint64_t stamp_us = 0;
  // TimeReply: coarse calendar time at reply construction in microseconds.
  uint64_t value_us = 0;
  uint32_t revision = 0;
  uint32_t ttl_ms = 0;
  uint32_t flags = 0;
  // Result: Detail; TimeReply: source RTC read age in milliseconds.
  uint32_t detail = 0;
};

inline void put(uint8_t *p, uint64_t value, size_t n) {
  for (size_t i = 0; i < n; ++i) { p[i] = uint8_t(value); value >>= 8; }
}
inline uint64_t get(const uint8_t *p, size_t n) {
  uint64_t value = 0;
  for (size_t i = 0; i < n; ++i) value |= uint64_t(p[i]) << (8 * i);
  return value;
}
inline void encode(const Frame &f, uint8_t out[kFrameBytes]) {
  memset(out, 0, kFrameBytes);
  memcpy(out, "ECO1", 4); out[4] = 1;
  out[5] = uint8_t(f.kind); out[6] = uint8_t(f.op); out[7] = uint8_t(f.phase);
  memcpy(out + 8, f.sender, 6); memcpy(out + 14, f.target, 6);
  put(out + 20, f.sender_boot, 8); put(out + 28, f.target_boot, 8);
  put(out + 36, f.request, 8); put(out + 44, f.session, 8);
  put(out + 52, f.group, 8); put(out + 60, f.stamp_us, 8);
  put(out + 68, f.value_us, 8); put(out + 76, f.revision, 4);
  put(out + 80, f.ttl_ms, 4); put(out + 84, f.flags, 4);
  put(out + 88, f.detail, 4);
}
inline bool decode(const uint8_t *in, size_t n, Frame &out) {
  if (!in || n != kFrameBytes || memcmp(in, "ECO1", 4) || in[4] != 1 ||
      in[5] < 1 || in[5] > 6 || in[6] > 3 || in[7] > 8 ||
      get(in + 92, 4) != 0 || (get(in + 84, 4) & ~uint64_t(15))) return false;
  Frame f;
  f.kind = Kind(in[5]); f.op = Op(in[6]); f.phase = Phase(in[7]);
  memcpy(f.sender, in + 8, 6); memcpy(f.target, in + 14, 6);
  f.sender_boot = get(in + 20, 8); f.target_boot = get(in + 28, 8);
  f.request = get(in + 36, 8); f.session = get(in + 44, 8);
  f.group = get(in + 52, 8); f.stamp_us = get(in + 60, 8);
  f.value_us = get(in + 68, 8); f.revision = uint32_t(get(in + 76, 4));
  f.ttl_ms = uint32_t(get(in + 80, 4)); f.flags = uint32_t(get(in + 84, 4));
  f.detail = uint32_t(get(in + 88, 4)); out = f; return true;
}
inline bool sameDevice(const uint8_t a[6], const uint8_t b[6]) {
  return memcmp(a, b, 6) == 0;
}
inline bool commandFresh(const Frame &f, uint64_t receiver_now_us) {
  return f.kind == Kind::Command && f.request && f.ttl_ms &&
      f.ttl_ms <= kCommandTtlMs && receiver_now_us >= f.stamp_us &&
      receiver_now_us - f.stamp_us <= uint64_t(f.ttl_ms) * 1000;
}
inline bool active(Phase p) {
  return p == Phase::Starting || p == Phase::Recording || p == Phase::Stopping;
}
inline bool startable(Phase p) { return p == Phase::Idle || p == Phase::Closed; }
inline const char *phaseName(Phase p) {
  switch (p) {
    case Phase::Idle: return "idle"; case Phase::Starting: return "starting";
    case Phase::Recording: return "recording"; case Phase::Stopping: return "stopping";
    case Phase::Closed: return "closed"; case Phase::Error: return "error";
    case Phase::Rejected: return "rejected"; case Phase::Accepted: return "accepted";
    default: return "unknown";
  }
}
}  // namespace ecosystem
