#pragma once

namespace shunt {
// Owner-confirmed nameplate, 2026-09-07. Nominal values, not measured calibration.
constexpr double ratedMillivolts = 60.0;
constexpr double ratedAmps = 400.0;
constexpr double microOhms = ratedMillivolts * 1000.0 / ratedAmps;
constexpr double ampsFromMicrovolts(double microvolts) {
    return microvolts / microOhms;
}
static_assert(microOhms == 150.0, "60 mV / 400 A shunt");
static_assert(ampsFromMicrovolts(60000.0) == 400.0, "positive rated current");
static_assert(ampsFromMicrovolts(-60000.0) == -400.0, "negative rated current");
static_assert(ampsFromMicrovolts(0.0) == 0.0, "zero current");
static_assert(ampsFromMicrovolts(150.0) == 1.0, "one ampere");
}
