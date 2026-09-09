#include "r3_time_beacon.h"

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

#define CHECK(condition) do { if (!(condition)) { \
    std::cerr << "line " << __LINE__ << ": " << #condition << '\n'; \
    std::exit(1); } } while (false)

using namespace r3_time;

static ObserveResult send(Tracker& tracker, const char* line, uint64_t at) {
    return tracker.observe(line, std::strlen(line), at);
}

static void decoderTests() {
    Beacon packet = {};
    const char minimum[] = "$TMB,0,0,0,0\n";
    CHECK(decode(minimum, sizeof(minimum) - 1, packet) == DecodeResult::Ok);
    CHECK(packet.sequence == 0 && packet.unix_s == 0 && !packet.time_valid && packet.last_tick_ms == 0);
    const char maximum[] = "$TMB,4294967295,4294967295,1,4294967295\n";
    CHECK(sizeof(maximum) - 1 == kMaxBeaconBytes);
    CHECK(decode(maximum, sizeof(maximum) - 1, packet) == DecodeResult::Ok);
    CHECK(packet.sequence == UINT32_MAX && packet.unix_s == UINT32_MAX && packet.time_valid && packet.last_tick_ms == UINT32_MAX);

    // All truncations fail, leaving caller output unchanged. A buffer need not
    // have a NUL after LF; explicit length, not strlen, defines the packet.
    const char normal[] = "$TMB,123,1788912000,1,54321\n";
    for (size_t n = 0; n < sizeof(normal) - 1; ++n) {
        CHECK(decode(normal, n, packet) != DecodeResult::Ok);
        CHECK(packet.sequence == UINT32_MAX && packet.unix_s == UINT32_MAX);
    }
    CHECK(decode(normal, sizeof(normal) - 1, packet) == DecodeResult::Ok);
    CHECK(packet.sequence == 123 && packet.unix_s == 1788912000u && packet.last_tick_ms == 54321);
    const char nonterminated[] = {'$', 'T', 'M', 'B', ',', '1', ',', '2', ',', '1', ',', '3', '\n'};
    CHECK(decode(nonterminated, sizeof(nonterminated), packet) == DecodeResult::Ok);
    CHECK(packet.sequence == 1 && packet.unix_s == 2 && packet.last_tick_ms == 3);

    const char* bad[] = {
        "$TMB,4294967296,2,1,3\n", "$TMB,1,4294967296,1,3\n", "$TMB,1,2,1,4294967296\n",
        "$TMB,-1,2,1,3\n", "$TMB,+1,2,1,3\n", "$TMB, 1,2,1,3\n",
        "$TMB,01,2,1,3\n", "$TMB,1,02,1,3\n", "$TMB,1,2,1,03\n",
        "$TMB,,2,1,3\n", "$TMB,1,,1,3\n", "$TMB,1,2,1,\n",
        "$TMB,1,2,2,3\n", "$TMB,1,2,01,3\n", "$TMB,1,2,true,3\n",
        "$TMB,1,2,,3\n", "$TMB,1,2,-1,3\n", "$TMB,1,2,1,3,4\n",
        "$TMB,1,2,1,3\r\n", "$TMB,1,2,1,3\n\n", "$TMB,1,2,1,3\nX",
        "$TMB,1,2,1,3.0\n", "$tmb,1,2,1,3\n", " $TMB,1,2,1,3\n",
        "$TMB,1,2,3,1\n", // Alternate field ordering is never guessed.
    };
    for (const char* line : bad) {
        CHECK(decode(line, std::strlen(line), packet) != DecodeResult::Ok);
        CHECK(packet.sequence == 1 && packet.unix_s == 2 && packet.last_tick_ms == 3);
    }
    std::string embedded(normal, sizeof(normal) - 1);
    embedded[7] = '\0';
    CHECK(decode(embedded.data(), embedded.size(), packet) != DecodeResult::Ok);
    CHECK(decode(minimum, sizeof(minimum), packet) != DecodeResult::Ok); // trailing NUL
    CHECK(decode(nullptr, 13, packet) == DecodeResult::InvalidLength);
    CHECK(decode(minimum, size_t(-1), packet) == DecodeResult::InvalidLength);
    std::cout << "DECODER PASS\n";
}

static void trackerTests() {
    Tracker t;
    const uint64_t start = 17000000000000ULL; // Beyond micros32/millis32 uptime.
    CHECK(!t.connected() && !t.fresh(start) && !t.utcEvidenceEligible(start));
    CHECK(send(t, "$TMB,10,1788912000,1,1000\n", start) == ObserveResult::Disconnected);
    CHECK(t.counters().disconnected_packets == 1 && !t.hasDecoded());
    t.beginSegment(42);
    CHECK(t.connected() && !t.hasAccepted());
    CHECK(send(t, "$TMB,0,1788912000,1,1000\n", start) == ObserveResult::UnexpectedSequence);
    CHECK(t.hasDecoded() && !t.hasAccepted() && !t.utcEvidenceEligible(start));
    CHECK(t.counters().unexpected_sequences == 1);
    CHECK(send(t, "$TMB,10,1788912000,1,1000\n", start) == ObserveResult::Accepted);
    CHECK(t.lastAccepted().connection_segment == 42 && t.lastAccepted().local_receive_us == start);
    CHECK(t.utcEvidenceEligible(start) && t.fresh(start + kStaleAfterUs - 1));
    CHECK(!t.fresh(start + kStaleAfterUs) && !t.utcEvidenceEligible(start + kStaleAfterUs));
    CHECK(!t.fresh(start - 1));

    CHECK(send(t, "$TMB,10,1788912001,1,2000\n", start + 4000000) == ObserveResult::Duplicate);
    CHECK(send(t, "$TMB,9,1788912001,1,2000\n", start + 4000001) == ObserveResult::OutOfOrder);
    CHECK(send(t, "$TMB,1,2,2,3\n", start + 4000002) == ObserveResult::Malformed);
    CHECK(!t.fresh(start + kStaleAfterUs));
    CHECK(t.lastAccepted().local_receive_us == start && t.lastAccepted().beacon.unix_s == 1788912000u);
    CHECK(t.lastDecoded().beacon.sequence == 9 && t.counters().bad_packets == 1);
    CHECK(t.counters().duplicates == 1 && t.counters().out_of_order == 1);

    CHECK(send(t, "$TMB,13,1788912003,1,4000\n", start + 6000000) == ObserveResult::Accepted);
    CHECK(t.counters().missing_sequences == 2 && t.counters().accepted == 2);
    CHECK(t.utcEvidenceEligible(start + 6000000));
    CHECK(send(t, "$TMB,14,0,0,5000\n", start + 7000000) == ObserveResult::AcceptedTimeInvalid);
    CHECK(t.fresh(start + 7000000) && !t.utcEvidenceEligible(start + 7000000));
    CHECK(t.lastAccepted().beacon.unix_s == 0 && !t.lastAccepted().beacon.time_valid);
    CHECK(send(t, "$TMB,15,1788912005,1,6000\n", start + 8000000) == ObserveResult::Accepted);
    CHECK(t.utcEvidenceEligible(start + 8000000));

    // Conservative revocation also applies to invalid-time duplicate/reordered
    // evidence; valid duplicates cannot silently restore eligibility.
    CHECK(send(t, "$TMB,15,0,0,6000\n", start + 8000001) == ObserveResult::Duplicate);
    CHECK(!t.utcEvidenceEligible(start + 8000001));
    CHECK(send(t, "$TMB,15,1788912005,1,6000\n", start + 8000002) == ObserveResult::Duplicate);
    CHECK(!t.utcEvidenceEligible(start + 8000002));
    CHECK(send(t, "$TMB,16,1788912006,1,7000\n", start + 9000000) == ObserveResult::Accepted);
    CHECK(t.utcEvidenceEligible(start + 9000000));
    CHECK(send(t, "$TMB,17,1788912007,1,8000\n", start + 8999999) == ObserveResult::LocalClockRegression);
    CHECK(t.counters().local_clock_regressions == 1 && t.lastAccepted().beacon.sequence == 16);

    t.disconnect();
    CHECK(!t.utcEvidenceEligible(start + 9000001) && !t.fresh(start + 9000001));
    CHECK(t.hasAccepted() && t.lastAccepted().beacon.sequence == 16);
    CHECK(send(t, "$TMB,17,1788912007,1,8000\n", start + 10000000) == ObserveResult::Disconnected);
    t.beginSegment(43);
    CHECK(!t.hasAccepted() && !t.hasDecoded() && t.counters().disconnected_packets == 2);
    CHECK(send(t, "$TMB,1,1788912008,1,0\n", start + 11000000) == ObserveResult::Accepted);
    CHECK(t.lastAccepted().connection_segment == 43 && t.counters().missing_sequences == 2);

    // Sequence wrap and remote tick wrap are independent. A late pre-wrap
    // packet and an exactly half-range jump must not establish fresh time.
    t.beginSegment(44);
    CHECK(send(t, "$TMB,4294967294,1,1,4294967295\n", start) == ObserveResult::Accepted);
    CHECK(send(t, "$TMB,4294967295,1,1,0\n", start + 1) == ObserveResult::Accepted);
    CHECK(send(t, "$TMB,1,1,1,1\n", start + 2) == ObserveResult::Accepted);
    CHECK(t.counters().missing_sequences == 2); // MAX -> 1 skips zero on R3.
    CHECK(send(t, "$TMB,3,1,1,2\n", start + 3) == ObserveResult::Accepted);
    CHECK(t.counters().missing_sequences == 3);
    CHECK(send(t, "$TMB,4294967295,1,1,0\n", start + 4) == ObserveResult::OutOfOrder);
    CHECK(send(t, "$TMB,2147483651,1,1,0\n", start + 5) == ObserveResult::OutOfOrder);
    CHECK(t.lastAccepted().beacon.sequence == 3 && t.lastAccepted().local_receive_us == start + 3);
    CHECK(!t.fresh(start + 3 + kStaleAfterUs));

    // Age uses subtraction; no deadline overflow near uint64 maximum.
    t.beginSegment(45);
    CHECK(send(t, "$TMB,1,1,1,0\n", UINT64_MAX - 100) == ObserveResult::Accepted);
    CHECK(t.fresh(UINT64_MAX));
    CHECK(!t.fresh(0));
    std::cout << "TRACKER PASS\n";
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string mode(argv[1]);
    if (mode == "decoder") decoderTests();
    else if (mode == "tracker") trackerTests();
    else return 2;
}
