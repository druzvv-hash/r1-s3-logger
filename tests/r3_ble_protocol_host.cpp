#include "r3_ble_protocol.h"

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

#define CHECK(condition) do { if (!(condition)) { \
    std::cerr << "line " << __LINE__ << ": " << #condition << '\n'; \
    std::exit(1); } } while (false)

using namespace r3_ble;

// Independently generated with Python struct.pack('<...') and zlib.crc32.
// 02:00:00:00:00:A5 is a synthetic locally administered address.
static const uint8_t goldenIdentity[kIdentityBytes] = {
    0x52,0x33,0x54,0x49,0x01,0x01,0x24,0x00,0x02,0x00,0x00,0x00,
    0x00,0xa5,0x03,0x01,0xef,0xcd,0xab,0x89,0x67,0x45,0x23,0x01,
    0xd4,0xc3,0xb2,0xa1,0x43,0x00,0x00,0x00,0x44,0x97,0xe7,0x7c
};
static const uint8_t goldenBeacon[kBeaconBytes] = {
    0x52,0x33,0x54,0x4d,0x01,0x02,0x40,0x00,0x02,0x00,0x00,0x00,
    0x00,0xa5,0x03,0x00,0xef,0xcd,0xab,0x89,0x67,0x45,0x23,0x01,
    0xd4,0xc3,0xb2,0xa1,0x98,0xba,0xdc,0xfe,0x01,0x00,0x00,0x00,
    0x00,0x00,0x20,0x00,0x34,0xbc,0x12,0x6a,0xef,0xcd,0xab,0x89,
    0xff,0xff,0xff,0xff,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x17,0xe4,0xc4,0x38
};

static Identity identityValue() {
    Identity value = {{2,0,0,0,0,0xa5}, 0x0123456789abcdefULL, 0xa1b2c3d4u};
    return value;
}
static Beacon beaconValue() {
    Beacon value = {{2,0,0,0,0,0xa5}, 0x0123456789abcdefULL, 0xa1b2c3d4u,
        0xfedcba98u, 0x0020000000000001ULL, 0x6a12bc34u, 0x89abcdefu, true};
    return value;
}
static bool equalIdentity(const Identity& a, const Identity& b) {
    return sameDevice(a.device_id, b.device_id) && a.boot_id == b.boot_id &&
        a.clock_revision == b.clock_revision;
}
static bool equalBeacon(const Beacon& a, const Beacon& b) {
    return sameDevice(a.device_id, b.device_id) && a.boot_id == b.boot_id &&
        a.clock_revision == b.clock_revision && a.sequence == b.sequence &&
        a.capture_us == b.capture_us && a.unix_s == b.unix_s &&
        a.last_tick_ms == b.last_tick_ms && a.utc_valid == b.utc_valid;
}
static void rejectIdentity(const uint8_t* bytes, size_t length) {
    const Identity before = identityValue();
    Identity out = before;
    CHECK(!decodeIdentity(bytes, length, out));
    CHECK(equalIdentity(out, before));
}
static void rejectBeacon(const uint8_t* bytes, size_t length) {
    const Beacon before = beaconValue();
    Beacon out = before;
    CHECK(!decodeBeacon(bytes, length, out));
    CHECK(equalBeacon(out, before));
}
static void fixCrc(uint8_t* bytes, size_t length) {
    // Explicit storage independent of the codec's endian helpers.
    const uint32_t crc = crc32(bytes, length - 4);
    for (size_t i = 0; i < 4; ++i) bytes[length - 4 + i] = uint8_t(crc >> (8 * i));
}

static void goldenTests() {
    uint8_t identity[kIdentityBytes + 2];
    std::memset(identity, 0xa5, sizeof(identity));
    encodeIdentity(identityValue(), identity + 1);
    CHECK(identity[0] == 0xa5 && identity[sizeof(identity) - 1] == 0xa5);
    CHECK(std::memcmp(identity + 1, goldenIdentity, kIdentityBytes) == 0);
    Identity decodedIdentity = {};
    CHECK(decodeIdentity(goldenIdentity, kIdentityBytes, decodedIdentity));
    CHECK(equalIdentity(decodedIdentity, identityValue()));
    CHECK(decodeIdentity(identity + 1, kIdentityBytes, decodedIdentity)); // unaligned

    uint8_t beacon[kBeaconBytes + 2];
    std::memset(beacon, 0xa5, sizeof(beacon));
    encodeBeacon(beaconValue(), beacon + 1);
    CHECK(beacon[0] == 0xa5 && beacon[sizeof(beacon) - 1] == 0xa5);
    CHECK(std::memcmp(beacon + 1, goldenBeacon, kBeaconBytes) == 0);
    Beacon decodedBeacon = {};
    CHECK(decodeBeacon(goldenBeacon, kBeaconBytes, decodedBeacon));
    CHECK(equalBeacon(decodedBeacon, beaconValue()));
    CHECK(decodedBeacon.capture_us == 9007199254740993ULL); // > 2^53, no float
    CHECK(decodeBeacon(beacon + 1, kBeaconBytes, decodedBeacon));
    CHECK(crc32(reinterpret_cast<const uint8_t*>("123456789"), 9) == 0xcbf43926u);
    CHECK(crc32(nullptr, 0) == 0);
    std::cout << "GOLDEN PASS\n";
}

static void strictTests() {
    for (size_t n = 0; n < kIdentityBytes; ++n) rejectIdentity(goldenIdentity, n);
    for (size_t n = 0; n < kBeaconBytes; ++n) rejectBeacon(goldenBeacon, n);
    rejectIdentity(nullptr, kIdentityBytes);
    rejectBeacon(nullptr, kBeaconBytes);
    rejectIdentity(goldenIdentity, size_t(-1));
    rejectBeacon(goldenBeacon, size_t(-1));
    uint8_t identity[kIdentityBytes + 1] = {};
    uint8_t beacon[kBeaconBytes + 1] = {};
    std::memcpy(identity, goldenIdentity, kIdentityBytes);
    std::memcpy(beacon, goldenBeacon, kBeaconBytes);
    rejectIdentity(identity, sizeof(identity));
    rejectBeacon(beacon, sizeof(beacon));

    // Every individual bit error, including the CRC itself, must be rejected.
    for (size_t pos = 0; pos < kIdentityBytes; ++pos) {
        for (unsigned bit = 0; bit < 8; ++bit) {
            std::memcpy(identity, goldenIdentity, kIdentityBytes);
            identity[pos] ^= uint8_t(1u << bit);
            rejectIdentity(identity, kIdentityBytes);
        }
    }
    for (size_t pos = 0; pos < kBeaconBytes; ++pos) {
        for (unsigned bit = 0; bit < 8; ++bit) {
            std::memcpy(beacon, goldenBeacon, kBeaconBytes);
            beacon[pos] ^= uint8_t(1u << bit);
            rejectBeacon(beacon, kBeaconBytes);
        }
    }

    // Semantic checks must still hold when an unsupported sender computes a
    // valid checksum. Mutate all framing/role/capability/reserved bytes.
    const size_t identityOffsets[] = {0,1,2,3,4,5,6,7,14,15,28,29,30,31};
    for (size_t pos : identityOffsets) {
        for (unsigned value = 0; value < 256; ++value) {
            if (value == goldenIdentity[pos]) continue;
            std::memcpy(identity, goldenIdentity, kIdentityBytes);
            identity[pos] = uint8_t(value);
            fixCrc(identity, kIdentityBytes);
            rejectIdentity(identity, kIdentityBytes);
        }
    }
    const size_t beaconOffsets[] = {0,1,2,3,4,5,6,7,15,48,49,50,51,
                                   52,53,54,55,56,57,58,59};
    for (size_t pos : beaconOffsets) {
        for (unsigned value = 0; value < 256; ++value) {
            if (value == goldenBeacon[pos]) continue;
            std::memcpy(beacon, goldenBeacon, kBeaconBytes);
            beacon[pos] = uint8_t(value);
            fixCrc(beacon, kBeaconBytes);
            rejectBeacon(beacon, kBeaconBytes);
        }
    }
    for (unsigned flags = 0; flags < 256; ++flags) {
        std::memcpy(beacon, goldenBeacon, kBeaconBytes);
        beacon[14] = uint8_t(flags);
        fixCrc(beacon, kBeaconBytes);
        if (flags == 2 || flags == 3) {
            Beacon value = {};
            CHECK(decodeBeacon(beacon, kBeaconBytes, value));
            CHECK(value.utc_valid == (flags == 3));
        } else rejectBeacon(beacon, kBeaconBytes);
    }
    std::memcpy(beacon, goldenBeacon, kBeaconBytes);
    std::memset(beacon + 28, 0, 4); // sequence zero is not emitted by R3
    fixCrc(beacon, kBeaconBytes);
    rejectBeacon(beacon, kBeaconBytes);
    std::cout << "STRICT PASS\n";
}

static void boundaryTests() {
    Identity identity = {};
    uint8_t encodedIdentity[kIdentityBytes];
    encodeIdentity(identity, encodedIdentity);
    Identity outIdentity = identityValue();
    CHECK(decodeIdentity(encodedIdentity, sizeof(encodedIdentity), outIdentity));
    CHECK(equalIdentity(identity, outIdentity));
    std::memset(identity.device_id, 0xff, 6);
    identity.boot_id = UINT64_MAX;
    identity.clock_revision = UINT32_MAX;
    encodeIdentity(identity, encodedIdentity);
    CHECK(decodeIdentity(encodedIdentity, sizeof(encodedIdentity), outIdentity));
    CHECK(equalIdentity(identity, outIdentity));

    Beacon beacon = {};
    beacon.sequence = 1;
    uint8_t encodedBeacon[kBeaconBytes];
    encodeBeacon(beacon, encodedBeacon);
    Beacon outBeacon = beaconValue();
    CHECK(decodeBeacon(encodedBeacon, sizeof(encodedBeacon), outBeacon));
    CHECK(equalBeacon(beacon, outBeacon));
    CHECK(encodedBeacon[14] == 2 && encodedBeacon[15] == 0);
    std::memset(beacon.device_id, 0xff, 6);
    beacon.boot_id = UINT64_MAX;
    beacon.clock_revision = UINT32_MAX;
    beacon.sequence = UINT32_MAX;
    beacon.capture_us = UINT64_MAX;
    beacon.unix_s = UINT32_MAX;
    beacon.last_tick_ms = UINT32_MAX;
    beacon.utc_valid = true;
    encodeBeacon(beacon, encodedBeacon);
    CHECK(decodeBeacon(encodedBeacon, sizeof(encodedBeacon), outBeacon));
    CHECK(equalBeacon(beacon, outBeacon));
    // Legacy invalid UTC is still transport evidence, not a malformed frame.
    beacon.utc_valid = false;
    encodeBeacon(beacon, encodedBeacon);
    CHECK(decodeBeacon(encodedBeacon, sizeof(encodedBeacon), outBeacon));
    CHECK(equalBeacon(beacon, outBeacon));
    std::cout << "BOUNDARY PASS\n";
}

static void helperTests() {
    CHECK(kIdentityBytes == 36 && kBeaconBytes == 64);
    CHECK(kMinMtu == 67 && kPreferredMtu == 128);
    for (unsigned mtu = 0; mtu <= UINT16_MAX; ++mtu)
        CHECK(supportsMtu(uint16_t(mtu)) == (mtu >= 67));
    CHECK(std::strcmp(kServiceUuid, "7e57a100-7a1e-4e54-a930-64e137711031") == 0);
    CHECK(std::strcmp(kIdentityUuid, "7e57a101-7a1e-4e54-a930-64e137711031") == 0);
    CHECK(std::strcmp(kBeaconUuid, "7e57a102-7a1e-4e54-a930-64e137711031") == 0);
    const uint8_t expected[] = {2,0xab,0xcd,0xef,0x12,0x34};
    uint8_t parsed[6] = {};
    CHECK(parseDevice("02:aB:cD:eF:12:34", parsed));
    CHECK(sameDevice(parsed, expected));
    char formatted[19];
    std::memset(formatted, '!', sizeof(formatted));
    formatDevice(parsed, formatted);
    CHECK(std::strcmp(formatted, "02:AB:CD:EF:12:34") == 0);
    CHECK(formatted[18] == '!');
    CHECK(!sameDevice(nullptr, expected));
    CHECK(!sameDevice(expected, nullptr));
    uint8_t different[6];
    std::memcpy(different, expected, 6);
    different[5] ^= 1;
    CHECK(!sameDevice(different, expected));
    const char* bad[] = {"", "02", "02:AB:CD:EF:12:3", "02:AB:CD:EF:12:345",
        "02-AB-CD-EF-12-34", "02:AB:CD:EF:12:3G", "02:AB:CD:EF:12:34 ",
        " 02:AB:CD:EF:12:34", "2:AB:CD:EF:12:34", "02:AB:CD:EF:12:34\n"};
    for (const char* value : bad) {
        CHECK(!parseDevice(value, parsed));
        CHECK(sameDevice(parsed, expected));
    }
    for (size_t n = 0; n < 17; ++n) {
        CHECK(!parseDevice(std::string("02:AB:CD:EF:12:34", n).c_str(), parsed));
        CHECK(sameDevice(parsed, expected));
    }
    CHECK(!parseDevice(nullptr, parsed));
    CHECK(sameDevice(parsed, expected));
    CHECK(!parseDevice("02:AB:CD:EF:12:34", nullptr));
    std::cout << "HELPER PASS\n";
}

int main(int argc, char** argv) {
    CHECK(argc == 2);
    const std::string mode(argv[1]);
    if (mode == "golden") goldenTests();
    else if (mode == "strict") strictTests();
    else if (mode == "boundary") boundaryTests();
    else if (mode == "helper") helperTests();
    else return 2;
    return 0;
}
