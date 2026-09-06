# Прошивка HWTEST v0.6

PlatformIO + Arduino, ESP32-S3 N32R16V. Працювати з кореня репозиторію, не з цієї папки. Актуальні команди та профілі: [README](../README.md).

- `src/main.cpp`: пам’ять, повторний I²C scan, SD-тест, OLED SH1106 128×64 із поворотом 180°.
- `src/eeprom_test.cpp`: backup 24C32 на SD, вибірковий запис, відновлення та повне порівняння.
- `src/rtc_test.cpp`: DS3231 read-only, календар/BCD, температура, OSF/EOSC, перевірка приросту часу.
- `include/pins.h`: GPIO, узгоджені з hardware/pinmap.md.

SD-тест зберігає контрольний рядок v0.2; новий файл створюється при кожному boot. RTC не змінює час. EEPROM write-test є тимчасовим діагностичним кроком; не вимикати живлення до завершення restore.

Основний профіль: esp32-s3-uart-manual. UART/USB експериментальні варіанти збережені в platformio.ini. Збірки v0.6 проходили; надійність входу у bootloader ще не підтверджено. Докладні результати: [bring-up](../docs/bring-up.md).
