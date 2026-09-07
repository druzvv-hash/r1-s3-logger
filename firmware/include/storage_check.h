#pragma once

const char* checkEepromReadOnly();
// Serial export only: reads twice, compares, then emits a complete hex image.
void dumpEepromReadOnly();
