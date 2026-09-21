# Shared-network Wi-Fi

The network task runs AP+STA. The existing AP remains available; STA joins up to
three saved 2.4 GHz profiles, with a bounded 20-second attempt per profile.
Reconnect rotates profiles without blocking the acquisition task. mDNS advertises
r1-s3-<device suffix>.local; the DHCP address, connected SSID and RSSI are exposed
in station status. Downloads redirect using the receiving socket's local IP,
so both AP and LAN clients remain on a reachable interface.

A private ignored firmware/include/wifi_secrets.h can supply WifiSeed entries
for first-boot provisioning. Normal public builds work without this file and
start with the AP only. NVS namespace r1-wifi stores complete profile blobs and
count, separate from measurement EEPROM. The UI WIFI command changes the primary
profile only, is queued to the network task and checked against recording/file
activity both before queueing and before writing. Acceptance means queued; check
station status for persistence errors or successful connection. Retry is explicit.

Credentials are not included in station status, CSV, configuration exports or
reports. Private seeded firmware binaries must not be published. The existing
HTTP panel is for a trusted local network; no router port forwarding is needed.

TTGO was audited read-only. OTA/captive portal behavior was not copied. Physical
LAN results and limitations are in WORK_REPORT.md.
