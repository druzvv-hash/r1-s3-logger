#pragma once
#include <stddef.h>
#include <stdint.h>
// Host-only allocation seam; firmware resolves the actual ESP-IDF header.
constexpr uint32_t MALLOC_CAP_SPIRAM = 1, MALLOC_CAP_INTERNAL = 2;
constexpr uint32_t MALLOC_CAP_DMA = 4, MALLOC_CAP_8BIT = 8;
void* heap_caps_malloc(size_t bytes, uint32_t caps);
void heap_caps_free(void* pointer);
