#pragma once
#include "recording_buffer.h"

namespace recording {
constexpr uint32_t SD_BLOCK_BYTES = 8192;
// Preparation only. P4/P5 will attach the acquisition and recorder owners.
// Call before starting either task; repeated calls are allowed only at this
// quiescent stage and only for the same budget. No resizing an active queue.
bool prepareMemory(uint32_t queueBytes);
// Session admission only: both producer/consumer must be quiescent.
// Reallocate on an explicit applied budget change; retain old pools on failure.
bool resetMemory(uint32_t queueBytes);
bool memoryReady();
uint32_t allocatedQueueBytes();
SampleRing& sampleQueue();
BlockBuffer& outputBlock();
}  // namespace recording
