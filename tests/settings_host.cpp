#include "settings_core.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <cstring>
using namespace settings;
struct Memory:Storage {
 Bytes memory=Bytes(4096,0xff);int budget=-1,readFailure=-1,reads=0,writes=0;bool protect=false;
 bool read(uint16_t p,uint8_t* b,size_t n)override {if(reads++==readFailure)return false;assert(p+n<=memory.size());memcpy(b,memory.data()+p,n);return true;}
 bool write(uint16_t p,const uint8_t* b,size_t n)override {assert(n&&n<=32&&p%32+n<=32&&p+n<=3072);++writes;if(protect)return true;for(size_t i=0;i<n;++i){if(budget==0)return false;if(budget>0)--budget;memory[p+i]=b[i];}return true;}
 void seed(const Config& c,uint64_t gen=1,int at=0){auto b=slot(c,gen);std::copy(b.begin(),b.end(),memory.begin()+at*slotSize);}
};
struct Device:Registers {
 uint32_t regs[64]={};int writes=0,reads=0,failWrite=-1,failRead=-1;bool alwaysFail=false;
 Device(){regs[0x3e]=0x5449;regs[0x3f]=0x2281;regs[0]=0x80;regs[1]=0xfb68;}
 bool read(uint8_t reg,uint32_t& value)override {if(reads++==failRead)return false;value=regs[reg];return true;}
 bool write(uint8_t reg,uint16_t value)override {regs[reg]=value;return writes++!=failWrite&&!alwaysFail;}
};
void put(Bytes& b,size_t p,uint64_t v,int n){while(n--){b[p++]=v;v>>=8;}}
void fixCrc(Bytes& b){size_t n=b[20]|(b[21]<<8);put(b,24,0,4);auto crc=crc32(b.data(),32+n);put(b,24,crc,4);put(b,footerOffset+12,crc,4);}
int main(int argc,char** argv){
 if(argc==4&&std::string(argv[1])=="roundtrip"){
   std::ifstream in(argv[2],std::ios::binary);Bytes b((std::istreambuf_iterator<char>(in)),{});Config c;if(!decode(b,c))return 2;
   auto image=slot(c,1);std::ofstream out(argv[3],std::ios::binary);out.write(reinterpret_cast<const char*>(image.data()),image.size());return 0;
 }
 assert(crc32(reinterpret_cast<const uint8_t*>("123456789"),9)==0xcbf43926);
 Config a,b;b.i_gain=1.01;b.calibration_note="synthetic test";assert(timingFeasible(a));assert(adcBits(a)==0x0b68);assert(conversionUs(a)==3156);
 Config rate=a;rate.requested_rate_hz=200;
#if R1_BENCHMARK
 assert(validate(rate));rate.requested_rate_hz=1001;assert(!validate(rate));
#else
 assert(!validate(rate)); // Experimental rates cannot enter the normal build.
#endif
 Config invalid=a;invalid.average_code=7;assert(validate(invalid)&&!timingFeasible(invalid));invalid=a;invalid.i_gain=0;assert(!validate(invalid));invalid=a;invalid.calibration_utc="2025-02-29T00:00:00Z";assert(!validate(invalid));invalid.calibration_utc="2024-02-29T00:00:00Z";assert(validate(invalid));invalid.calibration_note=std::string("\xc0\x80",2);assert(!validate(invalid));
 Device device;bool latched=false;assert(applyRegisters(device,a,latched));assert(device.regs[0]==0&&device.regs[1]==0x0b68);
 device=Device{};device.failWrite=1;assert(!applyRegisters(device,a,latched)&&!latched);assert(device.regs[0]==0x80&&device.regs[1]==0xfb68);
 device=Device{};device.failRead=4;assert(!applyRegisters(device,a,latched)&&!latched);assert(device.regs[0]==0x80&&device.regs[1]==0xfb68);
 device=Device{};device.alwaysFail=true;assert(!applyRegisters(device,a,latched)&&latched);int count=device.writes;assert(!applyRegisters(device,a,latched)&&device.writes==count);
 latched=false;device=Device{};device.regs[0x3f]=0;assert(!applyRegisters(device,a,latched)&&device.writes==0);
 Memory initial;initial.seed(a);auto original=initial.memory;size_t totalWrites=64+32+encode(b).size();
 for(size_t cut=0;cut<=totalWrites;++cut){Memory m=initial;auto selected=scan(m);m.budget=int(cut);bool ok=save(m,b,selected);auto recovered=scan(m);assert(!recovered.blocked&&recovered.index>=0);assert(equal(recovered.selected.config,a)||equal(recovered.selected.config,b));if(ok)assert(equal(recovered.selected.config,b));assert(std::equal(original.begin(),original.begin()+slotSize,m.memory.begin()));assert(std::equal(original.begin()+3072,original.end(),m.memory.begin()+3072));}
 // Repeat cuts while overwriting a stale but committed inactive slot.
 for(size_t cut=0;cut<=totalWrites;++cut){Memory m;Config stale=a;stale.u_gain=.99;m.seed(a,4,0);m.seed(stale,3,1);auto old=m.memory;auto selected=scan(m);m.budget=int(cut);save(m,b,selected);auto recovered=scan(m);assert(!recovered.blocked&&recovered.index>=0);assert(equal(recovered.selected.config,a)||equal(recovered.selected.config,b));assert(std::equal(old.begin(),old.begin()+slotSize,m.memory.begin()));}
 for(int failedRead=0;failedRead<8;++failedRead){Memory m=initial;auto selected=scan(m);m.reads=0;m.readFailure=failedRead;save(m,b,selected);m.readFailure=-1;auto boot=scan(m);assert(boot.index>=0);assert(equal(boot.selected.config,a)||equal(boot.selected.config,b));}
 Memory m=initial;auto selected=scan(m);assert(save(m,a,selected)&&m.writes==0);m.protect=true;assert(!save(m,b,selected));m.protect=false;assert(save(m,b,selected));assert(selected.index==1&&selected.selected.generation==2);
 m=initial;m.seed(a,UINT64_MAX);selected=scan(m);assert(!save(m,b,selected)&&m.writes==0);
 m=initial;m.seed(b,1,1);selected=scan(m);assert(selected.blocked);assert(!save(m,a,selected)&&m.writes==0);
 auto future=slot(a,2);future[4]=2;fixCrc(future);m=initial;std::copy(future.begin(),future.end(),m.memory.begin()+slotSize);selected=scan(m);assert(selected.blocked&&!save(m,b,selected));
 future[24]^=1;assert(inspect(future).state==SlotState::invalid);
 future=slot(a,2);future[32]=99;fixCrc(future);assert(inspect(future).state==SlotState::unsupported);
 Memory empty;selected=scan(empty);assert(selected.index==-1&&!selected.blocked&&empty.writes==0);assert(save(empty,a,selected)&&selected.selected.generation==1);
 std::cout<<"P3 C++ PASS: codec, all write-byte cuts, read failures, write protection, unchanged saves, future schema, ambiguity, generation limit, reserve preservation\n";
}
