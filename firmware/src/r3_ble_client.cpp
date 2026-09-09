#include "r3_ble_client.h"
#include "r3_ble_protocol.h"
#include "r3_ble_receiver.h"
#include <NimBLEDevice.h>
#include <esp_timer.h>
#include <esp_heap_caps.h>
#include <atomic>

#if MYNEWT_VAL(BLE_SM_LEGACY) || MYNEWT_VAL(BLE_STORE_CONFIG_PERSIST)
#error "S1 requires Secure Connections only and volatile BLE storage"
#endif

namespace {
constexpr unsigned kDevices = 6;
struct Device { char address[18]; char name[32]; uint8_t type; };
struct Status {
    bool enabled, authenticated, utcValid, connected;
    char state[16], peer[18], error[56];
    uint64_t boot, segment, received, missing, malformed, duplicates, outOfOrder;
    uint64_t receiveUs, captureUs;
    uint32_t clockRevision, sequence, unixS, connections, reconnects, stackFree;
    uint16_t mtu;
    unsigned deviceCount;
    Device devices[kDevices];
};
struct Command { enum Kind { Scan, Connect, Off } kind; char peer[18]; uint32_t pin; };
struct Packet { uint8_t bytes[r3_ble::kBeaconBytes]; size_t length; uint64_t receiveUs; uint32_t epoch; };
Status status = {};
portMUX_TYPE statusLock = portMUX_INITIALIZER_UNLOCKED;
QueueHandle_t commands = nullptr, packets = nullptr;
TaskHandle_t workerHandle = nullptr;
std::atomic<bool> linkUp(false), authenticated(false);
std::atomic<uint32_t> pin(0), callbackEpoch(0), drops(0), deadlineMs(0);
std::atomic<int> activeHandle(-1);
esp_timer_handle_t guardTimer = nullptr;
NimBLEClient* client = nullptr;
NimBLEScan* scanner = nullptr;
bool initialized = false, desired = false, subscribed = false, pairing = false;
char desiredPeer[18] = {};
uint8_t desiredId[6] = {}, desiredType = BLE_ADDR_PUBLIC;
uint32_t retryAt = 0, retryDelay = 1000, pairingAt = 0, epoch = 0;
r3_ble::Receiver receiver;

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
    uint32_t onPassKeyRequest() override { return pin.load(); }
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

bool initRadio() {
    if (initialized) return true;
    // NimBLE's supported external host allocator has no internal fallback.
    // Keep RTOS stacks/controller and acquisition DMA staging internal.
    if (!psramFound() || heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM)<131072) {
        setState("ERROR", "BLE needs available PSRAM host-buffer space");
        return false;
    }
    NimBLEDevice::init("R1-S3-Time");
    NimBLEDevice::setMTU(r3_ble::kPreferredMtu);
    // MYNEWT build flags also prohibit legacy pairing and persistent BLE store.
    NimBLEDevice::setSecurityAuth(false, true, true);
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
    initialized = true;
    return true;
}

void dropLink() {
    deadlineMs.store(0); callbackEpoch.store(0);
    subscribed = pairing = false;
    receiver.disconnect();
    if (client && client->isConnected()) client->disconnect();
    // Wait boundedly for the host to release this handle before reuse.
    const uint32_t start = millis();
    while (linkUp.load() && millis()-start < 2000) vTaskDelay(pdMS_TO_TICKS(10));
    authenticated.store(false);
    xQueueReset(packets);
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
    callbackEpoch.store(epoch);
    if (!beacon->subscribe(true, notification, true)) {
        retry("R3 beacon subscription failed"); return false;
    }
    deadlineMs.store(0);
    subscribed = true; pairing = false; retryDelay = 1000;
    const uint16_t mtu = client->getMTU();
    portENTER_CRITICAL(&statusLock);
    if (status.connections) ++status.reconnects;
    ++status.connections; status.mtu = mtu;
    portEXIT_CRITICAL(&statusLock);
    setState("CONNECTED");
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
    desired = false;
    if (scanner && scanner->isScanning()) scanner->stop();
    dropLink();
    if (command.kind == Command::Off) {
        pin.store(0); desiredPeer[0] = 0;
        setState("OFF"); return;
    }
    if (!initRadio()) return;
    if (command.kind == Command::Scan) {
        pin.store(0);
        portENTER_CRITICAL(&statusLock); status.deviceCount = 0; portEXIT_CRITICAL(&statusLock);
        if (scanner->start(5, static_cast<void (*)(NimBLEScanResults)>(nullptr), false)) setState("SCANNING");
        else setState("ERROR", "BLE discovery could not start");
        return;
    }
    snprintf(desiredPeer, sizeof(desiredPeer), "%s", command.peer);
    r3_ble::parseDevice(desiredPeer, desiredId); pin.store(command.pin);
    desiredType = BLE_ADDR_PUBLIC;
    portENTER_CRITICAL(&statusLock);
    snprintf(status.peer, sizeof(status.peer), "%s", desiredPeer);
    for (unsigned i=0; i<status.deviceCount; ++i)
        if (!strcmp(desiredPeer, status.devices[i].address)) desiredType = status.devices[i].type;
    portEXIT_CRITICAL(&statusLock);
    desired = true; retryDelay = 1000; retryAt = millis();
    setState("CONNECTING");
}

void worker(void*) {
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
    commands = xQueueCreate(2, sizeof(Command));
    packets = xQueueCreate(12, sizeof(Packet));
    esp_timer_create_args_t args = {};
    args.callback = operationGuard; args.name = "r3ble-guard";
    if (!commands || !packets || esp_timer_create(&args,&guardTimer) != ESP_OK ||
        esp_timer_start_periodic(guardTimer,100000) != ESP_OK ||
        xTaskCreatePinnedToCore(worker,"r3ble",8192,nullptr,1,&workerHandle,0) != pdPASS) {
        setState("ERROR","BLE worker allocation failed"); return;
    }
    setState("OFF");
}

bool r3BleCommand(const char* argument, const char*& message) {
    if (!workerHandle) { message="BLE worker unavailable"; return false; }
    Command c = {};
    if (!strcmp(argument,"SCAN")) c.kind=Command::Scan;
    else if (!strcmp(argument,"OFF")) c.kind=Command::Off;
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
    } else {message="Use BLE SCAN, CONNECT address PIN, or OFF";return false;}
    if (xQueueSend(commands,&c,0)!=pdTRUE) {message="BLE command queue busy";return false;}
    message="BLE command queued; check connection status"; return true;
}

String r3BleStatusJson() {
    Status s;
    portENTER_CRITICAL(&statusLock); s=status; portEXIT_CRITICAL(&statusLock);
    const uint64_t now=uint64_t(esp_timer_get_time());
    const bool connected=s.connected && linkUp.load() && authenticated.load();
    const bool fresh=connected && s.receiveUs && now>=s.receiveUs && now-s.receiveUs<r3_time::kStaleAfterUs;
    String out;out.reserve(1600);
    out="{\"enabled\":"+String(s.enabled?"true":"false")+",\"state\":"+quoted(s.state)+",\"peer\":"+quoted(s.peer);
    out+=",\"authenticated\":"+String(connected?"true":"false")+",\"fresh\":"+String(fresh?"true":"false")+",\"utc_valid\":"+String(fresh&&s.utcValid?"true":"false");
    out+=",\"synchronized\":false,\"coarse\":true,\"uncertainty_us\":null,\"bonding\":false";
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
