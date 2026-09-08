#include "live_history.h"
#include <esp_heap_caps.h>
#include <atomic>
#include <new>
namespace {
constexpr unsigned CAPACITY=2048, BATCH=48;
LivePoint* points=nullptr;
portMUX_TYPE guard=portMUX_INITIALIZER_UNLOCKED;
uint64_t written=0;
std::atomic<uint32_t> dropped{0};
}
bool liveHistoryBegin(){
    points=static_cast<LivePoint*>(heap_caps_malloc(sizeof(LivePoint)*CAPACITY,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!points)return false;
    for(unsigned i=0;i<CAPACITY;++i)new(points+i)LivePoint{};
    return true;
}
void liveHistoryPush(const LivePoint& p){
    if(!points){++dropped;return;}
    portENTER_CRITICAL(&guard);
    points[written%CAPACITY]=p;++written;
    portEXIT_CRITICAL(&guard);
}
uint32_t liveHistoryDrops(){return dropped.load();}
String liveHistoryJson(uint64_t after){
    LivePoint copy[BATCH];unsigned count=0;uint64_t oldest=0,newest=0;bool lost=false;
    if(points){
        // Bounded binary lookup + at most 48 copies. No allocation, formatting,
        // serial output or RTOS wait while locked; neither core suspends holding it.
        portENTER_CRITICAL(&guard);
        const unsigned used=written<CAPACITY?written:CAPACITY;
        const uint64_t start=written-used;
        if(used){oldest=points[start%CAPACITY].id;newest=points[(written-1)%CAPACITY].id;}
        lost=after&&oldest&&after+1<oldest;
        // A fresh/reconnected viewer starts with recent data, not a minutes-long replay.
        unsigned first=0,last=used;
        if(after){
            while(first<last){
                const unsigned mid=first+(last-first)/2;
                if(points[(start+mid)%CAPACITY].id<=after)first=mid+1;else last=mid;
            }
        }else first=used>BATCH?used-BATCH:0;
        for(unsigned i=first;i<used&&count<BATCH;++i)copy[count++]=points[(start+i)%CAPACITY];
        portEXIT_CRITICAL(&guard);
    }
    String out;out.reserve(4000);
    out="{\"preview_drops\":"+String(dropped.load())+",\"lost\":"+(lost?"true":"false")+",\"samples\":[";
    for(unsigned i=0;i<count;++i){
        const auto& p=copy[i];char row[160];
        snprintf(row,sizeof(row),"%s[%llu,%llu,%.6f,%.6f,%u,%lu]",i?",":"",p.id,p.tUs,p.volts,p.amps,p.quality,static_cast<unsigned long>(p.revision));
        out+=row;
    }
    char tail[100];snprintf(tail,sizeof(tail),"],\"oldest\":%llu,\"newest\":%llu,\"cursor\":%llu}",oldest,newest,count?copy[count-1].id:after);
    return out+tail;
}
