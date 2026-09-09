#include "r3_ble_receiver.h"

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

#define CHECK(condition) do { if (!(condition)) { \
    std::cerr << "line " << __LINE__ << ": " << #condition << '\n'; \
    std::exit(1); } } while (false)

using namespace r3_ble;

static Identity source(uint32_t revision = 1) {
    Identity identity = {{2,0,0,0,0,0xa5}, 0x0123456789abcdefULL, revision};
    return identity;
}
static Beacon beacon(uint32_t sequence, uint64_t capture, uint32_t revision = 1,
                     bool utc_valid = true) {
    Beacon value = {{2,0,0,0,0,0xa5}, 0x0123456789abcdefULL, revision, sequence,
                    capture, 1788912000u, uint32_t(capture / 1000), utc_valid};
    return value;
}
static ReceiveResult send(Receiver& receiver, const Beacon& value, uint64_t receive) {
    uint8_t bytes[kBeaconBytes];
    encodeBeacon(value, bytes);
    return receiver.observe(bytes, sizeof(bytes), receive);
}

static void bindingTests() {
    Receiver r;
    CHECK(!r.connected() && !r.hasAccepted() && r.segment() == 0);
    CHECK(send(r, beacon(1, 900), 1000) == ReceiveResult::Disconnected);
    CHECK(r.counters().disconnected_packets == 1);
    r.bind(source());
    CHECK(r.connected() && !r.hasAccepted() && r.segment() == 1);
    CHECK(send(r, beacon(1, 900), 1000) == ReceiveResult::Accepted);
    CHECK(r.lastAccepted().connection_segment == 1);
    CHECK(r.lastAccepted().local_receive_us == 1000);
    CHECK(r.fresh(1000) && r.utcEvidenceEligible(1000));

    Beacon foreign = beacon(2, 1900, 1, false);
    foreign.device_id[5] ^= 1;
    CHECK(send(r, foreign, 2000) == ReceiveResult::IdentityMismatch);
    CHECK(r.utcEvidenceEligible(2000)); // Unselected sender cannot revoke UTC.
    foreign = beacon(2, 1900, 1, false);
    ++foreign.boot_id;
    CHECK(send(r, foreign, 2000) == ReceiveResult::BootMismatch);
    CHECK(r.utcEvidenceEligible(2000)); // New boot needs a new identity binding.
    uint8_t bytes[kBeaconBytes];
    encodeBeacon(beacon(2, 1900, 1, false), bytes);
    bytes[60] ^= 1;
    CHECK(r.observe(bytes, sizeof(bytes), 2000) == ReceiveResult::Malformed);
    CHECK(r.utcEvidenceEligible(2000)); // Bad checksum carries no evidence.
    CHECK(r.malformed() == 3 && r.counters().accepted == 1);
    CHECK(r.lastAccepted().beacon.sequence == 1);
    CHECK(r.fresh(1000 + r3_time::kStaleAfterUs - 1));
    CHECK(!r.fresh(1000 + r3_time::kStaleAfterUs));
    CHECK(!r.utcEvidenceEligible(1000 + r3_time::kStaleAfterUs));
    CHECK(!r.fresh(999));
    std::cout << "BINDING PASS\n";
}

static void revisionTests() {
    Receiver r;
    r.bind(source(7));
    // Real race: RTC correction after identity read but before first notify.
    CHECK(send(r, beacon(42, 900, 8), 1000) == ReceiveResult::Accepted);
    CHECK(r.segment() == 2 && r.identity().clock_revision == 8);
    CHECK(r.lastAccepted().beacon.sequence == 42 && r.utcEvidenceEligible(1000));
    CHECK(send(r, beacon(43, 1900, 8), 2000) == ReceiveResult::Accepted);
    CHECK(r.segment() == 2);
    CHECK(send(r, beacon(44, 2900, 7), 3000) == ReceiveResult::RevisionRejected);
    CHECK(r.segment() == 2 && r.identity().clock_revision == 8);
    // Claiming a newer revision cannot make an old/duplicate sequence new.
    CHECK(send(r, beacon(43, 2900, 9), 3000) == ReceiveResult::RevisionRejected);
    CHECK(send(r, beacon(42, 2900, 9), 3000) == ReceiveResult::RevisionRejected);
    CHECK(r.lastAccepted().beacon.sequence == 43 && r.segment() == 2);
    // Revision transitions do not excuse source/local monotonic regressions.
    CHECK(send(r, beacon(44, 1800, 9), 3000) == ReceiveResult::CaptureRegression);
    CHECK(send(r, beacon(44, 2900, 9), 1999) == ReceiveResult::LocalClockRegression);
    CHECK(r.counters().local_clock_regressions == 1);
    CHECK(r.identity().clock_revision == 8 && r.segment() == 2);
    CHECK(send(r, beacon(44, 2900, 9), 3000) == ReceiveResult::Accepted);
    CHECK(r.segment() == 3 && r.identity().clock_revision == 9);
    CHECK(r.counters().accepted == 3 && r.counters().missing_sequences == 0);
    CHECK(r.lastAccepted().connection_segment == 3);

    r.bind(source(UINT32_MAX));
    const uint64_t segment = r.segment();
    CHECK(send(r, beacon(1, 100, 0), 5000) == ReceiveResult::Accepted);
    CHECK(r.identity().clock_revision == 0 && r.segment() == segment + 1);
    CHECK(send(r, beacon(2, 200, UINT32_MAX), 6000) == ReceiveResult::RevisionRejected);
    CHECK(send(r, beacon(2, 200, 0x80000000u), 6000) == ReceiveResult::RevisionRejected);
    CHECK(r.identity().clock_revision == 0 && r.segment() == segment + 1);
    std::cout << "REVISION PASS\n";
}

static void utcTests() {
    Receiver r;
    r.bind(source());
    CHECK(send(r, beacon(10, 900), 1000) == ReceiveResult::Accepted);
    // Reordered invalid evidence is rejected, but its UTC invalidation sticks.
    CHECK(send(r, beacon(9, 800, 1, false), 2000) == ReceiveResult::CaptureRegression);
    CHECK(!r.utcEvidenceEligible(2000) && r.fresh(2000));
    CHECK(send(r, beacon(10, 900), 2100) == ReceiveResult::Duplicate);
    CHECK(!r.utcEvidenceEligible(2100));
    CHECK(send(r, beacon(11, 1900), 2200) == ReceiveResult::Accepted);
    CHECK(r.utcEvidenceEligible(2200));

    CHECK(send(r, beacon(12, 2900, 1, false), 3200) == ReceiveResult::AcceptedTimeInvalid);
    CHECK(r.fresh(3200) && !r.utcEvidenceEligible(3200));
    CHECK(send(r, beacon(12, 2900), 3300) == ReceiveResult::Duplicate);
    CHECK(!r.utcEvidenceEligible(3300));
    CHECK(send(r, beacon(13, 3900), 4200) == ReceiveResult::Accepted);
    CHECK(r.utcEvidenceEligible(4200));

    // Invalid evidence from an older revision also cannot be undone by replay.
    CHECK(send(r, beacon(14, 4900, 2), 5200) == ReceiveResult::Accepted);
    CHECK(send(r, beacon(15, 4900, 1, false), 5300) == ReceiveResult::RevisionRejected);
    CHECK(!r.utcEvidenceEligible(5300));
    CHECK(send(r, beacon(14, 4900, 2), 5400) == ReceiveResult::Duplicate);
    CHECK(!r.utcEvidenceEligible(5400));
    CHECK(send(r, beacon(15, 5900, 2), 6200) == ReceiveResult::Accepted);
    CHECK(r.utcEvidenceEligible(6200));
    CHECK(r.lastAccepted().local_receive_us == 6200);
    CHECK(send(r, beacon(15, 5900, 2), 6200 + r3_time::kStaleAfterUs) == ReceiveResult::Duplicate);
    CHECK(!r.fresh(6200 + r3_time::kStaleAfterUs));
    std::cout << "UTC PASS\n";
}

static void sequenceAndReconnectTests() {
    Receiver r;
    r.bind(source());
    const uint64_t large = 9007199254740993ULL;
    CHECK(send(r, beacon(UINT32_MAX - 1, large), large + 100) == ReceiveResult::Accepted);
    CHECK(send(r, beacon(UINT32_MAX, large + 1), large + 101) == ReceiveResult::Accepted);
    CHECK(send(r, beacon(1, large + 2), large + 102) == ReceiveResult::Accepted);
    CHECK(r.counters().missing_sequences == 0); // MAX -> 1 skips zero.
    CHECK(send(r, beacon(3, large + 3), large + 103) == ReceiveResult::Accepted);
    CHECK(r.counters().missing_sequences == 1);
    CHECK(send(r, beacon(3, large + 3), large + 104) == ReceiveResult::Duplicate);
    CHECK(send(r, beacon(UINT32_MAX, large + 3), large + 105) == ReceiveResult::OutOfOrder);
    CHECK(send(r, beacon(2147483651u, large + 3), large + 106) == ReceiveResult::OutOfOrder);
    CHECK(r.counters().duplicates == 1 && r.counters().out_of_order == 2);
    CHECK(r.lastAccepted().beacon.capture_us == large + 3);
    CHECK(r.lastAccepted().local_receive_us == large + 103);

    r.disconnect();
    CHECK(!r.connected() && r.hasAccepted());
    CHECK(!r.fresh(large + 107) && !r.utcEvidenceEligible(large + 107));
    CHECK(send(r, beacon(4, large + 4), large + 107) == ReceiveResult::Disconnected);
    CHECK(r.counters().disconnected_packets == 1);
    const uint64_t prior = r.segment();
    r.bind(source());
    CHECK(r.segment() == prior + 1 && !r.hasAccepted());
    CHECK(send(r, beacon(100000, large + 100000), large + 100100) == ReceiveResult::Accepted);
    CHECK(r.counters().missing_sequences == 1); // no guessed gap across reconnect
    CHECK(r.counters().accepted == 5);
    CHECK(r.lastAccepted().connection_segment == prior + 1);

    Identity reboot = source();
    ++reboot.boot_id;
    r.bind(reboot);
    Beacon restarted = beacon(1, 100);
    restarted.boot_id = reboot.boot_id;
    CHECK(send(r, restarted, large + 200000) == ReceiveResult::Accepted);
    CHECK(r.lastAccepted().beacon.capture_us == 100); // source reboot is explicit
    CHECK(r.counters().missing_sequences == 1);
    std::cout << "RECONNECT PASS\n";
}

int main(int argc, char** argv) {
    CHECK(argc == 2);
    const std::string mode(argv[1]);
    if (mode == "binding") bindingTests();
    else if (mode == "revision") revisionTests();
    else if (mode == "utc") utcTests();
    else if (mode == "reconnect") sequenceAndReconnectTests();
    else return 2;
    return 0;
}
