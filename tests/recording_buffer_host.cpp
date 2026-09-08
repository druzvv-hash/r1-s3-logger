#include "recording_buffer.h"
#include "recording_memory.h"
#include "local_input.h"
#include "esp_heap_caps.h"
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using namespace recording;
static unsigned allocations = 0, frees = 0, failAllocation = 0;
void* heap_caps_malloc(size_t n, uint32_t caps) {
    ++allocations;
    assert(caps == (allocations == 1 ? (MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)
        : (MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA | MALLOC_CAP_8BIT)));
    if (allocations == failAllocation) return nullptr;
    return std::malloc(n);
}
void heap_caps_free(void* p) { ++frees; std::free(p); }

static Sample sample(uint64_t seq) {
    Sample s{};
    s.seq = seq;
    s.t_us = seq * 20000 + 123;
    s.vshunt_raw = -static_cast<int32_t>(seq % 500000);
    s.vbus_raw = static_cast<uint32_t>(seq % 1000000);
    s.temp_raw = static_cast<int16_t>(seq % 32768);
    s.quality = static_cast<uint8_t>(seq % 32);
    s.raw_present = static_cast<uint8_t>(seq % 8);
    s.config_revision = static_cast<uint32_t>(seq >> 8);
    return s;
}
static void same(const Sample& a, const Sample& b) {
    assert(std::memcmp(&a, &b, sizeof(a)) == 0);
}

static void ringTests() {
    Sample slots[8], out{};
    SampleRing q;
    assert(!q.tryPush(sample(0)) && !q.peek(out) && !q.consume());
    assert(!q.attach(nullptr, 8) && !q.attach(slots, 0) && !q.attach(slots, 7));
    assert(capacityForBytes(0) == 0 && capacityForBytes(31) == 0);
    assert(capacityForBytes(65536) == 2048 && capacityForBytes(1048576) == 32768);
    assert(capacityForBytes(65535) == 1024);
    // Exercise counter wrap, full->empty wrap and repeated non-consuming peeks.
    assert(q.attach(slots, 8, UINT32_MAX - 3));
    for (uint64_t base = 0; base < 8000; base += 8) {
        for (unsigned i = 0; i < 8; ++i) assert(q.tryPush(sample(base + i)));
        assert(q.queuedApprox() == 8 && !q.tryPush(sample(999999)));
        for (unsigned i = 0; i < 8; ++i) {
            assert(q.peek(out)); same(out, sample(base + i));
            assert(q.peek(out)); same(out, sample(base + i));
            assert(q.consume());
        }
        assert(q.queuedApprox() == 0 && !q.consume() && !q.peek(out));
    }
    assert(q.highWater() == 8 && q.overflows() == 1000);

    // Concurrent producer/consumer: full retries, wrap and deliberate slow reads.
    std::vector<Sample> memory(128);
    SampleRing threaded;
    assert(threaded.attach(memory.data(), 128, UINT32_MAX - 20));
    constexpr uint64_t total = 400000;
    std::atomic<bool> done{false};
    std::thread producer([&] {
        for (uint64_t i = 0; i < total; ++i)
            while (!threaded.tryPush(sample(i))) std::this_thread::yield();
        done.store(true, std::memory_order_release);
    });
    std::thread consumer([&] {
        Sample v{};
        for (uint64_t i = 0; i < total; ++i) {
            while (!threaded.peek(v)) std::this_thread::yield();
            same(v, sample(i));
            if (i % 73 == 0) { std::this_thread::yield(); assert(threaded.peek(v)); same(v, sample(i)); }
            assert(threaded.consume());
        }
    });
    while (!done.load(std::memory_order_acquire)) {
        assert(threaded.queuedApprox() <= 128);
        std::this_thread::yield();
    }
    producer.join(); consumer.join();
    assert(threaded.queuedApprox() == 0 && threaded.highWater() <= 128);
}

struct Sink : ByteSink {
    std::vector<uint8_t> bytes;
    size_t limit = SIZE_MAX;
    unsigned calls = 0;
    bool invalid = false;
    size_t write(const uint8_t* p, size_t n) override {
        ++calls;
        if (invalid) return n + 1;
        const size_t accepted = std::min(n, limit);
        bytes.insert(bytes.end(), p, p + accepted);
        return accepted;
    }
};

static void blockTests() {
    uint8_t bytes[8192];
    std::vector<uint8_t> input(8192 * 3 + 199);
    for (size_t i = 0; i < input.size(); ++i) input[i] = static_cast<uint8_t>(i * 71);
    BlockBuffer b; Sink sink;
    assert(!b.append(input.data(), 1) && !b.drain(sink));
    assert(!b.attach(nullptr, 8192) && !b.attach(bytes, 511));
    assert(b.attach(bytes, 8192));
    // Variable producer chunks split only at staging capacity; identical byte stream.
    size_t offset = 0;
    while (offset < input.size()) {
        size_t n = std::min<size_t>(137, input.size() - offset);
        n = std::min(n, b.freeBytes());
        assert(b.append(input.data() + offset, n));
        offset += n;
        assert(b.drain(sink));
    }
    assert(sink.calls == 3 && b.pending() == 199);
    assert(b.drain(sink, true) && b.pending() == 0);
    assert(sink.bytes == input && sink.calls == 4 && b.acceptedBytes() == input.size());
    assert(b.drain(sink, true) && sink.calls == 4);

    // Every possible short write boundary: retain suffix and never retry silently.
    for (size_t cut = 0; cut < 512; ++cut) {
        BlockBuffer f; Sink failing;
        assert(f.attach(bytes, 512));
        assert(f.append(input.data(), 512));
        assert(!f.append(input.data(), 1) && f.pending() == 512);
        failing.limit = cut;
        assert(!f.drain(failing));
        assert(f.fault() == WriteFault::ShortWrite && f.pending() == 512 - cut);
        assert(f.acceptedBytes() == cut);
        assert(std::equal(f.pendingData(), f.pendingData() + f.pending(), input.data() + cut));
        assert(!f.drain(failing, true) && !f.append(input.data(), 1));
        assert(failing.calls == 1 && failing.bytes.size() == cut);
    }
    BlockBuffer invalid; Sink bad; bad.invalid = true;
    assert(invalid.attach(bytes, 512) && invalid.append(input.data(), 3));
    assert(!invalid.drain(bad, true) && invalid.fault() == WriteFault::InvalidCount);
    assert(invalid.pending() == 3 && invalid.acceptedBytes() == 0);

    // Downstream backpressure never consumes the source queue implicitly.
    Sample slots[2], out{}; SampleRing q;
    BlockBuffer full;
    assert(q.attach(slots, 2) && q.tryPush(sample(42)));
    assert(full.attach(bytes, 512) && full.append(input.data(), 512));
    assert(q.peek(out));
    assert(!full.append(reinterpret_cast<const uint8_t*>(&out), sizeof(out)));
    assert(q.queuedApprox() == 1 && q.peek(out)); same(out, sample(42));
}

int main(int argc, char** argv) {
    if (argc > 1) {
        const std::string mode = argv[1];
        if (mode == "psram-failure") failAllocation = 1;
        if (mode == "dma-failure") failAllocation = 2;
        assert(!prepareMemory(0) && !prepareMemory(1048577) && allocations == 0);
        const bool ready = prepareMemory(65536);
        if (failAllocation) {
            assert(!ready && !memoryReady() && allocatedQueueBytes() == 0);
            assert(sampleQueue().capacity() == 0);
            assert(allocations == failAllocation && frees == failAllocation - 1);
        } else {
            assert(ready && memoryReady() && allocatedQueueBytes() == 65536);
            assert(sampleQueue().capacity() == 2048 && outputBlock().freeBytes() == 8192);
            assert(prepareMemory(65536) && !prepareMemory(131072) && allocations == 2);
        }
        std::cout << "MEMORY PASS " << mode << '\n';
        return 0;
    }
    ringTests(); blockTests();
    local_input::begin();
    local_input::Event event; event.action = local_input::Action::Start;
    assert(!local_input::available() && !local_input::poll(event));
    assert(event.action == local_input::Action::None);
    std::cout << "BUFFER C++ PASS: FIFO concurrency/wrap/backpressure and all short-write cuts\n";
}
