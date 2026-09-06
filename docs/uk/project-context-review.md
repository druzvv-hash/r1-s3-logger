> Оновлення після огляду: поточний R1-S3 перенесено з C:\Projekts\r1-s3-logger до C:\Projects\r1-s3-logger поруч із Lily R3. Шляхи нижче описують стан на момент огляду.

# Контекст C:\Projects і C:\Projekts

Дата огляду: 2026-09-06. Мета — відновити історію роботи та контекст діагностики R1-S3. Старі проєкти, архіви й налаштування не змінювалися; прошивання під час огляду не виконувалося.

## Головні висновки

1. Це дві різні робочі папки з кількома поколіннями проєктів. C:\Projekts — узгоджене місце активного R1-S3; C:\Projects містить основний попередній репозиторій Lily Logger R3.
2. Lily R3 і R1-S3 — різні апаратні архітектури. Lily R3: STM32H755 + ADS131M08, ESP32-S3 як Control Center. R1-S3: ESP32-S3 + INA228, власні SD/OLED/24C32/DS3231.
3. Старий вивід CCTX на поточному модулі відповідає лінії ESP32-приймача Lily R3. У Git знайдено коміт d4b9a66 від 2026-04-20 із тими самими стартовими рядками та лічильниками.
4. У переглянутих прикладних файлах не знайдено операцій запису eFuse чи вимкнення download mode. Це не є читанням реальних eFuse і не виключає колишніх ручних команд з інших місць.
5. Поточний R1-S3 уже має підтверджені I2C, базовий SD, OLED та EEPROM тести. RTC відлічує час, але повідомляє SET TIME. Невирішена проблема — нестабільний вхід у ROM-завантажувач, не відсутність працездатної прошивки взагалі.

## Карта папок

| Шлях | Що містить | Як використовувати |
|---|---|---|
| C:\Projects\lily-logger-r3 | Основний Git-репозиторій R3, STM32 CM7/CM4, ESP Control Center, документація | Головне джерело історії Lily R3; є незакомічена робота |
| C:\Projects\r3_rec_profile_1b_snapshot | 15 файлів часткового знімка Recording Profile 1B, включно з NOTES | Знімок окремого етапу, не самостійний повний проєкт |
| C:\Projects\r3_rec_profile_1b_fram_snapshot | 5 файлів конфігурації/FRAM | Ще вужчий знімок, не повний репозиторій |
| C:\Projects\Beckup | 19 ZIP та 62 .bak; назви березня–квітня 2026, CubeMX backup | Історичні резервні матеріали |
| C:\Projects\KBD | KeyBit HU66 v0.3.5-alpha, локальний браузерний аналіз фото, README/roadmap/validation | Окремий проєкт, не firmware логера |
| C:\Projekts\r1-s3-logger | Поточний новий Git-репозиторій, HWTEST v0.6 | Робочий проєкт цієї розмови |
| C:\Projekts\STM32_ADS131M08_V1_0 | STM32H755ZIT6, CM7/CM4, ADS/FRAM/SD, CubeMX/CubeIDE | Попереднє дерево STM32; не тотожне Lily R3 |
| C:\Projekts\STM32 | STM32H755ZIT6, CM7/CM4, CubeMX/IAR структура | Раніший STM32-проєкт |
| C:\Projekts\TEMP | Варіанти STM32, Inc/Src, експерименти DMA/CRC, ZIP і 7z | Тимчасові та історичні матеріали, не автоматично актуальна версія |
| C:\Projekts\Bekup | 37 ZIP та розпаковані snapshots; лютий–березень 2026 | Історія 1CH/8CH/DMA/LL/CRC, FRAM, ADS service, SDMMC |
| C:\Projekts\.metadata | Службові дані IDE | Не джерело прошивки; докладно не аналізувалося |

## Lily Logger R3: що вже зроблено

Джерела: README_UA.md, NOTES.md, docs/ipc_live_mirror_cm7_cm4_note.md, прикладні вихідники, Git log/diff. Позначення «підтверджено» нижче означає зафіксований результат попередніх сесій у документації, а не повторний апаратний тест під час цього огляду.

- CM7: збір 8 каналів 24-bit ADS131M08 через DRDY/SPI DMA, профілі та запис у SD. CM4: IPC live mirror, decimation/history, CCTX transport. ESP32-S3: UART control link, Wi-Fi HTTP UI/API, scheduling і wall-time.
- Історія Git починається 2026-03-29: FRAM-профілі SD, tune/save, runtime hardening. Далі FATFS smoke, DMA/буфери, повноцінний FILELOG, IPC і ESP Control Center.
- 4/8/16 kSPS описані як перевірені режими запису. 32 kSPS лишається bench-only з обмеженнями timing margin.
- FILELOG V2: RFL2 header 512 bytes, physical records 8704 bytes, END2 512 bytes; окремі TCHK checkpoints. Первинні ADC дані та метадані — основа повторного аналізу.
- GAIN, wanted profile, runtime shadow та APPLIED gate розділені. CLOCK/MODE мають окремі обмеження; не переносити правила ADS у драйвер INA228 механічно.
- Є SD reserve/free telemetry, FRAM blackbox і bootlog, транспорт діагностики, operator readiness UI, профілі output SPS/decimation.
- RTC попереднього CC — **RV3028**, SDA=41, SCL=42, адреса 0x52. Це не DS3231 на GPIO8/9 з поточної плати.
- UART1 між ESP і STM32: RX=16, TX=15, 2 Mbaud. Це не UART0-консоль CP210x і не I2C нашого R1-S3.
- CC має власні cctx_uart_rx, decoder, consumer, time, scheduler. Поточний cc/src/main.cpp — великий модуль із вбудованим HTML/JS та API; його не слід переносити цілком у новий HWTEST.

### Актуальність документації та незавершена робота

README_UA має якір 2026-06-17; він відстає від NOTES і Git. HEAD на момент огляду: **cdfa3b9, 2026-06-26, add recording profile save-plan dry-run**. Попередні коміти включають FRAM bootlog, recording output SPS decimation і виправлення TCHK cadence при низькому output SPS.

NOTES від 26.06 фіксує REC.PROFILE.1A як preview-only save-plan. Наступний крок у ньому — REC.PROFILE.1B: запис wanted Recording Output SPS у FRAM без автоматичного застосування runtime FILELOG чи ADS CLOCK.

Робоче дерево вже містить **10 змінених tracked-файлів, 378 доданих / 32 видалених рядки**, плюс cc/.vscode/settings.json untracked. Зміни додають реальний save profile запит у UI/API/transport, mailbox-поля, CM7 handling, persistent rec_output_* поля та backward-compatible читання старого FRAM payload. Наявність коду не доводить завершення його перевірки. Цю роботу зберігати; не reset/clean і не накладати snapshot поверх неї.

Порівняння прикладних .c/.cpp/.h/.ioc файлів за однаковими відносними шляхами:

| Порівняння | Однакові | Відрізняються | Немає у цілі |
|---|---:|---:|---:|
| STM32 → TEMP/STM32 | 17 | 5 | 4 |
| STM32_ADS131M08_V1_0 → Lily firmware/stm32 | 32 | 40 | 0 |
| rec_profile_1b_snapshot → Lily | 6 | 8 | 0 |
| rec_profile_1b_fram_snapshot → Lily | 3 | 2 | 0 |

Це порівняння байтів, не семантична оцінка змін; vendor/generated каталоги виключені. Знімки не є точними дублями поточного дерева.

## Походження старої прошивки на ESP

`git show d4b9a66:cc/src/main.cpp` містить:

- CCTX RX minimal receiver start;
- CCTX_RX з bytes/ok/crc_fail/bad_magic/bad_ver/bad_type;
- CCTX_RX2 зі status/hist/chunk/last_seq/epoch/CRC;
- Commands: p=print, r=reset;
- UART1 RX=16, TX=15, 2000000 baud, статистика кожні 3 секунди.

Це сильний збіг із надісланими скриншотами старої програми. Точний бінарний образ не зіставлявся: у скриншоті стартова UART-строка не показувала TX, тому можливий близький проміжний варіант. Наступний коміт ef4a976 того ж дня розвиває decoder/mirror consumer.

cc/README_CCTX_MIN.txt прямо описує походження з R2: було прибрано ADS1256, ADS1115, FRAM, SD, LittleFS і PSRAM logger pipeline, залишено CCTX receiver. Окрему повну стару INA226/R1-прошивку в оглянутих місцях не знайдено.

## USB, ESP-IDF та eFuse

- Старий cc/platformio.ini: **PlatformIO + Arduino**, не окремий native ESP-IDF application. Використання ESP-IDF API всередині Arduino саме по собі не означає інший тип проєкту.
- USB_MODE=1 і USB_CDC_ON_BOOT=1 є у поточному старому ini та у квітневому Git-коміті. Поруч cc/platformio_ok.txt містить OPI/32MB конфігурацію, але без цих USB define. Це збережений варіант налаштування; назва «ok» не є нашим апаратним доказом.
- Поточний USB CDC profile змінює маршрутизацію Serial. Він не виправляє автоматично BOOT/EN або фізичну USB-лінію.
- У поточному R1-S3 головний профіль **esp32-s3-uart-manual**, COM5, CDC=0, before_reset=no_reset, after_reset=no_reset, upload 115200. USB profile та звичайний UART profile збережені.
- Ні наявність ESP-IDF extension у VS Code, ні старий Arduino код не доводять програмування eFuse.
- Пошук у прикладних файлах та відповідних текстових членах 66 ZIP не знайшов burn_efuse, esp_efuse_write або DIS_DOWNLOAD_MODE. У розпакованих файлах додатково шукали DIS_USB/CONFIG_ESP_CONSOLE. Не читали реальні eFuse, глобальну історію команд, сторонні каталоги й усі бінарні артефакти; 7z не розпаковували.
- Старі `.pio`, vendor Drivers/Middlewares і generated build trees не вважалися доказом дій користувача та не проходили повний аудит.

## R1-S3: стан, з якого продовжувати

| Вузол | Що підтверджено | Що лишилось |
|---|---|---|
| ESP32-S3 N32R16V | HWTEST запускався; Flash 33554432 bytes; PSRAM близько 16 MiB | Довгий memory/stability test |
| I2C GPIO8/9 | 0x3C/0x40/0x50/0x68 у повторних scan, 0 errors | Повна функціональна перевірка INA228 |
| SD SPI GPIO10–13 | 10 MHz, write/close/remount/exact readback PASS; обидва txt перевірено на ПК | Тривале логування, великі файли, fault recovery |
| OLED | SH1106G 128x64, 0x3C, поворот 180°, власник підтвердив читабельність | Майбутній UI |
| 24C32 | Власник повідомив EEP PASS: backup на SD, pattern verify, повне порівняння після restore | Постійний layout калібрування |
| DS3231 | Модель підтверджена; SET TIME за логікою v0.6 = хід є, OSF=1 | Одноразове встановлення часу, зона/UTC policy, battery retention |
| INA228 | Лише ACK на очікуваній адресі | ID, VBUS/VSHUNT/temp, ALERT, номінал шунта і калібрування |
| Upload | Були успішні записи; нестабільний вхід у bootloader | Встановити причину на рівні BOOT/EN/USB-UART/плати |

Фактичний прошитий profile не можна впевнено визначити лише за OLED: UI однаковий для USB/UART. Наявність SET TIME підтверджує роботу коду RTC, а не конкретні USB build flags.

Симптоми з розмови: ручний/автоматичний upload іноді вдається після підключення кабелю у певний момент; були No serial data, Wrong boot mode, окремо Access denied при зайнятому COM. USB-роз’єм не спричиняє видимої зміни в Device Manager. GPIO0 натиснутий = 0 V, відпущений змінювався приблизно 3.17–3.7 V; LDO за вимірюванням власника 3.35 V. Промивання/нагрівання передували тимчасовому поліпшенню, але причинний зв’язок не доведено.

## Наступна сесія

1. Не повторювати вже пройдені SD/OLED/EEPROM тести без потреби. EEPROM write-test наразі виконується при кожному boot — це тимчасовий bring-up код, не майбутня штатна поведінка.
2. На прохолодній платі, із тією самою GND-точкою, записати 3V3, EN, GPIO0 саме під час Connecting після ручного RESET із BOOT затиснутим.
3. Отримати фото обох боків плати, ділянки USB-UART, BOOT/RESET і пайки. EN, що утримується низьким, та GPIO0, який не низький на старті, ведуть до різних діагнозів.
4. Якщо рівні коректні, окремо перевірити ROM download log і UART-шляхи/вплив відкриття порту. Не вважати no_reset гарантією відсутності імпульсів драйвера.
5. Після стабілізації upload — встановити DS3231 за узгодженою часовою політикою; потім INA228 hardware test. eFuse не змінювати на підставі припущень.

## Межі огляду

Виконано карту всіх верхніх папок, читання ключової документації, цільовий аналіз авторського firmware, Git history і dirty diff Lily R3, порівняння дерев і огляд 66 ZIP без розпакування в старі проєкти. Це відновлення контексту, не повний построковий code review усіх vendor libraries, не повторення історичних hardware proofs і не перевірка кожного бінарного файла. Для KBD виконано огляд призначення та документації, без детального аудиту алгоритму.
