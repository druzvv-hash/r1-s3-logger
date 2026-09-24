#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Only the task creating this file sees the common-session creation date.
void gll_file_calendar_begin(uint64_t utc_us);
void gll_file_calendar_end(void);
#ifdef __cplusplus
}
#endif
