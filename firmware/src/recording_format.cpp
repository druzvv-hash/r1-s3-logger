#include "recording_format.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <ctime>

namespace recording {
namespace {
uint32_t rotr(uint32_t x,unsigned n){return (x>>n)|(x<<(32-n));}
constexpr uint32_t k[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
std::string integer(uint64_t v){char b[32];snprintf(b,sizeof(b),"%llu",(unsigned long long)v);return b;}
std::string signedInteger(int64_t v){char b[32];snprintf(b,sizeof(b),"%lld",(long long)v);return b;}
std::string real(double v){char b[40];snprintf(b,sizeof(b),"%.17g",v);return b;}
void crcAdd(uint32_t& crc,const std::string& s){for(uint8_t c:s){crc^=c;for(unsigned i=0;i<8;++i)crc=(crc>>1)^((crc&1)?0xedb88320:0);}}
std::string crcHex(uint32_t crc){char b[9];snprintf(b,sizeof(b),"%08lX",(unsigned long)crc);return b;}
void integral(double a,double b,double seconds,double& positive,double& negative){
    if(a*b<0){const double fraction=std::abs(a)/(std::abs(a)+std::abs(b));
        integral(a,0,seconds*fraction,positive,negative);integral(0,b,seconds*(1-fraction),positive,negative);return;}
    const double area=(a+b)*0.5*seconds/3600;
    if(area>=0)positive+=area;else negative-=area;
}
}
Sha256::Sha256(){const uint32_t initial[]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};memcpy(h_,initial,sizeof(h_));}
void Sha256::transform(const uint8_t* p){
    uint32_t w[64];for(unsigned i=0;i<16;++i)w[i]=(uint32_t(p[i*4])<<24)|(uint32_t(p[i*4+1])<<16)|(uint32_t(p[i*4+2])<<8)|p[i*4+3];
    for(unsigned i=16;i<64;++i){uint32_t a=w[i-15],b=w[i-2];w[i]=w[i-16]+(rotr(a,7)^rotr(a,18)^(a>>3))+w[i-7]+(rotr(b,17)^rotr(b,19)^(b>>10));}
    uint32_t a=h_[0],b=h_[1],c=h_[2],d=h_[3],e=h_[4],f=h_[5],g=h_[6],h=h_[7];
    for(unsigned i=0;i<64;++i){uint32_t t1=h+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^(~e&g))+k[i]+w[i];
        uint32_t t2=(rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
    h_[0]+=a;h_[1]+=b;h_[2]+=c;h_[3]+=d;h_[4]+=e;h_[5]+=f;h_[6]+=g;h_[7]+=h;
}
void Sha256::add(const void* bytes,size_t n){const auto* p=static_cast<const uint8_t*>(bytes);
    while(n){size_t offset=size_%64,take=std::min(n,64-offset);memcpy(tail_+offset,p,take);size_+=take;p+=take;n-=take;if(size_%64==0)transform(tail_);}}
std::string Sha256::hex() const {Sha256 copy=*this;uint64_t bits=size_*8;uint8_t pad[128]={0x80};size_t n=size_%64<56?56-size_%64:120-size_%64;
    for(unsigned i=0;i<8;++i)pad[n+i]=uint8_t(bits>>(56-8*i));copy.add(pad,n+8);char text[65];for(unsigned i=0;i<8;++i)snprintf(text+i*8,9,"%08lx",(unsigned long)copy.h_[i]);return text;}
std::string jsonQuote(const std::string& text){std::string s="\"";for(uint8_t c:text){if(c=='"'||c=='\\'){s+='\\';s+=char(c);}else if(c<32){char b[7];snprintf(b,sizeof(b),"\\u%04x",c);s+=b;}else s+=char(c);}return s+'"';}
std::string configJson(const settings::Config& c){std::string s="{";
#include "config_json_generated.inc"
return s+"}";}
std::string utcText(uint64_t epochUs){time_t seconds=epochUs/1000000;struct tm utc{};
#ifdef _WIN32
    gmtime_s(&utc,&seconds);
#else
    gmtime_r(&seconds,&utc);
#endif
    char b[40];snprintf(b,sizeof(b),"%04d-%02d-%02dT%02d:%02d:%02d.%06luZ",utc.tm_year+1900,utc.tm_mon+1,utc.tm_mday,utc.tm_hour,utc.tm_min,utc.tm_sec,(unsigned long)(epochUs%1000000));return b;
}
std::string sessionId(uint64_t utcUs,uint32_t randomHi,uint32_t randomLo){
    std::string stamp="time-unknown";
    if(utcUs){stamp=utcText(utcUs).substr(0,19);stamp[10]='_';stamp[13]=stamp[16]='-';stamp+='Z';}
    char suffix[20];snprintf(suffix,sizeof(suffix),"_%08lx_%08lx",(unsigned long)randomHi,(unsigned long)randomLo);
    return "r1s3_"+stamp+suffix;
}
void LogWriter::beginSession(const SessionInfo& info){info_=info;previous_=false;incomplete_=false;totals_={};sessionRows_=0;failed_=false;}
bool LogWriter::append(const std::string& bytes){
    if(failed_)return false;
    size_t pos=0;while(pos<bytes.size()){
        size_t n=std::min(block_.freeBytes(),bytes.size()-pos);
        if(!block_.append(reinterpret_cast<const uint8_t*>(bytes.data()+pos),n)){failed_=true;return false;}
        hash_.add(bytes.data()+pos,n);offset_+=n;pos+=n;
        if(!block_.freeBytes()&&!block_.drain(sink_)){failed_=true;return false;}
    }return true;
}
bool LogWriter::beginPart(uint32_t part,const std::string& previousSha){
    if(failed_||block_.pending()||block_.fault()!=WriteFault::None)return false;
    offset_=rows_=blockStart_=firstSeq_=lastSeq_=0;blockRows_=0;crc_=0xffffffff;hash_=Sha256();
    auto payload=settings::encode(info_.config);Sha256 configHash;configHash.add(payload.data(),payload.size());
    std::string meta="# META {\"acquisition\":{\"adc_config\":"+integer(info_.adc)+",\"measured_hz\":"+(info_.measuredHz>0?real(info_.measuredHz):"null")+",\"requested_hz\":"+integer(info_.config.requested_rate_hz)+",\"timestamp_note\":\"Sequential VSHUNT/VBUS/TEMP; conversion-ready observed before register readback\"},\"config\":"+configJson(info_.config)+",\"config_generation\":"+integer(info_.generation)+",\"config_sha256\":"+jsonQuote(configHash.hex())+",\"description\":"+jsonQuote(info_.description);
    meta+=",\"hardware\":{\"board\":\"ESP32-S3-N32R16V\",\"device_id\":"+integer(info_.device)+",\"manufacturer_id\":"+integer(info_.manufacturer)+",\"sensor\":\"INA228\",\"sensor_address\":64,\"shunt_nameplate\":\"60mV/400A\",\"topology\":\"low-side\"},\"integration\":\"trapezoid-sign-split-no-gap-v1\",\"part\":"+integer(part)+",\"previous_part_sha256\":"+(part?jsonQuote(previousSha):"null");
    meta+=",\"raw\":{\"temp\":\"signed16\",\"temp_C_lsb\":0.0078125,\"vbus\":\"unsigned20\",\"vbus_V_lsb\":0.0001953125,\"vshunt\":\"signed20\",\"vshunt_uV_lsb\":"+std::string(info_.config.adc_range?"0.078125":"0.3125")+"},\"schema\":1,\"session_id\":"+jsonQuote(info_.id);
    meta+=",\"time\":{\"anchor_t_us\":0,\"sample_point\":\"conversion-ready-observed\",\"source\":"+std::string(info_.utcUs?"\"DS3231\"":"\"unknown\"")+",\"uncertainty_us\":"+(info_.utcUs?"1100000":"null")+",\"utc_anchor\":"+(info_.utcUs?jsonQuote(utcText(info_.utcUs)):"null")+"}";
    meta+=",\"units\":{\"Ah_net\":\"Ah\",\"Ahc\":\"Ah\",\"Ahd\":\"Ah\",\"I_A\":\"A\",\"P_W\":\"W\",\"U_V\":\"V\",\"Wh_net\":\"Wh\",\"Whc\":\"Wh\",\"Whd\":\"Wh\",\"ms_from_start\":\"ms\",\"t_us\":\"us\"},\"writer\":{\"commit\":"+jsonQuote(info_.commit)+",\"dirty\":"+(info_.dirty?"true":"false")+",\"name\":\"R1-S3\",\"version\":"+jsonQuote(info_.version)+"}}\n";
    uint32_t crc=0xffffffff;crcAdd(crc,meta);
    return append("# R1S3_LOG schema=1\n")&&append(meta)&&append("# META_CRC32 "+crcHex(~crc)+"\n")&&append("timestamp,ms_from_start,I_A,U_V,P_W,Wh_net,Whc,Whd,seq,t_us,vshunt_raw,vbus_raw,temp_raw,quality,Ah_net,Ahc,Ahd\n");
}
bool LogWriter::row(const Sample& input){
    if(failed_||input.t_us<info_.originUs||input.config_revision!=info_.revision)return failed_=true,false;
    Sample s=input;s.t_us-=info_.originUs;
    if(previous_&&(s.seq<=prior_.seq||s.t_us<=prior_.t_us))return failed_=true,false;
    if(s.quality&~31)return failed_=true,false;
    if(s.raw_present!=7)s.quality|=1;
    if(((s.raw_present&1)&&(s.vshunt_raw==-524288||s.vshunt_raw==524287))||((s.raw_present&2)&&s.vbus_raw==1048575)||((s.raw_present&4)&&(s.temp_raw==-32768||s.temp_raw==32767)))s.quality|=5;
    if(previous_&&(s.seq!=prior_.seq+1||s.t_us-prior_.t_us>info_.config.max_gap_us))s.quality|=2;
    if(!previous_)s.quality&=~2; // A session has no measured interval before its first row.
    if(s.quality&3)incomplete_=true;if(incomplete_)s.quality|=16;
    if(!info_.utcUs)s.quality|=8;
    const auto& c=info_.config;double amps=c.polarity*(s.vshunt_raw*(c.adc_range?0.078125:0.3125)-c.i_zero_uV)/c.shunt_uohm*c.i_gain;
    double volts=(s.vbus_raw*0.0001953125-c.u_zero_V)*c.u_gain,watts=amps*volts;
    if(!(s.quality&1)&&(!std::isfinite(amps)||!std::isfinite(volts)||!std::isfinite(watts)))return failed_=true,false;
    if(previous_&&!((s.quality|prior_.quality)&1)&&!(s.quality&2)){
        double dt=(s.t_us-prior_.t_us)/1000000.0;integral(priorI_,amps,dt,totals_.ahc,totals_.ahd);integral(priorP_,watts,dt,totals_.whc,totals_.whd);}
    std::string line=info_.utcUs?utcText(info_.utcUs+s.t_us):"";
    line+=","+integer(s.t_us/1000)+","+((s.quality&1)?std::string(",,"):real(amps)+","+real(volts)+","+real(watts));
    line+=","+real(totals_.whc-totals_.whd)+","+real(totals_.whc)+","+real(totals_.whd)+","+integer(s.seq)+","+integer(s.t_us);
    line+=","+((s.raw_present&1)?signedInteger(s.vshunt_raw):"")+","+((s.raw_present&2)?integer(s.vbus_raw):"")+","+((s.raw_present&4)?signedInteger(s.temp_raw):"")+","+integer(s.quality);
    line+=","+real(totals_.ahc-totals_.ahd)+","+real(totals_.ahc)+","+real(totals_.ahd)+"\n";
    if(!blockRows_){blockStart_=offset_;firstSeq_=s.seq;}lastSeq_=s.seq;
    crcAdd(crc_,line);if(!append(line))return false;++blockRows_;++rows_;++sessionRows_;prior_=s;priorI_=amps;priorP_=watts;previous_=true;
    return blockRows_<256||checkpoint();
}
bool LogWriter::checkpoint(){
    if(!blockRows_)return !failed_;
    std::string line="# CHECKPOINT {\"crc32\":"+jsonQuote(crcHex(~crc_))+",\"end\":"+integer(offset_)+",\"first_seq\":"+integer(firstSeq_)+",\"last_seq\":"+integer(lastSeq_)+",\"rows\":"+integer(blockRows_)+",\"start\":"+integer(blockStart_)+"}\n";
    if(!append(line))return false;crc_=0xffffffff;blockRows_=0;return true;
}
bool LogWriter::checkpointAndSync(){if(!checkpoint()||!block_.drain(sink_,true)||!sink_.sync()){failed_=true;return false;}return true;}
bool LogWriter::finish(bool rotation,std::string& wholeFileSha){
    if(!checkpointAndSync())return false;
    const std::string end="# END {\"clean\":true,\"reason\":"+jsonQuote(rotation?"rotation":"stop")+",\"rows\":"+integer(rows_)+",\"sha256\":"+jsonQuote(hash_.hex())+"}\n";
    if(!append(end)||!block_.drain(sink_,true)||!sink_.sync()){failed_=true;return false;}wholeFileSha=hash_.hex();return true;
}
}
