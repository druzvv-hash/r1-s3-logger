#include <Arduino.h>
#include "pins.h"

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("R1-S3 Logger: firmware scaffold");
    Serial.println("Hardware tests are not implemented yet.");
}

void loop() {
    delay(1000);
}
