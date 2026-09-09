#include "r3_ble_trust.h"
#include "ecosystem_command_cache.h"
#include <assert.h>
#include <stdio.h>

int main() {
    r3_trust::Policy p; const uint8_t id[6] = {1, 2, 3, 4, 5, 6};
    memcpy(p.peer, id, 6); p.remote = true; p.addressType = 1;
    uint8_t bytes[r3_trust::kBytes]; r3_trust::encode(p, bytes);
    r3_trust::Policy out;
    assert(r3_trust::decode(bytes, sizeof(bytes), out));
    assert(out.remote && out.addressType == 1 && !memcmp(out.peer, id, 6));
    for (size_t i = 0; i < sizeof(bytes); ++i) {
        bytes[i] ^= 1; assert(!r3_trust::decode(bytes, sizeof(bytes), out)); bytes[i] ^= 1;
    }
    assert(!r3_trust::decode(bytes, sizeof(bytes)-1, out));
    bytes[4] = 2; r3_ble::detail::put32(bytes+20, r3_ble::crc32(bytes,20));
    assert(!r3_trust::decode(bytes, sizeof(bytes), out)); // valid-CRC future version fails closed
    r3_trust::encode(p, bytes); bytes[5] = 3;
    r3_ble::detail::put32(bytes+20,r3_ble::crc32(bytes,20));
    assert(!r3_trust::decode(bytes,sizeof(bytes),out)); // no unknown policy bits
    p.remote=false; r3_trust::encode(p,bytes); assert(r3_trust::decode(bytes,sizeof(bytes),out));
    assert(!out.remote); // time enrollment does not imply remote record authority

    ecosystem::Frame reply; reply.kind=ecosystem::Kind::TimeReply; reply.request=3;
    reply.stamp_us=10000000; reply.value_us=1789000000123456ULL;
    reply.flags=ecosystem::RtcValid; reply.detail=1500;
    assert(r3_trust::timeReplyEligible(reply,3,10000000,11000000));
    assert(!r3_trust::timeReplyEligible(reply,3,10000000,11000001));
    assert(!r3_trust::timeReplyEligible(reply,3,10000000,9999999));
    assert(!r3_trust::timeReplyEligible(reply,4,10000000,10500000));
    assert(!r3_trust::timeReplyEligible(reply,3,9999999,10500000));
    reply.detail=1501; assert(!r3_trust::timeReplyEligible(reply,3,10000000,10500000));
    reply.detail=0; reply.flags=0; assert(!r3_trust::timeReplyEligible(reply,3,10000000,10500000));
    reply.flags=ecosystem::RtcValid; reply.value_us=4102444800000000ULL;
    assert(!r3_trust::timeReplyEligible(reply,3,10000000,10500000));

    ecosystem::Frame command; command.kind=ecosystem::Kind::Command;
    command.request=7; command.stamp_us=20000000; command.ttl_ms=5000;
    assert(ecosystem::commandFresh(command,25000000));
    assert(!ecosystem::commandFresh(command,25000001));
    assert(!ecosystem::commandFresh(command,19999999));
    command.ttl_ms=5001; assert(!ecosystem::commandFresh(command,21000000));
    command.ttl_ms=5000;
    assert(r3_trust::commandForConnection(command,19000000,21000000));
    assert(!r3_trust::commandForConnection(command,20500000,21000000)); // old Status echo after reconnect
    assert(!r3_trust::commandForConnection(command,0,21000000)); // no active connection
    ecosystem::Frame status; status.flags=ecosystem::RtcSynced|ecosystem::Ready;
    uint8_t frameBytes[ecosystem::kFrameBytes]; ecosystem::encode(status,frameBytes);
    ecosystem::Frame decoded; assert(ecosystem::decode(frameBytes,sizeof(frameBytes),decoded));
    assert(decoded.flags & ecosystem::RtcSynced);
    frameBytes[84] |= 16; assert(!ecosystem::decode(frameBytes,sizeof(frameBytes),decoded));

    ecosystem::CommandCache cache;
    command.ttl_ms=5000; command.op=ecosystem::Op::Start; command.session=100;
    for (unsigned i=0; i<ecosystem::CommandCache::kCapacity; ++i) {
        auto* slot=cache.vacant(20000000); assert(slot);
        slot->used=true; slot->command=command; slot->command.request=i+1;
        slot->expiresUs=35000000;
    }
    assert(!cache.vacant(25000000)); // flood cannot evict a still-retryable START
    auto* original=cache.find(1); assert(original);
    auto duplicate=original->command; assert(ecosystem::sameCommand(original->command,duplicate));
    duplicate.session++; assert(!ecosystem::sameCommand(original->command,duplicate));
    duplicate=original->command; duplicate.op=ecosystem::Op::Stop;
    assert(!ecosystem::sameCommand(original->command,duplicate));
    duplicate=original->command; duplicate.sender_boot++;
    assert(!ecosystem::sameCommand(original->command,duplicate));
    assert(!cache.vacant(35000000));
    assert(cache.vacant(35000001)); // expired receipt only; its original wire command is already stale
    assert(!ecosystem::commandFresh(original->command,35000001));
    cache.reset(); assert(!cache.find(1)); assert(cache.vacant(20000000));
    // Admission rejection cannot change into execution when state/permission
    // changes before an identical request is retried.
    const ecosystem::Detail reasons[]={ecosystem::Detail::NotReady, ecosystem::Detail::Permission,
                       ecosystem::Detail::WrongSession, ecosystem::Detail::Clock,
                       ecosystem::Detail::QueueFull};
    for (auto reason : reasons) {
        cache.reset(); command.request=90; command.stamp_us=40000000; command.ttl_ms=5000;
        auto first=cache.admit(command,41000000);
        assert(first.admission==ecosystem::CommandCache::Admission::New);
        first.receipt->result.phase=ecosystem::Phase::Rejected;
        first.receipt->result.detail=uint32_t(reason);
        auto afterStateChange=cache.admit(command,42000000);
        assert(afterStateChange.admission==ecosystem::CommandCache::Admission::Replay);
        assert(afterStateChange.receipt->result.phase==ecosystem::Phase::Rejected);
        assert(afterStateChange.receipt->result.detail==uint32_t(reason));
        auto conflict=command; conflict.session++;
        assert(cache.admit(conflict,42000000).admission==ecosystem::CommandCache::Admission::Conflict);
    }
    // A full-cache rejection also stays rejected when old entries expire
    // before the newly rejected request does. Overflow never evicts live IDs.
    cache.reset();
    for (unsigned i=0;i<ecosystem::CommandCache::kCapacity;++i) {
        auto* slot=cache.vacant(49000000);assert(slot);slot->used=true;
        slot->command=command;slot->command.request=i+1;slot->expiresUs=50000000;
    }
    command.request=99;command.stamp_us=49000000;
    assert(cache.admit(command,49000000).admission==ecosystem::CommandCache::Admission::Full);
    assert(cache.vacant(51000000));
    assert(cache.admit(command,51000000).admission==ecosystem::CommandCache::Admission::Full);
    auto later=command;later.request=100;later.stamp_us=52000000;
    assert(cache.admit(later,52000000).admission==ecosystem::CommandCache::Admission::Full);
    assert(cache.admit(later,56000000).admission==ecosystem::CommandCache::Admission::Full);
    assert(!ecosystem::commandFresh(later,57000001));
    later.request=101;later.stamp_us=57000001;
    assert(cache.admit(later,57000001).admission==ecosystem::CommandCache::Admission::New);
    puts("PASS versioned trust, permission isolation, coarse-time freshness and command expiry");
}
