#include "r3_ble_client.h"
#include "r3_ble_protocol.h"
#include "r3_ble_receiver.h"
#include "r3_ble_trust.h"
#include "ecosystem_protocol.h"
#include "ecosystem_command_cache.h"
#include <NimBLEDevice.h>
#include <nimble/nimble/host/include/host/ble_store.h>
#include <Preferences.h>
#include <esp_timer.h>
#include <esp_heap_caps.h>
#include <atomic>

#if MYNEWT_VAL(BLE_SM_LEGACY) || !MYNEWT_VAL(BLE_STORE_CONFIG_PERSIST)
#error "Ecosystem requires Secure Connections only and persistent bond storage"
#endif

namespace {
constexpr unsigned kDevices = 6;
struct Device { char address[18]; char name[32]; uint8_t type; };
struct Status {
    bool enabled, authenticated, utcValid, connected, enrolled, remote, ecosystem, rtcSynced;
    char state[16], peer[18], error[56];
    uint64_t boot, segment, received, missing, malformed, duplicates, outOfOrder;
    uint64_t receiveUs, captureUs;
    uint64_t correctionBoot;
    uint32_t clockRevision, sequence, unixS, connections, reconnects, stackFree;
    uint32_t correctionRevision;
    uint16_t mtu;
    unsigned deviceCount;
    Device devices[kDevices];
};
struct Command { enum Kind { Scan, Connect, Off, On, Save, Forget } kind; char peer[18]; uint32_t pin; bool remote; };
struct Packet { uint8_t bytes[r3_ble::kBeaconBytes]; size_t length; uint64_t receiveUs; uint32_t epoch; };
struct EcoPacket { uint8_t bytes[96]; size_t length; uint64_t receiveUs; uint32_t epoch; };
struct Completion { R3BleOwnerRequest request; bool accepted; char message[80]; };
Status status = {};
portMUX_TYPE statusLock = portMUX_INITIALIZER_UNLOCKED;
QueueHandle_t commands = nullptr, packets = nullptr, ecoPackets = nullptr, ownerActions = nullptr, completions = nullptr;
TaskHandle_t workerHandle = nullptr;
std::atomic<bool> linkUp(false), authenticated(false);
std::atomic<bool> allowPairing(false), trusted(false), remoteAllowed(false);
std::atomic<uint32_t> startGeneration(1);
std::atomic<uint32_t> pin(0), callbackEpoch(0), drops(0), deadlineMs(0);
std::atomic<int> activeHandle(-1);
esp_timer_handle_t guardTimer = nullptr;
NimBLEClient* client = nullptr;
NimBLEScan* scanner = nullptr;
bool initialized = false, desired = false, subscribed = false, pairing = false;
bool ecoSubscribed = false, helloSent = false, policyPresent = false, policyInvalid = false;
r3_trust::Policy policy;
R3BleOwnerSnapshot ownerSnapshot;
uint64_t localStopUs = 0;
NimBLERemoteCharacteristic* ecoUpstream = nullptr;
uint8_t ownId[6] = {};
uint64_t ownBoot = 0, timeRequestId = 0, timeRequestStamp = 0, lastStatusUs = 0;
uint64_t connectionBeganUs = 0;
uint64_t syncedSourceBoot = 0, nextTimeRequestUs = 0;
uint64_t pendingTimeDeadlineUs = 0;
uint32_t syncedRevision = 0;
bool timeActionPending = false;
ecosystem::CommandCache receipts;
char desiredPeer[18] = {};
uint8_t desiredId[6] = {}, desiredType = BLE_ADDR_PUBLIC;
uint32_t retryAt = 0, retryDelay = 1000, pairingAt = 0, epoch = 0;
r3_ble::Receiver receiver;

uint64_t monoUs() { return uint64_t(esp_timer_get_time()); }
bool selectedPolicy() { return policyPresent && r3_ble::sameDevice(policy.peer, desiredId); }
void publishPolicy() {
    const bool active = selectedPolicy();
    trusted.store(active); remoteAllowed.store(active && policy.remote);
    portENTER_CRITICAL(&statusLock);
    status.enrolled = policyPresent; status.remote = active && policy.remote;
    status.ecosystem = ecoSubscribed; status.rtcSynced = syncedSourceBoot != 0;
    status.correctionBoot = syncedSourceBoot; status.correctionRevision = syncedRevision;
    portEXIT_CRITICAL(&statusLock);
}

bool loadPolicy() {
    Preferences prefs;
    policyPresent = policyInvalid = false;
    if (!prefs.begin("r1-ecosystem", true)) return false;
    const size_t length = prefs.getBytesLength("peer-v1");
    uint8_t bytes[r3_trust::kBytes] = {};
    if (length) {
        policyInvalid = length != sizeof(bytes) || prefs.getBytes("peer-v1", bytes, sizeof(bytes)) != sizeof(bytes) ||
                        !r3_trust::decode(bytes, sizeof(bytes), policy);
        policyPresent = !policyInvalid;
    }
    prefs.end(); return policyPresent;
}

bool storePolicy(const r3_trust::Policy& value) {
    Preferences prefs;
    if (!prefs.begin("r1-ecosystem", false)) return false;
    uint8_t bytes[r3_trust::kBytes], readback[r3_trust::kBytes] = {};
    r3_trust::encode(value, bytes);
    const bool okay = prefs.putBytes("peer-v1", bytes, sizeof(bytes)) == sizeof(bytes) &&
        prefs.getBytes("peer-v1", readback, sizeof(readback)) == sizeof(readback) &&
        memcmp(bytes, readback, sizeof(bytes)) == 0;
    prefs.end();
    if (okay) { policy = value; policyPresent = true; policyInvalid = false; }
    return okay;
}

void setState(const char* state, const char* error = "") {
    portENTER_CRITICAL(&statusLock);
    snprintf(status.state, sizeof(status.state), "%s", state);
    snprintf(status.error, sizeof(status.error), "%s", error);
    status.enabled = initialized && (desired || strcmp(state, "OFF") != 0);
    status.connected = subscribed && linkUp.load();
    status.authenticated = authenticated.load() && status.connected;
    portEXIT_CRITICAL(&statusLock);
}

// A timed-out GATT operation releases its waiting worker via disconnection.
// The timer only calls the host GAP API, never a client object or hardware I/O.
void operationGuard(void*) {
    const uint32_t deadline = deadlineMs.load();
    const int handle = activeHandle.load();
    if (deadline && handle >= 0 && int32_t(millis() - deadline) >= 0) {
        deadlineMs.store(0);
        ble_gap_terminate(uint16_t(handle), BLE_ERR_REM_USER_CONN_TERM);
    }
}

class ClientCallbacks final : public NimBLEClientCallbacks {
    void onConnect(NimBLEClient* c) override {
        activeHandle.store(c->getConnId()); linkUp.store(true);
    }
    void onDisconnect(NimBLEClient*) override {
        linkUp.store(false); authenticated.store(false); activeHandle.store(-1);
        callbackEpoch.store(0);
    }
    uint32_t onPassKeyRequest() override {
        // A forgotten/replaced R3 bond must not cause unattended pairing with a
        // default PIN. Re-enrollment always requires explicit CONNECT.
        if (!allowPairing.load()) {
            const int handle = activeHandle.load();
            if (handle >= 0) ble_gap_terminate(uint16_t(handle), BLE_ERR_AUTH_FAIL);
            return 0;
        }
        return pin.load();
    }
    void onAuthenticationComplete(ble_gap_conn_desc* desc) override {
        const bool valid = desc->sec_state.encrypted && desc->sec_state.authenticated &&
                           desc->sec_state.key_size == 16;
        authenticated.store(valid);
        if (!valid) ble_gap_terminate(desc->conn_handle, BLE_ERR_AUTH_FAIL);
    }
} clientCallbacks;

class ScanCallbacks final : public NimBLEAdvertisedDeviceCallbacks {
    void onResult(NimBLEAdvertisedDevice* adv) override {
        if (!adv->isAdvertisingService(NimBLEUUID(r3_ble::kServiceUuid))) return;
        Device found = {};
        uint8_t id[6];
        const auto address = adv->getAddress().toString();
        if (!r3_ble::parseDevice(address.c_str(), id)) return;
        r3_ble::formatDevice(id, found.address);
        found.type = adv->getAddressType();
        const auto name = adv->getName();
        // Only printable ASCII from an untrusted advertisement reaches JSON.
        size_t n = 0;
        for (char c : name) if (n < sizeof(found.name)-1)
            found.name[n++] = c >= 32 && c <= 126 ? c : '?';
        portENTER_CRITICAL(&statusLock);
        unsigned slot = 0;
        while (slot < status.deviceCount && strcmp(status.devices[slot].address, found.address)) ++slot;
        if (slot < kDevices) {
            status.devices[slot] = found;
            if (slot == status.deviceCount) ++status.deviceCount;
        }
        portEXIT_CRITICAL(&statusLock);
        // Do not stop/clear scan here: NimBLE still owns the advertisement.
    }
} scanCallbacks;

void notification(NimBLERemoteCharacteristic*, uint8_t* bytes, size_t length, bool isNotify) {
    if (!isNotify || !linkUp.load() || !authenticated.load()) return;
    Packet packet = {};
    packet.receiveUs = uint64_t(esp_timer_get_time());
    packet.epoch = callbackEpoch.load();
    if (!packet.epoch) return;
    packet.length = length;
    if (length <= sizeof(packet.bytes)) memcpy(packet.bytes, bytes, length);
    if (xQueueSend(packets, &packet, 0) != pdTRUE) drops.fetch_add(1);
}

void ecoNotification(NimBLERemoteCharacteristic*, uint8_t* bytes, size_t length, bool isNotify) {
    if (!isNotify || !linkUp.load() || !authenticated.load() || length != 96) return;
    EcoPacket packet = {}; packet.receiveUs = monoUs(); packet.epoch = callbackEpoch.load();
    if (!packet.epoch) return;
    packet.length = length; memcpy(packet.bytes, bytes, length);
    if (xQueueSend(ecoPackets, &packet, 0) != pdTRUE) drops.fetch_add(1);
}

int preserveEnrolledBonds(ble_store_status_event* event, void*) {
    // NimBLE's sample default evicts the oldest bond on overflow. A new peer
    // must instead fail pairing; saved trust is removed only by explicit action.
    if (event->event_code == BLE_STORE_EVENT_FULL) return 0;
    return event->event_code == BLE_STORE_EVENT_OVERFLOW ? BLE_HS_ESTORE_CAP : BLE_HS_EUNKNOWN;
}

bool initRadio() {
    if (initialized) return true;
    // NimBLE's supported external host allocator has no internal fallback.
    // Keep RTOS stacks/controller and acquisition DMA staging internal.
    if (!psramFound() || heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM)<131072) {
        setState("ERROR", "BLE needs available PSRAM host-buffer space");
        return false;
    }
    NimBLEDevice::init("R1-S3-Time");
    ble_hs_cfg.store_status_cb = preserveEnrolledBonds;
    NimBLEDevice::setMTU(r3_ble::kPreferredMtu);
    // Secret keys persist in NimBLE NVS; explicit SAVE persists peer policy.
    NimBLEDevice::setSecurityAuth(true, true, true);
    NimBLEDevice::setSecurityIOCap(BLE_HS_IO_KEYBOARD_ONLY);
    client = NimBLEDevice::createClient();
    if (!client) { setState("ERROR", "BLE client allocation failed"); return false; }
    client->setClientCallbacks(&clientCallbacks, false);
    client->setConnectTimeout(5);
    client->setConnectionParams(24, 40, 0, 200);
    scanner = NimBLEDevice::getScan();
    scanner->setAdvertisedDeviceCallbacks(&scanCallbacks);
    scanner->setActiveScan(true);
    scanner->setInterval(120); scanner->setWindow(40); scanner->setMaxResults(0);
    r3_ble::parseDevice(NimBLEDevice::getAddress().toString().c_str(), ownId);
    initialized = true;
    return true;
}

void dropLink() {
    deadlineMs.store(0); callbackEpoch.store(0);
    connectionBeganUs = 0;
    subscribed = pairing = false;
    ecoSubscribed = helloSent = false; ecoUpstream = nullptr;
    timeRequestId = timeRequestStamp = 0; timeActionPending = false;
    receiver.disconnect();
    if (client && client->isConnected()) client->disconnect();
    // Wait boundedly for the host to release this handle before reuse.
    const uint32_t start = millis();
    while (linkUp.load() && millis()-start < 2000) vTaskDelay(pdMS_TO_TICKS(10));
    authenticated.store(false);
    xQueueReset(packets);
    xQueueReset(ecoPackets); xQueueReset(ownerActions);
    receipts.reset();
    publishPolicy();
}

void retry(const char* error) {
    dropLink();
    retryAt = millis()+retryDelay;
    retryDelay = retryDelay < 8000 ? retryDelay*2 : 8000;
    setState("RETRY", error);
}

void publishReceiver(uint64_t now) {
    const auto& c = receiver.counters();
    const auto& observation = receiver.lastAccepted();
    portENTER_CRITICAL(&statusLock);
    status.segment = receiver.segment();
    status.boot = receiver.identity().boot_id;
    status.clockRevision = receiver.identity().clock_revision;
    status.received = c.accepted; status.missing = c.missing_sequences;
    status.duplicates = c.duplicates; status.outOfOrder = c.out_of_order;
    status.malformed = receiver.malformed();
    status.utcValid = receiver.utcEvidenceEligible(now);
    status.receiveUs = observation.local_receive_us;
    status.captureUs = observation.beacon.capture_us;
    status.sequence = observation.beacon.sequence;
    status.unixS = observation.beacon.unix_s;
    portEXIT_CRITICAL(&statusLock);
}

R3BleOwnerSnapshot snapshot() {
    R3BleOwnerSnapshot value;
    portENTER_CRITICAL(&statusLock); value = ownerSnapshot; portEXIT_CRITICAL(&statusLock);
    return value;
}

ecosystem::Phase phaseOf(const R3BleOwnerSnapshot& s) {
    switch (s.state) {
        case R3BleOwnerState::Starting: return ecosystem::Phase::Starting;
        case R3BleOwnerState::Running: return ecosystem::Phase::Recording;
        case R3BleOwnerState::Stopping: return ecosystem::Phase::Stopping;
        case R3BleOwnerState::Error: return ecosystem::Phase::Error;
        default: return s.fileClosed && s.sessionId ? ecosystem::Phase::Closed : ecosystem::Phase::Idle;
    }
}

ecosystem::Frame baseFrame(ecosystem::Kind kind) {
    ecosystem::Frame f;
    f.kind = kind; memcpy(f.sender, ownId, 6); memcpy(f.target, desiredId, 6);
    f.sender_boot = ownBoot; f.target_boot = receiver.identity().boot_id;
    f.stamp_us = monoUs();
    const auto s = snapshot(); f.phase = phaseOf(s); f.session = s.sessionId; f.group = s.groupId;
    const bool timeReady = s.clockSynced && syncedSourceBoot == receiver.identity().boot_id &&
                           syncedRevision == receiver.identity().clock_revision && receiver.utcEvidenceEligible(monoUs());
    f.flags = (remoteAllowed.load() ? ecosystem::RemoteAllowed : 0u) |
              (s.ready && timeReady ? ecosystem::Ready : 0u) | (s.rtcValid ? ecosystem::RtcValid : 0u) |
              (timeReady ? ecosystem::RtcSynced : 0u);
    if (s.state == R3BleOwnerState::Error) f.detail = uint32_t(ecosystem::Detail::Storage);
    return f;
}

bool sendEco(const ecosystem::Frame& f) {
    if (!ecoSubscribed || !ecoUpstream || !trusted.load() || !linkUp.load() || !authenticated.load()) return false;
    uint8_t bytes[ecosystem::kFrameBytes]; ecosystem::encode(f, bytes);
    deadlineMs.store(millis() + 2000);
    const bool okay = ecoUpstream->writeValue(bytes, sizeof(bytes), true);
    deadlineMs.store(0); return okay;
}

void rejectEco(const ecosystem::Frame& command, ecosystem::Detail detail) {
    auto f = baseFrame(ecosystem::Kind::Result);
    f.request = command.request; f.op = command.op; f.group = command.group;
    f.phase = ecosystem::Phase::Rejected; f.detail = uint32_t(detail); sendEco(f);
}

void commandReceived(const ecosystem::Frame& frame, uint64_t now) {
    const uint32_t commandGeneration = startGeneration.load();
    if (!r3_trust::commandForConnection(frame, connectionBeganUs, now)) { rejectEco(frame, ecosystem::Detail::Expired); return; }
    if (frame.op == ecosystem::Op::Query) {
        if (!remoteAllowed.load()) rejectEco(frame, ecosystem::Detail::Permission);
        else sendEco(baseFrame(ecosystem::Kind::Status));
        return;
    }
    if ((frame.op != ecosystem::Op::Start && frame.op != ecosystem::Op::Stop) || !frame.session ||
        (frame.op == ecosystem::Op::Start && !frame.group)) {
        rejectEco(frame, ecosystem::Detail::Invalid); return;
    }
    const auto decision = receipts.admit(frame, now);
    if (decision.admission == ecosystem::CommandCache::Admission::Replay) { sendEco(decision.receipt->result); return; }
    if (decision.admission == ecosystem::CommandCache::Admission::Conflict) { rejectEco(frame, ecosystem::Detail::Conflict); return; }
    if (decision.admission == ecosystem::CommandCache::Admission::Full) { rejectEco(frame, ecosystem::Detail::QueueFull); return; }
    auto* vacant = decision.receipt;
    vacant->result = baseFrame(ecosystem::Kind::Result); vacant->result.request = frame.request;
    vacant->result.op = frame.op; vacant->result.group = frame.group;
    const auto rejectAdmission = [&](ecosystem::Detail detail) {
        vacant->result.phase = ecosystem::Phase::Rejected;
        vacant->result.detail = uint32_t(detail); sendEco(vacant->result);
    };
    if (!remoteAllowed.load()) { rejectAdmission(ecosystem::Detail::Permission); return; }
    const auto s = snapshot();
    uint64_t stopFence;
    portENTER_CRITICAL(&statusLock); stopFence = localStopUs; portEXIT_CRITICAL(&statusLock);
    if (frame.op == ecosystem::Op::Start && frame.stamp_us <= stopFence) {
        rejectAdmission(ecosystem::Detail::Conflict); return;
    }
    if (frame.op == ecosystem::Op::Start && (!s.clockSynced || syncedSourceBoot != receiver.identity().boot_id ||
        syncedRevision != receiver.identity().clock_revision || frame.revision != receiver.identity().clock_revision ||
        !receiver.utcEvidenceEligible(monoUs()))) {
        rejectAdmission(ecosystem::Detail::Clock); return;
    }
    if (frame.op == ecosystem::Op::Start && (!s.ready || !ecosystem::startable(phaseOf(s)))) {
        rejectAdmission(ecosystem::Detail::NotReady); return;
    }
    if (frame.op == ecosystem::Op::Stop && (s.sessionId != frame.session || !ecosystem::active(phaseOf(s)))) {
        // A repeat STOP after successful closure is a successful idempotent
        // observation; it never creates another storage operation.
        if (s.sessionId == frame.session && s.fileClosed) {
            vacant->result.phase = ecosystem::Phase::Closed;
            vacant->result.detail = 0; sendEco(vacant->result); return;
        }
        rejectAdmission(ecosystem::Detail::WrongSession); return;
    }
    R3BleOwnerRequest request;
    request.kind = frame.op == ecosystem::Op::Start ? R3BleOwnerRequest::Start : R3BleOwnerRequest::Stop;
    request.requestId = frame.request; request.sourceBoot = frame.sender_boot; request.targetBoot = ownBoot;
    request.sessionId = frame.session; request.groupId = frame.group; request.epoch = epoch;
    request.clockRevision = frame.revision; request.startGeneration = commandGeneration;
    request.receivedLocalUs = now; request.expiresLocalUs = frame.stamp_us + uint64_t(frame.ttl_ms) * 1000;
    memcpy(request.sourceDevice, frame.sender, 6);
    if (xQueueSend(ownerActions, &request, 0) != pdTRUE) { rejectAdmission(ecosystem::Detail::QueueFull); return; }
    vacant->result.session = frame.session;
    vacant->result.detail = 0;
    vacant->result.phase = ecosystem::Phase::Accepted;
    // Accepted here means queued, never recording or finalized.
    sendEco(vacant->result);
}

void timeReceived(const ecosystem::Frame& frame, uint64_t now) {
    if (!timeRequestId || frame.request != timeRequestId || frame.stamp_us != timeRequestStamp) return;
    const bool eligible = r3_trust::timeReplyEligible(frame, timeRequestId, timeRequestStamp, now);
    timeRequestId = 0;
    if (!eligible) {
        setState("CONNECTED", "R3 time reply invalid or stale; RTC unchanged"); return;
    }
    // Calendar alignment only. No midpoint/airtime precision claim is made.
    // A command queued during STARTING/RUNNING/STOPPING is rejected by owner;
    // the next idle attempt always obtains a new request/reply.
    R3BleOwnerRequest request;
    request.kind = R3BleOwnerRequest::SetTime; request.requestId = frame.request;
    request.sourceBoot = frame.sender_boot; request.targetBoot = ownBoot; request.epoch = epoch;
    request.receivedLocalUs = now; request.expiresLocalUs = now + 1000000;
    request.unixS = uint32_t(frame.value_us / 1000000); request.clockRevision = frame.revision;
    request.sourceReadAgeMs = frame.detail; request.roundtripUs = uint32_t(now - frame.stamp_us);
    memcpy(request.sourceDevice, frame.sender, 6);
    if (xQueueSend(ownerActions, &request, 0) == pdTRUE) {
        timeActionPending = true; pendingTimeDeadlineUs = request.expiresLocalUs + 1000000;
    }
}

void ecosystemStep() {
    if (!ecoSubscribed || !selectedPolicy()) return;
    const uint64_t now = monoUs();
    if (!helloSent) {
        helloSent = sendEco(baseFrame(ecosystem::Kind::Hello));
        if (!helloSent) return;
        nextTimeRequestUs = now;
    }
    EcoPacket packet;
    for (unsigned i = 0; i < 8 && xQueueReceive(ecoPackets, &packet, 0) == pdTRUE; ++i) {
        if (packet.epoch != epoch || !authenticated.load() || !linkUp.load()) continue;
        ecosystem::Frame f;
        if (!ecosystem::decode(packet.bytes, packet.length, f)) { drops.fetch_add(1); continue; }
        if (!ecosystem::sameDevice(f.sender, desiredId) || !ecosystem::sameDevice(f.target, ownId) ||
            f.sender_boot != receiver.identity().boot_id || f.target_boot != ownBoot) continue;
        if (f.kind == ecosystem::Kind::Command) commandReceived(f, packet.receiveUs);
        else if (f.kind == ecosystem::Kind::TimeReply) timeReceived(f, packet.receiveUs);
    }
    Completion completed;
    for (unsigned i = 0; i < 4 && xQueueReceive(completions, &completed, 0) == pdTRUE; ++i) {
        if (completed.request.epoch != epoch) continue;
        if (completed.request.kind == R3BleOwnerRequest::SetTime) {
            timeActionPending = false;
            if (completed.accepted) {
                syncedSourceBoot = completed.request.sourceBoot; syncedRevision = completed.request.clockRevision;
                setState("CONNECTED"); publishPolicy();
            }
            nextTimeRequestUs = now + 3000000;
        } else for (auto& receipt : receipts) if (receipt.used && receipt.command.request == completed.request.requestId) {
            receipt.result = baseFrame(ecosystem::Kind::Result);
            receipt.result.request = receipt.command.request; receipt.result.op = receipt.command.op;
            receipt.result.group = receipt.command.group;
            receipt.result.phase = completed.accepted ? ecosystem::Phase::Accepted : ecosystem::Phase::Rejected;
            if (completed.accepted) receipt.result.session = receipt.command.session;
            receipt.result.detail = completed.accepted ? 0 : uint32_t(ecosystem::Detail::NotReady);
            sendEco(receipt.result);
        }
    }
    const auto s = snapshot();
    if (now - lastStatusUs >= 500000) {
        auto f = baseFrame(ecosystem::Kind::Status);
        if (sendEco(f)) lastStatusUs = now;
        // Convey actual recorder transitions separately from acceptance.
        for (auto& receipt : receipts) if (receipt.used && receipt.result.phase != ecosystem::Phase::Rejected &&
            s.sessionId == receipt.command.session && receipt.result.phase != phaseOf(s)) {
            receipt.result = f; receipt.result.kind = ecosystem::Kind::Result;
            receipt.result.request = receipt.command.request; receipt.result.op = receipt.command.op;
            receipt.result.group = receipt.command.group; sendEco(receipt.result);
        }
    }
    if (timeRequestId && now - timeRequestStamp > 1500000) timeRequestId = 0;
    if (timeActionPending && now > pendingTimeDeadlineUs) timeActionPending = false;
    const bool correctionNeeded = syncedSourceBoot != receiver.identity().boot_id ||
                                  syncedRevision != receiver.identity().clock_revision || !s.clockSynced;
    if (correctionNeeded && s.state == R3BleOwnerState::Ready && !timeRequestId && !timeActionPending && now >= nextTimeRequestUs) {
        auto f = baseFrame(ecosystem::Kind::TimeRequest);
        f.request = (uint64_t(esp_random()) << 32) | esp_random(); if (!f.request) f.request = 1;
        timeRequestId = f.request; timeRequestStamp = f.stamp_us; nextTimeRequestUs = now + 3000000;
        if (!sendEco(f)) timeRequestId = 0;
    }
}

bool discoverAndSubscribe() {
    deadlineMs.store(millis()+12000);
    auto service = client->getService(r3_ble::kServiceUuid);
    if (!service) { retry("R3 time service unavailable"); return false; }
    auto identity = service->getCharacteristic(r3_ble::kIdentityUuid);
    auto beacon = service->getCharacteristic(r3_ble::kBeaconUuid);
    if (!identity || !identity->canRead() || !beacon || !beacon->canNotify()) {
        retry("R3 time characteristics unavailable"); return false;
    }
    const auto value = identity->readValue();
    r3_ble::Identity decoded = {};
    if (!r3_ble::decodeIdentity(value.data(), value.size(), decoded) ||
        !r3_ble::sameDevice(decoded.device_id, desiredId)) {
        retry("R3 identity mismatch or unsupported protocol"); return false;
    }
    if (!linkUp.load() || !authenticated.load() || !r3_ble::supportsMtu(client->getMTU())) {
        retry("Authenticated connection or MTU lost"); return false;
    }
    receiver.bind(decoded);
    publishReceiver(uint64_t(esp_timer_get_time()));
    if (++epoch == 0) ++epoch;
    connectionBeganUs = monoUs();
    callbackEpoch.store(epoch);
    if (!beacon->subscribe(true, notification, true)) {
        retry("R3 beacon subscription failed"); return false;
    }
    ecoUpstream = service->getCharacteristic(ecosystem::kUpstreamUuid);
    auto downstream = service->getCharacteristic(ecosystem::kDownstreamUuid);
    ecoSubscribed = ecoUpstream && ecoUpstream->canWrite() && downstream && downstream->canNotify() &&
        client->getMTU() >= ecosystem::kMinimumMtu && downstream->subscribe(true, ecoNotification, true);
    if (!ecoSubscribed) ecoUpstream = nullptr;
    publishPolicy();
    deadlineMs.store(0);
    subscribed = true; pairing = false; retryDelay = 1000;
    const uint16_t mtu = client->getMTU();
    portENTER_CRITICAL(&statusLock);
    if (status.connections) ++status.reconnects;
    ++status.connections; status.mtu = mtu;
    portEXIT_CRITICAL(&statusLock);
    setState("CONNECTED", ecoSubscribed ? "" : "Ecosystem needs R3 extension and MTU >= 99; S1 only");
    return true;
}

void receivePackets() {
    Packet packet;
    for (unsigned drained=0; drained<12 && xQueueReceive(packets, &packet, 0)==pdTRUE; ++drained) {
        if (!subscribed || !linkUp.load() || packet.epoch != epoch) continue;
        receiver.observe(packet.bytes, packet.length, packet.receiveUs);
        publishReceiver(packet.receiveUs);
    }
}

void handleCommand(const Command& command) {
    if (command.kind == Command::Save) {
        if (!subscribed || !authenticated.load() || !linkUp.load() || !ecoSubscribed ||
            !NimBLEDevice::isBonded(NimBLEAddress(std::string(desiredPeer), desiredType))) {
            setState(subscribed ? "CONNECTED" : "ERROR", "SAVE needs authenticated bonded ecosystem peer"); return;
        }
        r3_trust::Policy saved;
        memcpy(saved.peer, desiredId, 6); saved.addressType = desiredType; saved.remote = command.remote;
        if (!storePolicy(saved)) { setState("CONNECTED", "Peer policy NVS save failed"); return; }
        allowPairing.store(false); pin.store(0); publishPolicy(); helloSent = false;
        setState("CONNECTED"); return;
    }
    desired = false;
    if (scanner && scanner->isScanning()) scanner->stop();
    dropLink();
    if (command.kind == Command::Off) {
        allowPairing.store(false); pin.store(0);
        setState("OFF"); return;
    }
    if (command.kind == Command::Forget) {
        allowPairing.store(false); pin.store(0); trusted.store(false); remoteAllowed.store(false);
        Preferences prefs;
        bool erased = false;
        if (prefs.begin("r1-ecosystem", false)) {
            erased = !prefs.isKey("peer-v1") || prefs.remove("peer-v1"); prefs.end();
        }
        // Even an OFF/boot-time client can have persistent NimBLE keys. Bring
        // up its host before erasing, otherwise FORGET would leave stale keys.
        const bool radioReady = initRadio();
        if (radioReady) NimBLEDevice::deleteAllBonds();
        policyPresent = false; syncedSourceBoot = 0; syncedRevision = 0; desiredPeer[0] = 0;
        publishPolicy(); setState(erased && radioReady ? "OFF" : "ERROR",
            !erased ? "NVS forget failed; retry FORGET" : !radioReady ? "Bond erase unavailable; retry FORGET" : ""); return;
    }
    if (!initRadio()) return;
    if (command.kind == Command::Scan) {
        allowPairing.store(false); pin.store(0);
        portENTER_CRITICAL(&statusLock); status.deviceCount = 0; portEXIT_CRITICAL(&statusLock);
        if (scanner->start(5, static_cast<void (*)(NimBLEScanResults)>(nullptr), false)) setState("SCANNING");
        else setState("ERROR", "BLE discovery could not start");
        return;
    }
    if (command.kind == Command::On) {
        if (!policyPresent) { setState("OFF", policyInvalid ? "Unsupported peer policy; FORGET and enroll again" : "No saved R3; CONNECT then SAVE first"); return; }
        r3_ble::formatDevice(policy.peer, desiredPeer); memcpy(desiredId, policy.peer, 6);
        desiredType = policy.addressType; pin.store(0); allowPairing.store(false);
        if (!NimBLEDevice::isBonded(NimBLEAddress(std::string(desiredPeer), desiredType))) {
            publishPolicy(); setState("ERROR", "Saved peer has no bond; explicitly enroll again"); return;
        }
    } else {
        snprintf(desiredPeer, sizeof(desiredPeer), "%s", command.peer);
        r3_ble::parseDevice(desiredPeer, desiredId); pin.store(command.pin); allowPairing.store(true);
        desiredType = BLE_ADDR_PUBLIC;
    }
    portENTER_CRITICAL(&statusLock);
    snprintf(status.peer, sizeof(status.peer), "%s", desiredPeer);
    for (unsigned i=0; command.kind == Command::Connect && i<status.deviceCount; ++i)
        if (!strcmp(desiredPeer, status.devices[i].address)) desiredType = status.devices[i].type;
    portEXIT_CRITICAL(&statusLock);
    desired = true; retryDelay = 1000; retryAt = millis();
    publishPolicy();
    setState("CONNECTING");
}

void worker(void*) {
    if (loadPolicy()) {
        Command bootCommand = {}; bootCommand.kind = Command::On; handleCommand(bootCommand);
    } else if (policyInvalid) setState("OFF", "Unsupported peer policy; FORGET and enroll again");
    for (;;) {
        Command command;
        if (xQueueReceive(commands, &command, 0) == pdTRUE) handleCommand(command);
        if (desired) {
            if ((subscribed || pairing) && !linkUp.load()) retry("R3 disconnected; retrying selected device");
            if (pairing && linkUp.load()) {
                if (authenticated.load()) discoverAndSubscribe();
                else if (millis()-pairingAt >= 15000) retry("Pairing timed out; verify R3 PIN");
            }
            if (!subscribed && !pairing && int32_t(millis()-retryAt) >= 0) {
                setState("CONNECTING");
                if (!client->connect(NimBLEAddress(std::string(desiredPeer), desiredType), true))
                    retry("R3 connection failed");
                else if (!r3_ble::supportsMtu(client->getMTU())) retry("R3 MTU below 67; cannot carry a beacon");
                else {
                    setState("PAIRING"); pairing = true; pairingAt = millis();
                    // Nonblocking security initiation: worker still handles OFF
                    // and the 15-second deadline instead of waiting indefinitely.
                    if (NimBLEDevice::startSecurity(client->getConnId()) != 0) retry("R3 pairing could not start");
                }
            }
            receivePackets();
            ecosystemStep();
        } else if (initialized && scanner && !scanner->isScanning()) {
            bool done;
            portENTER_CRITICAL(&statusLock); done = !strcmp(status.state,"SCANNING"); portEXIT_CRITICAL(&statusLock);
            if (done) setState("READY");
        }
        const uint32_t stackFree = uxTaskGetStackHighWaterMark(nullptr);
        portENTER_CRITICAL(&statusLock);
        status.stackFree = stackFree;
        portEXIT_CRITICAL(&statusLock);
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

String quoted(const char* text) {
    String out("\"");
    for (; *text; ++text) {
        const unsigned char c = *text;
        if (c=='"' || c=='\\') out+='\\';
        out += c >= 32 ? char(c) : '?';
    }
    return out+'"';
}
String decimal(uint64_t value) {
    char text[24]; snprintf(text,sizeof(text),"%llu",(unsigned long long)value); return quoted(text);
}
} // namespace

void r3BleBegin() {
    if (workerHandle) return;
    ownBoot = (uint64_t(esp_random()) << 32) | esp_random(); if (!ownBoot) ownBoot = 1;
    esp_read_mac(ownId, ESP_MAC_BT);
    commands = xQueueCreate(2, sizeof(Command));
    packets = xQueueCreate(12, sizeof(Packet));
    ecoPackets = xQueueCreate(8, sizeof(EcoPacket));
    ownerActions = xQueueCreate(4, sizeof(R3BleOwnerRequest));
    completions = xQueueCreate(4, sizeof(Completion));
    esp_timer_create_args_t args = {};
    args.callback = operationGuard; args.name = "r3ble-guard";
    setState("OFF");
    if (!commands || !packets || !ecoPackets || !ownerActions || !completions || esp_timer_create(&args,&guardTimer) != ESP_OK ||
        esp_timer_start_periodic(guardTimer,100000) != ESP_OK ||
        xTaskCreatePinnedToCore(worker,"r3ble",12288,nullptr,1,&workerHandle,0) != pdPASS) {
        setState("ERROR","BLE worker allocation failed"); return;
    }
}

bool r3BleCommand(const char* argument, const char*& message) {
    if (!workerHandle) { message="BLE worker unavailable"; return false; }
    Command c = {};
    if (!strcmp(argument,"SCAN")) c.kind=Command::Scan;
    else if (!strcmp(argument,"OFF")) c.kind=Command::Off;
    else if (!strcmp(argument,"ON")) c.kind=Command::On;
    else if (!strcmp(argument,"FORGET")) c.kind=Command::Forget;
    else if (!strcmp(argument,"SAVE") || !strcmp(argument,"SAVE 0") || !strcmp(argument,"SAVE 1")) {
        c.kind=Command::Save; c.remote=!strcmp(argument,"SAVE 1");
    }
    else if (!strncmp(argument,"CONNECT ",8) && strlen(argument)==32 && argument[25]==' ') {
        c.kind=Command::Connect;
        memcpy(c.peer,argument+8,17);
        uint8_t id[6];
        if (!r3_ble::parseDevice(c.peer,id)) {message="Invalid R3 address";return false;}
        r3_ble::formatDevice(id,c.peer);
        for (unsigned i=26;i<32;++i) {
            if (argument[i]<'0'||argument[i]>'9') {message="R3 PIN must have six digits";return false;}
            c.pin=c.pin*10+uint32_t(argument[i]-'0');
        }
    } else {message="Use BLE SCAN, CONNECT address PIN, SAVE 0|1, ON, OFF, or FORGET";return false;}
    if (xQueueSend(commands,&c,0)!=pdTRUE) {message="BLE command queue busy";return false;}
    message="BLE command queued; check connection status"; return true;
}

String r3BleStatusJson() {
    Status s; bool ownerSynced;
    portENTER_CRITICAL(&statusLock); s=status; ownerSynced=ownerSnapshot.clockSynced; portEXIT_CRITICAL(&statusLock);
    const uint64_t now=uint64_t(esp_timer_get_time());
    const bool connected=s.connected && linkUp.load() && authenticated.load();
    const bool fresh=connected && s.receiveUs && now>=s.receiveUs && now-s.receiveUs<r3_time::kStaleAfterUs;
    String out;out.reserve(1600);
    out="{\"enabled\":"+String(s.enabled?"true":"false")+",\"state\":"+quoted(s.state)+",\"peer\":"+quoted(s.peer);
    out+=",\"authenticated\":"+String(connected?"true":"false")+",\"fresh\":"+String(fresh?"true":"false")+",\"utc_valid\":"+String(fresh&&s.utcValid?"true":"false");
    out+=",\"synchronized\":false,\"coarse\":true,\"uncertainty_us\":null,\"bonding\":true";
    out+=",\"enrolled\":"+String(s.enrolled?"true":"false")+",\"remote_allowed\":"+String(s.remote?"true":"false");
    const bool aligned=ownerSynced&&s.rtcSynced&&s.correctionBoot==s.boot&&s.correctionRevision==s.clockRevision;
    out+=",\"ecosystem\":"+String(connected&&s.ecosystem?"true":"false")+",\"rtc_synced\":"+String(aligned?"true":"false");
    out+=",\"source_boot\":"+decimal(s.boot)+",\"clock_revision\":"+String(s.clockRevision)+",\"segment\":"+decimal(s.segment);
    out+=",\"last_sequence\":"+String(s.sequence)+",\"age_ms\":"+(s.receiveUs&&now>=s.receiveUs?String(uint32_t((now-s.receiveUs)/1000)):String("null"));
    out+=",\"source_capture_us\":"+decimal(s.captureUs)+",\"local_receive_us\":"+decimal(s.receiveUs)+",\"source_unix_s\":"+String(s.unixS);
    out+=",\"received\":"+decimal(s.received)+",\"missing\":"+decimal(s.missing)+",\"malformed\":"+decimal(s.malformed)+",\"duplicates\":"+decimal(s.duplicates)+",\"out_of_order\":"+decimal(s.outOfOrder);
    out+=",\"drops\":"+String(drops.load())+",\"reconnects\":"+String(s.reconnects)+",\"connections\":"+String(s.connections)+",\"last_error\":"+quoted(s.error)+",\"mtu\":"+String(s.mtu)+",\"stack_free\":"+String(s.stackFree)+",\"devices\":[";
    for (unsigned i=0;i<s.deviceCount;++i) {
        if(i)out+=',';
        out+="{\"address\":"+quoted(s.devices[i].address)+",\"name\":"+quoted(s.devices[i].name)+"}";
    }
    return out+"]}";
}

uint64_t r3BleBootId() { return ownBoot; }
void r3BleCopyDeviceId(uint8_t out[6]) { if (out) memcpy(out, ownId, 6); }
bool r3BleRemoteAllowed() { return trusted.load() && remoteAllowed.load(); }
void r3BleCancelPendingStarts() {
    const uint64_t now = monoUs();
    portENTER_CRITICAL(&statusLock);
    startGeneration.fetch_add(1); localStopUs = now;
    portEXIT_CRITICAL(&statusLock);
}
void r3BlePublishOwner(const R3BleOwnerSnapshot& value) {
    portENTER_CRITICAL(&statusLock); ownerSnapshot = value; portEXIT_CRITICAL(&statusLock);
}
bool r3BleTakeOwnerAction(R3BleOwnerRequest& request) {
    return ownerActions && xQueueReceive(ownerActions, &request, 0) == pdTRUE;
}
bool r3BleOwnerActionCurrent(const R3BleOwnerRequest& request) {
    if (!trusted.load() || !authenticated.load() || !linkUp.load() || request.targetBoot != ownBoot ||
        !request.epoch || request.epoch != callbackEpoch.load() || monoUs() > request.expiresLocalUs) return false;
    uint64_t sourceBoot, receivedUs; uint32_t sourceRevision; bool clockSynced, sourceValid;
    portENTER_CRITICAL(&statusLock);
    sourceBoot = status.boot; sourceRevision = status.clockRevision; clockSynced = ownerSnapshot.clockSynced;
    receivedUs = status.receiveUs; sourceValid = status.utcValid;
    portEXIT_CRITICAL(&statusLock);
    if (request.sourceBoot != sourceBoot) return false;
    if (request.kind == R3BleOwnerRequest::Start &&
        (request.startGeneration != startGeneration.load() || request.clockRevision != sourceRevision || !clockSynced ||
         !sourceValid || !receivedUs || monoUs() - receivedUs > r3_time::kStaleAfterUs)) return false;
    if (request.kind == R3BleOwnerRequest::SetTime && request.clockRevision != sourceRevision &&
        uint32_t(request.clockRevision - sourceRevision) >= 0x80000000u) return false;
    return request.kind == R3BleOwnerRequest::SetTime || remoteAllowed.load();
}
void r3BleCompleteOwnerAction(const R3BleOwnerRequest& request, bool accepted, const char* message) {
    Completion completion = {}; completion.request = request; completion.accepted = accepted;
    snprintf(completion.message, sizeof(completion.message), "%s", message ? message : "");
    if (completions && xQueueSend(completions, &completion, 0) != pdTRUE) drops.fetch_add(1);
}
