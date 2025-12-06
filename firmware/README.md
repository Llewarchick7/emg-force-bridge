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
  - idf.py -p COM3 flash monitor

