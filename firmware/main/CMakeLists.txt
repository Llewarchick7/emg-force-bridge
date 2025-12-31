# This CMakeLists.txt defines the "main" ESP-IDF component for the app.
#
# What it does:
# - Lists the source files that belong to the application component (SRCS).
# - Adds the include search paths for headers in this component (INCLUDE_DIRS).
# - Declares dependencies on other ESP-IDF components (REQUIRES), which
#   automatically adds their include paths, compile options, and libraries.
#
# Why it matters:
# - ESP-IDF's build system discovers the "main" component in this folder and
#   compiles anything listed in SRCS.
# - Declaring REQUIRES (e.g., "driver", "esp_timer") is how headers like
#   <driver/i2c.h> and <esp_timer.h> become resolvable during compilation.

idf_component_register(
    SRCS
        ../src/main.c
        ../src/drivers/adc_emg_driver.c
        ../src/drivers/i2c_scan.c
        ../src/drivers/gpio_test.c
        ../src/drivers/uart_transport.c
        ../src/tasks/task_acq.c
        ../src/tasks/task_stream.c
        ../src/tasks/task_proc.c
        ../src/services/ble_emg.c
    INCLUDE_DIRS
        ../src
    REQUIRES
        driver
        esp_timer
        bt
        nvs_flash
)
