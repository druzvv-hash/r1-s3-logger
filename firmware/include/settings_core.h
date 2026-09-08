#pragma once
#include "config_fields.h"
#include <vector>
#include <cstddef>
namespace settings {
using Bytes=std::vector<uint8_t>;
constexpr size_t slotSize=1536, footerOffset=1504;
bool validate(const Config&);
Bytes encode(const Config&);
bool decode(const Bytes&, Config&);
uint32_t crc32(const uint8_t*,size_t);
Bytes slot(const Config&,uint64_t);
enum class SlotState { invalid, valid, unsupported };
struct Slot { SlotState state=SlotState::invalid; uint64_t generation=0; Config config; Bytes payload; };
Slot inspect(const Bytes&);
struct Storage {
    virtual bool read(uint16_t,uint8_t*,size_t)=0;
    // One <=32-byte, page-contained write; must finish ACK polling before return.
    virtual bool write(uint16_t,const uint8_t*,size_t)=0;
    virtual ~Storage()=default;
};
struct Selection { bool blocked=false; int index=-1; Slot selected; };
Selection scan(Storage&);
bool save(Storage&,const Config&,Selection&);
bool equal(const Config&,const Config&);
uint16_t adcBits(const Config&); // shutdown mode; measurements explicitly trigger
uint32_t conversionUs(const Config&);
struct Registers {
    virtual bool read(uint8_t,uint32_t&)=0;
    virtual bool write(uint8_t,uint16_t)=0;
    virtual ~Registers()=default;
};
bool applyRegisters(Registers&,const Config&,bool& latchedFailure);
bool timingFeasible(const Config&); // representation/timing bound, not measured cadence
}
