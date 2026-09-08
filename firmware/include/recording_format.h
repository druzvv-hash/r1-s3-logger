#pragma once
#include "recording_buffer.h"
#include "settings_core.h"
#include <string>

namespace recording {
// Portable SHA-256 for file integrity; not authentication.
class Sha256 {
public:
    Sha256();
    void add(const void* bytes, size_t size);
    std::string hex() const;
private:
    void transform(const uint8_t* block);
    uint32_t h_[8]; uint8_t tail_[64] = {}; uint64_t size_ = 0;
};
std::string jsonQuote(const std::string& text);
std::string configJson(const settings::Config& config);
std::string utcText(uint64_t epochUs);
// UTC in a FAT/Windows-safe name; keep the random suffix for same-second starts.
std::string sessionId(uint64_t utcUs, uint32_t randomHi, uint32_t randomLo);
struct SessionInfo {
    settings::Config config;
    uint64_t generation = 0, originUs = 0, utcUs = 0;
    uint32_t revision = 0;
    uint16_t manufacturer = 0, device = 0, adc = 0;
    double measuredHz = 0;
    std::string id, commit, version, description;
    bool dirty = false;
};
struct Totals { double whc=0, whd=0, ahc=0, ahd=0; };
struct SyncSink : ByteSink { virtual bool sync() = 0; };
// Sole storage-owner serializer. A failed sink/format operation latches failure;
// callers must retain the .part file and never finalize/retry it as a clean file.
class LogWriter {
public:
    LogWriter(BlockBuffer& block, SyncSink& sink) : block_(block), sink_(sink) {}
    void beginSession(const SessionInfo& info);
    bool beginPart(uint32_t part, const std::string& previousSha);
    bool row(const Sample& sample);
    bool checkpointAndSync();
    bool finish(bool rotation, std::string& wholeFileSha);
    bool failed() const { return failed_; }
    uint64_t bytes() const { return offset_; }
    uint64_t rows() const { return rows_; }
    uint64_t sessionRows() const { return sessionRows_; }
    const Totals& totals() const { return totals_; }
private:
    bool append(const std::string& bytes);
    bool checkpoint();
    SessionInfo info_;
    BlockBuffer& block_; SyncSink& sink_; Sha256 hash_;
    uint64_t offset_=0, rows_=0, sessionRows_=0, blockStart_=0, firstSeq_=0, lastSeq_=0;
    uint32_t crc_=0xffffffff, blockRows_=0;
    bool failed_=false, previous_=false, incomplete_=false;
    Sample prior_{}; double priorI_=0, priorP_=0;
    Totals totals_;
};
}
