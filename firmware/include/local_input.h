#pragma once

#include <stdint.h>

namespace local_input {
// Shared UI actions; a future GPIO adapter translates encoder/button edges here.
enum class Action : uint8_t { None, Previous, Next, Select, Back, Start, Stop };
struct Event { Action action = Action::None; };

// Hardware is not installed. These functions deliberately never access GPIO,
// enable pull-ups/interrupts, or synthesize clicks. Menu dispatch follows in P4a.
void begin();
bool available();
bool poll(Event& event);
}  // namespace local_input
