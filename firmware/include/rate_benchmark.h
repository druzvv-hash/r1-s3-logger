#pragma once
#include "test_panel.h"
#if R1_BENCHMARK
bool rateBenchmarkStart(const char* argument, const char*& message, PanelAction action);
void rateBenchmarkStep(); // Hardware owner only, between conversions.
bool rateBenchmarkActive();
#else
inline void rateBenchmarkStep() {}
inline bool rateBenchmarkActive() { return false; }
#endif
