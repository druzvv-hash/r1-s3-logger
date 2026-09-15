// Runs exclusively inside the existing BLE worker; R3 and CANBox are explicit
// modes of its single connection. This avoids competing NimBLE owners.
constexpr char canServiceUuid[]="7e57c100-7a1e-4e54-a930-64e137711031";
constexpr char canCommandUuid[]="7e57c101-7a1e-4e54-a930-64e137711031";
constexpr char canStateUuid[]="7e57c102-7a1e-4e54-a930-64e137711031";
constexpr char canDescriptorUuid[]="7e57c103-7a1e-4e54-a930-64e137711031";
bool canMode=false,canSaved=false,canHello=false;
uint8_t canSavedPeer[6]={};
ecosystem::Frame canObserved;
uint64_t canSeen=0,canPoll=0,canPending=0,canDeadline=0;
std::atomic<uint32_t> canReadErrors(0),canConnections(0),canTimeReplies(0),canInvalidTime(0);
NimBLERemoteCharacteristic *canRx=nullptr,*canTx=nullptr;
struct CanView {bool mode,saved,connected,fresh,pending,ready,authorized,clockSynced;uint64_t boot,session,seen;uint8_t phase;uint32_t detail;char peer[18];};
CanView canView={};
void canPublish() {
    CanView v={};v.mode=canMode;v.saved=canSaved;
    v.connected=canMode&&subscribed&&linkUp.load()&&authenticated.load();
    v.fresh=v.connected&&canSeen&&monoUs()-canSeen<3000000;
    v.seen=canSeen;v.pending=canPending!=0;v.boot=canObserved.sender_boot;v.session=canObserved.session;
    v.ready=(canObserved.flags&ecosystem::Ready)!=0;v.authorized=canHello;v.clockSynced=(canObserved.flags&ecosystem::RtcSynced)!=0;
    v.phase=uint8_t(canObserved.phase);v.detail=canObserved.detail;
    snprintf(v.peer,sizeof(v.peer),"%s",canMode?desiredPeer:"");
    portENTER_CRITICAL(&statusLock);canView=v;status.canboxMode=canMode;portEXIT_CRITICAL(&statusLock);
}
String canJson() {
    CanView v;portENTER_CRITICAL(&statusLock);v=canView;portEXIT_CRITICAL(&statusLock);
    v.connected=v.connected&&linkUp.load()&&authenticated.load();
    v.fresh=v.connected&&v.seen&&monoUs()-v.seen<3000000;
    char text[520];snprintf(text,sizeof(text),
        "{\"mode\":%s,\"saved\":%s,\"connected\":%s,\"fresh\":%s,\"pending\":%s,\"ready\":%s,\"authorized\":%s,\"clock_synced\":%s,\"boot\":\"%llu\",\"session\":\"%llu\",\"phase\":\"%s\",\"detail\":%lu,\"peer\":\"%s\"}",
        v.mode?"true":"false",v.saved?"true":"false",v.connected?"true":"false",v.fresh?"true":"false",v.pending?"true":"false",v.ready?"true":"false",v.authorized?"true":"false",v.clockSynced?"true":"false",
        (unsigned long long)v.boot,(unsigned long long)v.session,ecosystem::phaseName(ecosystem::Phase(v.phase)),(unsigned long)v.detail,v.peer);
    const auto source=snapshot();const uint64_t now=monoUs();
    const uint64_t age=now>=source.snapshotUs?(now-source.snapshotUs)/1000:UINT64_MAX;
    String out(text);out.remove(out.length()-1);
    out+=",\"connections\":"+String(canConnections.load())+",\"read_errors\":"+String(canReadErrors.load());
    out+=",\"time_replies\":"+String(canTimeReplies.load())+",\"invalid_time_replies\":"+String(canInvalidTime.load());
    out+=",\"rtc_read_age_ms\":"+(source.rtcValid&&age<=UINT32_MAX&&source.rtcReadAgeMs<=UINT32_MAX-age?String(uint32_t(age+source.rtcReadAgeMs)):String("null"));
    return out+"}";
}
void canLoad() {
    Preferences prefs;if(!prefs.begin("r1-canbox",true))return;
    uint8_t record[7];size_t n=prefs.getBytesLength("peer-v1");
    canSaved=n==7&&prefs.getBytes("peer-v1",record,7)==7&&record[0]==1;
    if(canSaved)memcpy(canSavedPeer,record+1,6);prefs.end();canPublish();
}
bool canRead() {
    if(!canTx||!linkUp.load()||!authenticated.load())return false;
    deadlineMs.store(millis()+5000);auto value=canTx->readValue();deadlineMs.store(0);
    ecosystem::Frame f;
    if(!ecosystem::decode(value.data(),value.size(),f)||!ecosystem::sameDevice(f.sender,desiredId)||!f.sender_boot||
        (canHello&&f.target_boot&&f.target_boot!=ownBoot)||
        (canHello&&f.target_boot&&!ecosystem::sameDevice(f.target,ownId)))return false;
    if(canObserved.sender_boot&&canObserved.sender_boot!=f.sender_boot) {canPending=0;canHello=false;}
    if(f.stamp_us!=canObserved.stamp_us)canSeen=monoUs();
    canObserved=f;
    if(canPending&&f.kind==ecosystem::Kind::Result&&f.request==canPending) {
        canPending=0;setState("CANBOX",f.phase==ecosystem::Phase::Rejected?"CANBox rejected command; inspect detail":"");
    }
    return true;
}
bool canSend(ecosystem::Frame f) {
    if(!canRx||!linkUp.load()||!authenticated.load())return false;
    memcpy(f.sender,ownId,6);memcpy(f.target,desiredId,6);f.sender_boot=ownBoot;f.target_boot=canObserved.sender_boot;
    uint8_t bytes[96];ecosystem::encode(f,bytes);deadlineMs.store(millis()+5000);
    bool ok=canRx->writeValue(bytes,96,true);deadlineMs.store(0);return ok;
}
void canReplyTime() {
    const auto s=snapshot();const uint64_t now=monoUs();
    ecosystem::Frame f;f.kind=ecosystem::Kind::TimeReply;f.request=canObserved.request;f.stamp_us=canObserved.stamp_us;f.revision=s.rtcRevision;
    const uint64_t age=now>=s.snapshotUs?(now-s.snapshotUs)/1000:UINT64_MAX;
    if(s.rtcValid&&s.utcUs&&age<=1500&&s.rtcReadAgeMs<=12000&&age+s.rtcReadAgeMs<=12000) {
        f.value_us=s.utcUs+(now-s.snapshotUs);f.detail=uint32_t(age+s.rtcReadAgeMs);f.flags=ecosystem::RtcValid;
    } else {f.detail=UINT32_MAX;++canInvalidTime;}
    if(canSend(f))++canTimeReplies;
}
void canDiscover() {
    deadlineMs.store(millis()+10000);auto service=client->getService(canServiceUuid);
    if(!service){retry("CANBox service unavailable");return;}
    auto d=service->getCharacteristic(canDescriptorUuid);
    canRx=service->getCharacteristic(canCommandUuid);canTx=service->getCharacteristic(canStateUuid);
    if(!d||!d->canRead()||!canRx||!canRx->canWrite()||!canTx||!canTx->canRead()||client->getMTU()<99) {
        retry("CANBox protocol or MTU unsupported");return;
    }
    auto value=d->readValue();const uint8_t expected[16]={'C','B','X','1',1,3,2,2,3,0,0,0,0,0,0,0};
    if(value.size()!=16||memcmp(value.data(),expected,16)){retry("CANBox capabilities unsupported");return;}
    canHello=false;canObserved=ecosystem::Frame();
    if(!canRead()){retry("CANBox identity/status invalid");return;}
    deadlineMs.store(0);subscribed=true;pairing=false;retryDelay=1000;canHello=false;++canConnections;
    setState("CANBOX",canSaved?"":"Use CANBox BLE ENROLL, then save association on R1");
}
void canStep() {
    if(desired) {
        if((subscribed||pairing)&&!linkUp.load()) {canPending=0;canSeen=0;retry("CANBox disconnected; recording outcome unknown");}
        if(pairing&&linkUp.load()) {
            if(authenticated.load())canDiscover();
            else if(millis()-pairingAt>=15000)retry("CANBox pairing timed out");
        }
        if(!subscribed&&!pairing&&int32_t(millis()-retryAt)>=0) {
            setState("CONNECTING");
            if(!client->connect(NimBLEAddress(std::string(desiredPeer),BLE_ADDR_PUBLIC),true))retry("CANBox connection failed");
            else {pairing=true;pairingAt=millis();if(NimBLEDevice::startSecurity(client->getConnId()))retry("CANBox security failed");}
        }
        if(subscribed&&monoUs()-canPoll>=500000) {
            canPoll=monoUs();
            if(!canRead()) {++canReadErrors;setState("CANBOX","CANBox status read failed; checking link");}
            else if(!canHello) {ecosystem::Frame hello;hello.kind=ecosystem::Kind::Hello;canHello=canSend(hello);}
            else if(canObserved.kind==ecosystem::Kind::TimeRequest)canReplyTime();
        }
        if(canPending&&monoUs()>canDeadline) {canPending=0;setState("CANBOX","Command result unknown; inspect actual state before retry");}
    }
    canPublish();
}
void canHandle(const Command& c) {
    if(c.kind==Command::CanForget) {
        if(canMode){desired=false;dropLink();canMode=false;canSeen=canPending=0;}
        Preferences prefs;bool ok=prefs.begin("r1-canbox",false);
        if(ok){ok=!prefs.isKey("peer-v1")||prefs.remove("peer-v1");prefs.end();}
        if(ok&&canSaved&&initRadio()) {
            char address[18];r3_ble::formatDevice(canSavedPeer,address);
            NimBLEDevice::deleteBond(NimBLEAddress(std::string(address),BLE_ADDR_PUBLIC));
        }
        if(ok)canSaved=false;
        setState(ok?"OFF":"ERROR",ok?"":"CANBox policy erase failed");canPublish();return;
    }

    if(c.kind==Command::CanStart||c.kind==Command::CanStop||c.kind==Command::CanQuery) {
        if(!canMode||!canHello||!canSaved||!ecosystem::sameDevice(desiredId,canSavedPeer)||canPending||!subscribed||!canRead()||monoUs()-canSeen>=3000000) {
            setState("CANBOX","Command needs fresh enrolled CANBox; no pending action");return;
        }
        ecosystem::Frame f;f.kind=ecosystem::Kind::Command;
        f.op=c.kind==Command::CanStart?ecosystem::Op::Start:c.kind==Command::CanStop?ecosystem::Op::Stop:ecosystem::Op::Query;
        if(f.op==ecosystem::Op::Start&&!(canObserved.flags&ecosystem::RtcSynced)){setState("CANBOX","Time sync required; check R1 RTC");return;}
        if(f.op==ecosystem::Op::Start&&(!(canObserved.flags&ecosystem::Ready)||!ecosystem::startable(canObserved.phase))) {setState("CANBOX","CANBox is not idle/closed");return;}
        f.request=(uint64_t(esp_random())<<32)|esp_random();if(!f.request)f.request=1;
        f.session=f.op==ecosystem::Op::Start?((uint64_t(esp_random())<<32)|esp_random()):canObserved.session;
        if(f.op==ecosystem::Op::Start&&!uint32_t(f.session))f.session|=1;
        f.stamp_us=canObserved.stamp_us;f.ttl_ms=ecosystem::kCommandTtlMs;
        if(canSend(f)) {canPending=f.request;canDeadline=monoUs()+12000000;setState("CANBOX","Command sent; waiting for actual CANBox result");}
        else setState("CANBOX","Command delivery unknown; inspect CANBox state");
        canPublish();return;
    }
    if(c.kind==Command::CanSave) {
        if(!canMode||!canHello||!subscribed||!authenticated.load()||!NimBLEDevice::isBonded(NimBLEAddress(std::string(desiredPeer),BLE_ADDR_PUBLIC))) {
            setState("CANBOX","Save needs authenticated CANBox and its ENROLL permission");return;
        }
        Preferences prefs;uint8_t record[7]={1};memcpy(record+1,desiredId,6);
        bool ok=prefs.begin("r1-canbox",false)&&prefs.putBytes("peer-v1",record,7)==7;prefs.end();
        if(ok) {memcpy(canSavedPeer,desiredId,6);canSaved=true;allowPairing.store(false);pin.store(0);}
        setState("CANBOX",ok?"":"CANBox policy save failed");canPublish();return;
    }
    desired=false;if(scanner&&scanner->isScanning())scanner->stop();dropLink();
    canMode=true;canSeen=canPending=0;canHello=false;canRx=canTx=nullptr;
    if(!initRadio()){canPublish();return;}
    if(c.kind==Command::CanOn) {
        if(!canSaved){setState("OFF","No saved CANBox");canPublish();return;}
        memcpy(desiredId,canSavedPeer,6);r3_ble::formatDevice(desiredId,desiredPeer);
        pin.store(0);allowPairing.store(false);
        if(!NimBLEDevice::isBonded(NimBLEAddress(std::string(desiredPeer),BLE_ADDR_PUBLIC))) {setState("ERROR","CANBox bond missing; enroll again");canPublish();return;}
    } else {
        snprintf(desiredPeer,sizeof(desiredPeer),"%s",c.peer);r3_ble::parseDevice(desiredPeer,desiredId);
        pin.store(c.pin);allowPairing.store(true);
    }
    desiredType=BLE_ADDR_PUBLIC;trusted.store(false);remoteAllowed.store(false);
    desired=true;retryAt=millis();retryDelay=1000;setState("CONNECTING");canPublish();
}
bool canQueue(const char* a,const char*& message) {
    Command c={};
    if(!strcmp(a,"FORGET"))c.kind=Command::CanForget;
    else if(!strcmp(a,"ON"))c.kind=Command::CanOn;
    else if(!strcmp(a,"SAVE"))c.kind=Command::CanSave;
    else if(!strcmp(a,"START"))c.kind=Command::CanStart;
    else if(!strcmp(a,"STOP"))c.kind=Command::CanStop;
    else if(!strcmp(a,"QUERY"))c.kind=Command::CanQuery;
    else if(!strncmp(a,"CONNECT ",8)&&strlen(a)==32&&a[25]==' ') {
        c.kind=Command::CanConnect;memcpy(c.peer,a+8,17);uint8_t id[6];
        if(!r3_ble::parseDevice(c.peer,id)){message="Invalid CANBox address";return false;}
        r3_ble::formatDevice(id,c.peer);
        for(unsigned i=26;i<32;i++){if(a[i]<'0'||a[i]>'9'){message="PIN needs six digits";return false;}c.pin=c.pin*10+a[i]-'0';}
    }else{message="Use BLE CAN CONNECT address PIN, SAVE, ON, START, STOP, QUERY";return false;}
    if(xQueueSend(commands,&c,0)!=pdTRUE){message="BLE queue busy";return false;}
    message="CANBox action queued; check its actual result";return true;
}
