# Project context review

Review date: 2026-09-06. This summary captures relevant findings from the earlier logger projects. The detailed historical workspace inventory and comparison counts remain in the [Ukrainian owner notes](uk/project-context-review.md).

## Architecture and previous work

R1-S3 and Lily Logger R3 have different architectures. R1-S3 uses ESP32-S3 + INA228 with SPI SD, SH1106G OLED, 24C32 and DS3231. Lily R3 uses STM32H755 + ADS131M08; ESP32-S3 acts as its Control Center.

In R3, CM7 handles eight-channel 24-bit acquisition and recording; CM4 handles IPC/live/history/transport; ESP handles UART control, HTTP UI/API and scheduling. Earlier documentation reports 4/8/16 kSPS recording tests, with 32 kSPS bench-only. FILELOG V2 uses a 512-byte header, 8704-byte physical records, a 512-byte END record and separate TCHK checkpoints. FRAM stores profiles and diagnostics.

The reviewed R3 HEAD was `cdfa3b9` (2026-06-26), recording profile save-plan dry-run. Uncommitted work adds actual Recording Profile 1B persistence. Its presence does not prove hardware validation. Existing changes and snapshots were left intact; snapshots were not identical to the current tree.

R3 Control Center uses RV3028 RTC at `0x52`, SDA=41/SCL=42, and UART1 RX=16/TX=15 at 2 Mbaud. These settings must not be copied into the R1-S3 DS3231/I²C configuration.

## Previous firmware on this ESP32-S3

R3 commit `d4b9a66` (2026-04-20) contains the CCTX RX minimal receiver startup text, CCTX_RX/CCTX_RX2 counters and p=print/r=reset commands seen in the owner's screenshots. This is a strong source-level match, not a binary identification; a nearby intermediate build may have been installed. That receiver was derived from an earlier project with logger peripherals removed. A complete old INA226/R1 application was not found in the reviewed locations.

## USB and eFuse findings

The earlier Control Center is PlatformIO + Arduino, not a standalone native ESP-IDF application. Its configuration includes USB_MODE=1 and USB_CDC_ON_BOOT=1; a saved alternative omits these flags. These options change Serial routing and do not establish a solution for BOOT/EN or physical USB faults.

Targeted searches of authored files and relevant text inside 66 ZIP archives found no eFuse burn/write or download-disable operations. Actual eFuses, global command history, unrelated directories and every binary artifact were not inspected. This is not proof that eFuses were never modified. No eFuses were changed during the review.

## Current continuation point

I²C, basic SD, OLED and sample EEPROM write/restore tests are confirmed. DS3231 ticks but needs valid time; INA228 functional checks remain pending. Flash/PSRAM detection is not a stress test. See the [current bring-up record](bring-up.md) for precise evidence and outstanding measurements.

OLED output cannot identify which UART/USB build environment was flashed because the display behavior is shared. Heating/cleaning correlated with temporary upload improvement but does not establish a cause. Obtain EN/GPIO0 measurements during bootloader entry before drawing further conclusions.

## Review limits

The review covered folder mapping, key documentation, selected authored firmware, Git history and working-tree diffs, source comparisons and archive inspection. It was not a line-by-line review of vendor code, a test of every binary, or a repeat of historical hardware validation. Old project files and archives were not modified.

## Additional source discovery — 2026-09-07

The later review of Desktop/Logger_Analysis **did locate INA226/R1 firmware**, including an archived STAB candidate. This supersedes the earlier search's limited finding that R1 was not found in the directories then reviewed. See [legacy R1 and viewer analysis](legacy-r1-analysis.md).
