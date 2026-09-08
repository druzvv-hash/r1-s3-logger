#include "settings_core.h"
#include <cstring>
#include <cmath>
#include <algorithm>
#include <limits>
namespace settings {
namespace {
void put(Bytes& b,size_t p,uint64_t v,size_t n){for(size_t i=0;i<n;++i)b[p+i]=uint8_t(v>>(8*i));}
uint64_t get(const uint8_t* p,size_t n){uint64_t v=0;for(size_t i=0;i<n;++i)v|=uint64_t(p[i])<<(8*i);return v;}
bool utf8(const std::string& s){
    for(size_t i=0;i<s.size();){uint32_t cp=uint8_t(s[i++]);unsigned count=0;uint32_t min=0;
        if(!cp)return false;if(cp<128)continue;
        if(cp>=0xc2&&cp<=0xdf){count=1;cp&=31;min=128;}
        else if(cp>=0xe0&&cp<=0xef){count=2;cp&=15;min=2048;}
        else if(cp>=0xf0&&cp<=0xf4){count=3;cp&=7;min=65536;}else return false;
        while(count--){if(i==s.size()||(uint8_t(s[i])&0xc0)!=0x80)return false;cp=(cp<<6)|(uint8_t(s[i++])&63);}
        if(cp<min||cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff))return false;
    }return true;
}
bool validDate(const std::string& s){
    if(s.empty())return true;if(s.size()!=20||s[4]!='-'||s[7]!='-'||s[10]!='T'||s[13]!=':'||s[16]!=':'||s[19]!='Z')return false;
    for(size_t i=0;i<19;++i)if(i!=4&&i!=7&&i!=10&&i!=13&&i!=16&&(s[i]<'0'||s[i]>'9'))return false;
    auto num=[&](int p,int n){int v=0;while(n--)v=v*10+s[p++]-'0';return v;};
    const int y=num(0,4),m=num(5,2),d=num(8,2),days[]={31,28,31,30,31,30,31,31,30,31,30,31};
    return y>=1&&m>=1&&m<=12&&d>=1&&d<=days[m-1]+(m==2&&y%4==0&&(y%100!=0||y%400==0))&&num(11,2)<24&&num(14,2)<60&&num(17,2)<60;
}
void raw(Bytes& b,unsigned id,unsigned type,const uint8_t* p,size_t n){size_t pos=b.size();b.resize(pos+8);put(b,pos,id,2);b[pos+2]=type;put(b,pos+4,n,2);b.insert(b.end(),p,p+n);}
void append(Bytes& b,unsigned id,unsigned type,uint32_t v){Bytes r(4);put(r,0,v,4);raw(b,id,type,r.data(),4);}
void append(Bytes& b,unsigned id,unsigned type,int32_t v){append(b,id,type,uint32_t(v));}
void append(Bytes& b,unsigned id,unsigned type,double v){static_assert(sizeof(v)==8,"IEEE binary64 required");uint64_t u;memcpy(&u,&v,8);Bytes r(8);put(r,0,u,8);raw(b,id,type,r.data(),8);}
void append(Bytes& b,unsigned id,unsigned type,bool v){uint8_t r=v;raw(b,id,type,&r,1);}
void append(Bytes& b,unsigned id,unsigned type,const std::string& v){raw(b,id,type,reinterpret_cast<const uint8_t*>(v.data()),v.size());}
bool field(const Bytes& b,size_t& pos,unsigned id,unsigned type,const uint8_t*& p,size_t& n){
    if(pos+8>b.size()||get(&b[pos],2)!=id||b[pos+2]!=type||b[pos+3]||b[pos+6]||b[pos+7])return false;
    n=get(&b[pos+4],2);pos+=8;if(n>b.size()-pos)return false;p=b.data()+pos;pos+=n;return true;
}
bool take(const Bytes& b,size_t& pos,unsigned id,unsigned type,uint32_t& v){const uint8_t* p;size_t n;if(!field(b,pos,id,type,p,n)||n!=4)return false;v=get(p,4);return true;}
bool take(const Bytes& b,size_t& pos,unsigned id,unsigned type,int32_t& v){uint32_t u;if(!take(b,pos,id,type,u))return false;memcpy(&v,&u,4);return true;}
bool take(const Bytes& b,size_t& pos,unsigned id,unsigned type,double& v){const uint8_t* p;size_t n;if(!field(b,pos,id,type,p,n)||n!=8)return false;uint64_t u=get(p,8);memcpy(&v,&u,8);return true;}
bool take(const Bytes& b,size_t& pos,unsigned id,unsigned type,bool& v){const uint8_t* p;size_t n;if(!field(b,pos,id,type,p,n)||n!=1||*p>1)return false;v=*p;return true;}
bool take(const Bytes& b,size_t& pos,unsigned id,unsigned type,std::string& v){const uint8_t* p;size_t n;if(!field(b,pos,id,type,p,n))return false;v.assign(reinterpret_cast<const char*>(p),n);return true;}
}
#include "config_codec_generated.inc"
uint32_t crc32(const uint8_t* data,size_t n){uint32_t c=0xffffffff;while(n--){c^=*data++;for(unsigned j=0;j<8;++j)c=(c>>1)^((c&1)?0xedb88320:0);}return ~c;}
// Keep legacy-compatible values byte-identical; extended values protect rollback
// by declaring minor 1, which previous firmware treats as write-protected.
unsigned configMinor(const Config& c){return (c.requested_rate_hz==10||c.requested_rate_hz==50||c.requested_rate_hz==100)&&c.max_gap_us<=1000000?0:1;}
Bytes slot(const Config& c,uint64_t gen){
    const Bytes payload=encode(c);if(payload.empty()||payload.size()>1472||!gen)return {};
    Bytes out(slotSize,0xff);std::fill(out.begin(),out.begin()+32,0);memcpy(out.data(),"R1CF",4);put(out,4,1,2);put(out,6,configMinor(c),2);put(out,8,32,2);put(out,12,gen,8);put(out,20,payload.size(),4);std::copy(payload.begin(),payload.end(),out.begin()+32);
    uint32_t crc=crc32(out.data(),32+payload.size());put(out,24,crc,4);
    std::fill(out.begin()+footerOffset,out.end(),0);memcpy(out.data()+footerOffset,"RCMT",4);put(out,footerOffset+4,gen,8);put(out,footerOffset+12,crc,4);put(out,footerOffset+16,payload.size(),4);return out;
}
Slot inspect(const Bytes& b){
    Slot s;if(b.size()!=slotSize||memcmp(b.data(),"R1CF",4)||get(&b[8],2)!=32||get(&b[10],2)||get(&b[28],4))return s;
    const uint64_t gen=get(&b[12],8);const size_t n=get(&b[20],4);const uint32_t crc=get(&b[24],4);if(!gen||n>1472)return s;
    const auto* f=&b[footerOffset];if(memcmp(f,"RCMT",4)||get(f+4,8)!=gen||get(f+12,4)!=crc||get(f+16,4)!=n)return s;
    for(unsigned i=20;i<32;++i)if(f[i])return s;
    Bytes checked(b.begin(),b.begin()+32+n);std::fill(checked.begin()+24,checked.begin()+28,0);if(crc32(checked.data(),checked.size())!=crc)return s;
    if(get(&b[4],2)!=1||get(&b[6],2)>1){s.state=SlotState::unsupported;return s;}
    s.payload.assign(b.begin()+32,b.begin()+32+n);
    // A committed v1 image with an unknown field ID is protected, even if malformed.
    for(size_t p=0;p+8<=s.payload.size();){if(get(&s.payload[p],2)>28){s.state=SlotState::unsupported;return s;}size_t len=get(&s.payload[p+4],2);if(len>s.payload.size()-p-8)break;p+=8+len;}
    if(!decode(s.payload,s.config)||get(&b[6],2)<configMinor(s.config))return s;
    s.state=SlotState::valid;s.generation=gen;return s;
}
Selection scan(Storage& io){
    Selection r;Slot items[2];for(int i=0;i<2;++i){Bytes b(slotSize);if(!io.read(i*slotSize,b.data(),b.size())){r.blocked=true;return r;}items[i]=inspect(b);if(items[i].state==SlotState::unsupported)r.blocked=true;}
    if(items[0].state==SlotState::valid&&items[1].state==SlotState::valid&&items[0].generation==items[1].generation&&items[0].payload!=items[1].payload){r.blocked=true;return r;}
    for(int i=0;i<2;++i)if(items[i].state==SlotState::valid&&(r.index<0||items[i].generation>r.selected.generation)){r.index=i;r.selected=items[i];}
    return r;
}
bool save(Storage& io,const Config& c,Selection& persisted){
    if(!validate(c)||persisted.blocked)return false;
    Selection now=scan(io);if(now.blocked)return false;
    // Refuse to replace a previously loaded good image that is no longer readable.
    if(persisted.index>=0&&(now.index<0||now.selected.generation<persisted.selected.generation))return false;
    const Bytes payload=encode(c);if(now.index>=0&&payload==now.selected.payload){persisted=now;return true;}
    if(now.selected.generation==UINT64_MAX)return false;
    const int target=now.index==0?1:0;const uint16_t base=target*slotSize;Bytes image=slot(c,now.selected.generation+1),readback(slotSize),zero(32,0);
    if(!io.write(base+footerOffset,zero.data(),32)||!io.read(base+footerOffset,readback.data(),32)||memcmp(readback.data(),zero.data(),32))return false;
    // Write only header+used payload. Old padding is excluded by the contract.
    const size_t used=32+payload.size();for(size_t p=0;p<used;){size_t n=std::min(size_t(32-p%32),used-p);if(!io.write(base+p,image.data()+p,n))return false;p+=n;}
    if(!io.read(base,readback.data(),used)||memcmp(readback.data(),image.data(),used))return false;
    if(!io.write(base+footerOffset,image.data()+footerOffset,32)||!io.read(base,readback.data(),slotSize))return false;
    Slot verified=inspect(readback);if(verified.state!=SlotState::valid||verified.generation!=now.selected.generation+1||verified.payload!=payload)return false;
    persisted.index=target;persisted.selected=verified;persisted.blocked=false;return true;
}
bool equal(const Config& a,const Config& b){return encode(a)==encode(b);}
uint16_t adcBits(const Config& c){return (c.vbus_ct_code<<9)|(c.vshunt_ct_code<<6)|(c.temp_ct_code<<3)|c.average_code;}
uint32_t conversionUs(const Config& c){const unsigned ct[]={50,84,150,280,540,1052,2074,4120},avg[]={1,4,16,64,128,256,512,1024};return (ct[c.vbus_ct_code]+ct[c.vshunt_ct_code]+ct[c.temp_ct_code])*avg[c.average_code];}
bool timingFeasible(const Config& c){return validate(c)&&conversionUs(c)<c.ready_timeout_us&&conversionUs(c)<1000000/c.requested_rate_hz;}
uint32_t busHz(const Config& c){return c.requested_rate_hz>100?400000:100000;}
bool runtimeTimingFeasible(const Config& c){
    if(!timingFeasible(c))return false;
    // Reserve trigger/readback, scheduler and display service time. Actual cadence
    // remains observable; this check is not a claim of measured performance.
    const uint32_t overhead=busHz(c)==400000?2500:4000;
    return conversionUs(c)+overhead<=1000000/c.requested_rate_hz;
}
bool applyRegisters(Registers& io,const Config& c,bool& latchedFailure) {
    if (latchedFailure || !timingFeasible(c)) return false;
    uint32_t manufacturer,device,oldConfig,oldAdc;
    if (!io.read(0x3E,manufacturer) || !io.read(0x3F,device) ||
        manufacturer != 0x5449 || (device >> 4) != 0x228 ||
        !io.read(0,oldConfig) || !io.read(1,oldAdc)) return false;
    const uint16_t nextConfig=(oldConfig & ~0x3FD0u) | (c.adc_range << 4);
    const uint16_t nextAdc=adcBits(c);
    uint32_t checkConfig=0,checkAdc=0;
    if (io.write(1,nextAdc) && io.write(0,nextConfig) &&
        io.read(0,checkConfig) && io.read(1,checkAdc) &&
        checkConfig==nextConfig && checkAdc==nextAdc) return true;
    // Try both restorations, including when the first write/readback failed.
    const bool restoredConfig=io.write(0,oldConfig),restoredAdc=io.write(1,oldAdc);
    const bool configRead=io.read(0,checkConfig),adcRead=io.read(1,checkAdc);
    if (!restoredConfig || !restoredAdc || !configRead || !adcRead ||
        checkConfig!=oldConfig || checkAdc!=oldAdc) latchedFailure=true;
    return false;
}

}
