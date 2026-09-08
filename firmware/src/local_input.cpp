#include "local_input.h"

namespace local_input {
void begin() {}
bool available() { return false; }
bool poll(Event& event) {
    event.action = Action::None;
    return false;
}
}  // namespace local_input
