#include "recorder.h"
#include "recording_memory.h"
#include "pins.h"
#include <SD.h>
#include <SPI.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <atomic>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <cerrno>

namespace recorder {
namespace {
std::atomic<State> phase{State::Ready};
std::atomic<bool> overflow{false};
recording::SessionInfo session;
portMUX_TYPE statusLock=portMUX_INITIALIZER_UNLOCKED;
Status published, local;
int fd=-1;
bool mounted=false;
uint64_t budget=0, lastSync=0, lastPublish=0, sessionBytes=0;
uint32_t part=0;
char partial[160], complete[160];
std::string previousSha;
class Sink : public recording::SyncSink {
public:
    size_t write(const uint8_t* data,size_t size) override {
        if(fd<0||budget<size)return 0;
        const uint64_t began=esp_timer_get_time();const ssize_t n=::write(fd,data,size);
        local.maxWriteUs=std::max(local.maxWriteUs,uint32_t(esp_timer_get_time()-began));
        if(n>0){budget-=n;sessionBytes+=n;}return n>0?size_t(n):0;
    }
    bool sync() override {
        const uint64_t began=esp_timer_get_time();const bool ok=fd>=0&&fsync(fd)==0;
        local.maxSyncUs=std::max(local.maxSyncUs,uint32_t(esp_timer_get_time()-began));return ok;
    }
} sink;
recording::LogWriter writer(recording::outputBlock(),sink);
void publish(){
    local.rows=writer.sessionRows();local.bytes=sessionBytes;local.part=part;
    local.queued=recording::sampleQueue().queuedApprox();local.highWater=recording::sampleQueue().highWater();local.overflows=recording::sampleQueue().overflows();
    local.wh=writer.totals().whc-writer.totals().whd;local.ah=writer.totals().ahc-writer.totals().ahd;
    portENTER_CRITICAL(&statusLock);published=local;portEXIT_CRITICAL(&statusLock);lastPublish=esp_timer_get_time();
}
void fault(const char* why){
    // Producer observes Error before any slow close. No clean END or automatic retry.
    phase.store(State::Stopping);overflow.store(true);
    strlcpy(local.error,why,sizeof(local.error));
    if(fd>=0){::close(fd);fd=-1;}if(mounted){SD.end();mounted=false;}
    publish();phase.store(State::Error);
}
bool freeSpace(){
    const uint64_t total=SD.totalBytes(),used=SD.usedBytes(),reserve=session.config.reserve_bytes;
    if(!total||used>total||total-used<=reserve+recording::SD_BLOCK_BYTES*2)return false;
    budget=total-used-reserve;return true;
}
bool openPart(){
    snprintf(partial,sizeof(partial),"/sd/records/%s_%04lu.part",session.id.c_str(),(unsigned long)part);
    snprintf(complete,sizeof(complete),"/sd/records/%s_%04lu.csv",session.id.c_str(),(unsigned long)part);
    if(access(complete,F_OK)==0)return false;
    fd=::open(partial,O_WRONLY|O_CREAT|O_EXCL,0666);
    if(fd<0)return false;
    strlcpy(local.path,partial+3,sizeof(local.path));
    if(!writer.beginPart(part,previousSha)||!writer.checkpointAndSync())return false;
    lastSync=esp_timer_get_time();return true;
}
bool finishPart(bool rotation){
    std::string digest;
    if(!writer.finish(rotation,digest))return false;
    const bool closed=::close(fd)==0;fd=-1;if(!closed)return false;
    if(access(complete,F_OK)==0||::rename(partial,complete)!=0)return false;
    strlcpy(local.path,complete+3,sizeof(local.path));previousSha=digest;return true;
}
}
State state(){return phase.load(std::memory_order_acquire);}
bool busy(){const auto p=state();return p==State::Starting||p==State::Running||p==State::Stopping;}
const char* stateName(){switch(state()){case State::Starting:return "STARTING";case State::Running:return "RUNNING";case State::Stopping:return "STOPPING";case State::Error:return "ERROR";default:return "READY";}}
Status status(){Status s;portENTER_CRITICAL(&statusLock);s=published;portEXIT_CRITICAL(&statusLock);return s;}
bool start(const recording::SessionInfo& info,const char*& message){
    if(busy()){message="Recording is already starting, running or stopping";return false;}
    if(info.config.max_gap_us<=1000000/info.config.requested_rate_hz){message="Gap threshold must exceed one sample period; use twice the period or more";return false;}
    if(!info.generation||(!info.utcUs&&!info.config.allow_unknown_utc)){message="Set RTC time and save an initial valid settings generation before recording";return false;}
    if(!recording::resetMemory(info.config.queue_bytes)){message="Cannot allocate recording buffers in PSRAM/internal RAM";return false;}
    session=info;overflow.store(false);phase.store(State::Starting,std::memory_order_release);
    message="START accepted; wait for RUNNING";return true;
}
bool stop(const char*& message){
    if(state()==State::Stopping){message="Already finishing; wait for READY";return true;}
    if(state()!=State::Running){message="Recording is not running";return false;}
    phase.store(State::Stopping,std::memory_order_release);message="STOP accepted; draining and verifying file close";return true;
}
void push(const recording::Sample& s){
    if(state()!=State::Running||overflow.load())return;
    if(!recording::sampleQueue().tryPush(s))overflow.store(true);
}
void storageStep(bool transferActive){
    State p=state();
    if(p==State::Starting){
        local={};part=0;sessionBytes=0;previousSha.clear();writer.beginSession(session);
        if(transferActive){fault("SD transfer is active; close it before START");return;}
        pinMode(pins::SD_CS,OUTPUT);digitalWrite(pins::SD_CS,HIGH);SPI.begin(pins::SD_SCK,pins::SD_MISO,pins::SD_MOSI,pins::SD_CS);
        mounted=true;
        if(!SD.begin(pins::SD_CS,SPI,10000000,"/sd",5,false)||SD.cardType()==CARD_NONE){fault("SD mount failed");return;}
        if(!freeSpace()){fault("SD free space is below the configured reserve");return;}
        if(::mkdir("/sd/records",0777)!=0&&errno!=EEXIST){fault("Cannot create records directory");return;}
        if(!openPart()){fault("Cannot create/sync unique session file");return;}
        publish();phase.store(State::Running,std::memory_order_release);return;
    }
    if(p!=State::Running&&p!=State::Stopping)return;
    if(overflow.load()){fault("PSRAM FIFO overflow; incomplete .part retained");return;}
    recording::Sample sample;
    unsigned count=0;
    // Bounded storage work per pass; acquisition has higher priority on this core.
    while(count++<32&&recording::sampleQueue().peek(sample)){
        if(!writer.row(sample)){fault("SD write or sample-format failure; incomplete .part retained");return;}
        local.elapsedUs=sample.t_us-session.originUs;
        recording::sampleQueue().consume();
        // Leave room for checkpoint and END; each rotation has independent metadata.
        if(writer.bytes()+2048>=session.config.rotation_bytes){
            if(!finishPart(true)){fault("SD rotation finalization failed");return;}
            ++part;if(!freeSpace()||!openPart()){fault("SD rotation open/reserve failure");return;}
        }
    }
    if(overflow.load()){fault("PSRAM FIFO overflow; incomplete .part retained");return;}
    if(state()==State::Stopping&&!recording::sampleQueue().queuedApprox()){
        if(!finishPart(false)){fault("SD final sync/close/rename failed; inspect .part file");return;}
        SD.end();mounted=false;publish();phase.store(State::Ready,std::memory_order_release);return;
    }
    const uint64_t now=esp_timer_get_time();
    if(now-lastSync>=uint64_t(session.config.flush_interval_ms)*1000){
        if(!writer.checkpointAndSync()||!freeSpace()){fault("SD sync or free-space reserve failure");return;}lastSync=now;
    }
    if(now-lastPublish>=100000)publish();
}
}
