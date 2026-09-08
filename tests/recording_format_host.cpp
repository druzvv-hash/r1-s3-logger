#include "recording_format.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <limits>
#include <vector>
using namespace recording;
struct Sink:SyncSink {
    std::string bytes;size_t limit=SIZE_MAX;unsigned syncs=0,failSync=0;
    size_t write(const uint8_t* p,size_t n)override{n=std::min(n,limit-bytes.size());bytes.append(reinterpret_cast<const char*>(p),n);return n;}
    bool sync()override{return ++syncs!=failSync;}
};
SessionInfo info(){SessionInfo s;s.generation=3;s.revision=7;s.originUs=2000000;s.utcUs=1788854400123456ULL;s.id="host-roundtrip";s.commit="host-test";s.version="0.18";s.manufacturer=0x5449;s.device=0x2281;s.adc=0x7000|settings::adcBits(s.config);s.description="Synthetic \"roundtrip\"\nwith controls and UTF-8 Ω";return s;}
Sample sample(unsigned n){Sample s{};s.seq=100+n;s.t_us=2000000ULL+n*20000;s.vshunt_raw=n%16<8?1440:-1440;s.vbus_raw=15360;s.temp_raw=2944;s.raw_present=7;s.config_revision=7;return s;}
void writeFile(const std::string& path,const std::string& bytes){std::ofstream f(path,std::ios::binary);f<<bytes;assert(f.good());}
int main(int argc,char** argv){
    assert(argc==2);std::string dir=argv[1];
    assert(sessionId(1788864937000000ULL,0x4ee24d5b,0x9ebc8459)=="r1s3_2026-09-08_10-55-37Z_4ee24d5b_9ebc8459");
    assert(sessionId(951782400123456ULL,0,1)=="r1s3_2000-02-29_00-00-00Z_00000000_00000001");
    assert(sessionId(2147483648000000ULL,0,2)=="r1s3_2038-01-19_03-14-08Z_00000000_00000002");
    assert(sessionId(0,0,3)=="r1s3_time-unknown_00000000_00000003");
    Sha256 h;assert(h.hex()=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");h.add("abc",3);assert(h.hex()=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    Sha256 million;std::string a(1000,'a');for(unsigned i=0;i<1000;++i)million.add(a.data(),a.size());assert(million.hex()=="cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
    for(unsigned unknown=0;unknown<2;++unknown){
        uint8_t staging[8192];BlockBuffer block;assert(block.attach(staging,sizeof(staging)));Sink sink;LogWriter writer(block,sink);auto cfg=info();
        if(unknown){cfg.utcUs=0;cfg.config.allow_unknown_utc=true;cfg.config.calibration_note="control\nquote\" slash\\ Ω";}
        writer.beginSession(cfg);assert(writer.beginPart(0,""));
        for(unsigned n=0;n<600;++n){if(n==300)continue;auto s=sample(n);
            if(n==20){s.quality=1;s.raw_present=0;}if(n==25){s.vshunt_raw=524287;s.quality=5;}if(n==31){s.temp_raw=-32768;s.quality=5;}
            assert(writer.row(s));if(n==120)assert(writer.checkpointAndSync());}
        std::string digest;assert(writer.finish(false,digest));assert(writer.rows()==599);Sha256 full;full.add(sink.bytes.data(),sink.bytes.size());assert(digest==full.hex());
        writeFile(dir+(unknown?"/unknown.csv":"/known.csv"),sink.bytes);
    }
    {uint8_t bytes[8192];BlockBuffer b;b.attach(bytes,sizeof(bytes));Sink sink;LogWriter w(b,sink);w.beginSession(info());assert(w.beginPart(0,""));
        for(unsigned n=0;n<25;++n)assert(w.row(sample(n)));std::string digest;assert(w.finish(true,digest));writeFile(dir+"/part0.csv",sink.bytes);sink.bytes.clear();
        assert(w.beginPart(1,digest));for(unsigned n=25;n<55;++n)assert(w.row(sample(n)));assert(w.finish(false,digest));writeFile(dir+"/part1.csv",sink.bytes);}
    {uint8_t bytes[8192];BlockBuffer b;b.attach(bytes,sizeof(bytes));Sink sink;LogWriter w(b,sink);w.beginSession(info());assert(w.beginPart(0,""));std::string digest;assert(w.finish(false,digest));writeFile(dir+"/empty.csv",sink.bytes);}
    {uint8_t bytes[8192];BlockBuffer b;b.attach(bytes,sizeof(bytes));Sink sink;LogWriter w(b,sink);auto cfg=info();cfg.config.requested_rate_hz=10;cfg.config.max_gap_us=200000;w.beginSession(cfg);assert(w.beginPart(0,""));
        for(unsigned n=0;n<30;++n){auto s=sample(n);s.t_us=cfg.originUs+n*100000;assert(w.row(s));}std::string h;assert(w.finish(false,h));writeFile(dir+"/ten-hz.csv",sink.bytes);}
    // Failure before END may leave a verified prefix; no retry may turn it clean.
    for(size_t cut:{size_t(0),size_t(200),size_t(8191),size_t(8200),size_t(16000)}){
        uint8_t bytes[8192];BlockBuffer b;b.attach(bytes,sizeof(bytes));Sink sink;sink.limit=cut;LogWriter w(b,sink);w.beginSession(info());
        bool ok=w.beginPart(0,"");for(unsigned n=0;ok&&n<300;++n)ok=w.row(sample(n));
        std::string digest;assert(!ok&&!w.finish(false,digest));assert(w.failed());assert(sink.bytes.find("# END ")==std::string::npos);assert(sink.bytes.size()==cut);
    }
    {uint8_t bytes[8192];BlockBuffer b;b.attach(bytes,sizeof(bytes));Sink sink;sink.failSync=1;LogWriter w(b,sink);w.beginSession(info());assert(w.beginPart(0,""));assert(w.row(sample(0)));std::string h;assert(!w.finish(false,h));assert(sink.bytes.find("# END ")==std::string::npos);}
    {uint8_t bytes[8192];BlockBuffer b;b.attach(bytes,sizeof(bytes));Sink sink;LogWriter w(b,sink);w.beginSession(info());assert(w.beginPart(0,""));assert(w.row(sample(0)));auto bad=sample(1);bad.config_revision++;assert(!w.row(bad));std::string h;assert(!w.finish(false,h));}
    std::cout<<"FORMAT PASS\n";
}
