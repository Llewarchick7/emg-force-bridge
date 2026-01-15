# Firmware (ESP32-IDF)

This folder contains the ESP32-S3 firmware built with ESP-IDF.

Directories
- src/: Application sources (tasks, drivers, services)
- components/: Optional reusable ESP-IDF components

Build & Flash
- Install ESP-IDF v5+ per Espressif docs.
- Set IDF_PATH and add tools to PATH.
- From this folder, run:
  - idf.py set-target esp32s3
  - idf.py build
  - idf.py -p COM6 flash monitor

Troubleshooting (Download/Flashing Mode)
- Ensure the board enumerates as "USB JTAG/Serial" on Windows (e.g., COM6). Use Device Manager to confirm the port.
- If you see errors like "Failed to connect" or mention of downloader state/mode:
  1) Press and hold BOOT (IO0), then press EN (RESET), release EN, and release BOOT to force USB download mode.
  2) Try a lower baud rate or let `idf.py` pick defaults: `idf.py -p COM6 flash`.
  3) Use the native USB port on ESP32-S3; avoid external UART bridges unless required.
  4) Swap the USB cable/port (use a data-capable cable; avoid unpowered hubs).
- Direct esptool fallback (from this folder after `idf.py build`):
  esptool.py -p COM6 --chip esp32s3 --before default_reset --after hard_reset \
    write_flash --flash_mode dio --flash_size 2MB --flash_freq 80m \
    0x0 build/bootloader/bootloader.bin \
    0x8000 build/partition_table/partition-table.bin \
    0x10000 build/emg_force_bridge.bin

Notes
- Project target is ESP32-S3 (`sdkconfig` sets CONFIG_IDF_TARGET="esp32s3").
- Console is configured for USB Serial JTAG; monitor baud is 115200.

