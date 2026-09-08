#pragma once
#include <Arduino.h>

namespace sd_files {
constexpr size_t CHUNK = 2048, PATH_BYTES = 240;
enum class Op { List, Next, Open, Read, Close, Check };
struct Request {
    Op op = Op::Check;
    uint32_t session = 0, offset = 0;
    char path[PATH_BYTES] = {};
};
struct Response {
    bool ok = false, more = false;
    uint32_t session = 0, size = 0, offset = 0, crc = 0;
    size_t count = 0;
    uint8_t data[CHUNK] = {};
    char json[6000] = {};
};
// Boot after the one-shot SD diagnostics. Only this task owns runtime SD access.
void begin();
bool request(const Request& input, Response& output);
String protocol(const char* command);
bool decodePath(const char* hex, char* output);
String encodePath(const char* path);
bool active();
}
