#pragma once
// Read-only DS3231 check. Call periodically; never sets time or clears OSF.
const char* pollRtc();
