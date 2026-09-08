#include "recording_memory.h"
#include <esp_heap_caps.h>
#include <new>

namespace recording {
namespace {
SampleRing queue;
BlockBuffer block;
uint32_t requestedBytes = 0, allocatedBytes = 0;
bool ready = false;
}

bool prepareMemory(uint32_t queueBytes) {
    if (ready) return queueBytes == requestedBytes;
    if (queueBytes < 4096 || queueBytes > 1048576) return false;
    const uint32_t capacity = capacityForBytes(queueBytes);
    const uint32_t bytes = capacity * sizeof(Sample);
    auto* slots = static_cast<Sample*>(heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (!slots) return false; // Never silently spend internal RAM on the large FIFO.
    auto* staging = static_cast<uint8_t*>(heap_caps_malloc(
        SD_BLOCK_BYTES, MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
    if (!staging) { heap_caps_free(slots); return false; }
    for (uint32_t i = 0; i < capacity; ++i) new (&slots[i]) Sample{};
    // Inputs have been validated, so both attachments are guaranteed to succeed.
    queue.attach(slots, capacity);
    block.attach(staging, SD_BLOCK_BYTES);
    requestedBytes = queueBytes;
    allocatedBytes = bytes;
    ready = true;
    return true;
}
bool memoryReady() { return ready; }
uint32_t allocatedQueueBytes() { return allocatedBytes; }
SampleRing& sampleQueue() { return queue; }
BlockBuffer& outputBlock() { return block; }
}  // namespace recording
