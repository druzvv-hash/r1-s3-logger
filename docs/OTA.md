# R1 Wi-Fi firmware update

Firmware 0.35 adds browser OTA at `/update`, linked from the Wi-Fi tab.
Open the device directly on its LAN IP or AP address, not the PC USB bridge.
Username: `admin`. Password: the existing R1 access-point password displayed in
its Wi-Fi panel. Select `.pio/build/esp32-s3-usb/firmware.bin` from this project.
Do not use a bootloader, partition table, merged image or another ESP32-S3 project.
The page displays upload progress, waits for validation and returns to the panel
following reboot. This is HTTP browser OTA, not the ArduinoOTA/espota IDE protocol.

Initial installation uses USB; subsequent updates can use Wi-Fi. Both existing
4.5 MiB application slots are retained. Settings/EEPROM, NVS Wi-Fi and SD files
are not erased. The signed-image/automatic unhealthy-boot rollback features are
not enabled: a valid but broken application can still require USB recovery.

The hardware owner rejects maintenance during recording or linked recording,
and obtains the SD request gate only when no file session is active. It pauses
acquisition and command processing until failure or reboot; another core handles
the upload. New SD requests cannot enter the storage owner while the gate is held.
Invalid size, wrong chip header, short uploads and Update validation failures do
not activate the candidate slot. The completed HTTP request activates the image.

Use on a trusted local network. Basic authentication reuses the AP password;
the existing panel exposes that password and other unauthenticated controls.
This is an accidental-update guard, not hostile-LAN isolation or HTTPS. The
same-origin/custom-header check blocks ordinary cross-site form uploads.

`/api/ota` exposes current slot and maximum image size with the same credentials.
`tools/test_ota_hardware.py` is an explicit physical test (not CI): it sends bad
images and a real application update to the configured idle test device.
