# ADS1115 Config Bit-Masking Guide

This project configures the ADS1115 via its 16-bit CONFIG register (0x01). The code uses explicit bit fields and shifts to build the register value in a clear, datasheet-aligned way.

## Config Register Layout (0x01)

```
Bit:  15   14 13 12   11 10  9    8   7  6  5    4    3    2    1    0
      OS   MUX(3)      PGA(3)      MODE  DR(3)  COMP_MODE POL  LAT  COMP_QUE(2)
```

- OS (bit 15): Start single conversion (single-shot mode). Not used in continuous mode.
- MUX (bits 14:12): Input channel selection (differential or single-ended). Example: `AIN0 vs GND = 0b100`.
- PGA (bits 11:9): Full-scale range. Common values: `±4.096V = 0b001`, `±2.048V = 0b010`.
- MODE (bit 8): `0 = continuous`, `1 = single-shot/power-down`.
- DR (bits 7:5): Data rate. `0b111 = 860 SPS`.
- Comparator (bits 4..0): Set `COMP_QUE = 0b11` to disable comparator; leave others at 0.

## Where It’s Done in Code

File: `firmware/src/drivers/adc_emg_driver.c`

- `ads1115_build_config(...)`: Packs the fields into a 16-bit `cfg` using shifts aligned to datasheet positions.
  - MUX → `((mux & 0x7) << 12)`
  - PGA → `((pga & 0x7) <<  9)`
  - MODE → `continuous ? 0 : (1 << 8)`
  - DR  → `((dr  & 0x7) <<  5)`
  - Comparator disable → `cfg |= 0b11` (COMP_QUE)
- `ads1115_init()`: Writes the config and immediately calls `ads1115_read_config()` to log readback.
- `ads1115_read_config(...)`: Performs a write+read to obtain the current CONFIG register.

## Example Derivation

Defaults used in this firmware:

- `MUX = 0b100` (AIN0 vs GND) → `0b100 << 12 = 0x4000`
- `PGA = 0b001` (±4.096 V)    → `0b001 <<  9 = 0x0200`
- `MODE = 0` (continuous)     → bit 8 remains 0
- `DR  = 0b111` (860 SPS)     → `0b111 <<  5 = 0x00E0`
- `COMP_QUE = 0b11`           → `0x0003`

Sum: `0x4000 + 0x0200 + 0x00E0 + 0x0003 = 0x41E3`

You should see this value (or your customized value) echoed as both written and readback in boot logs.

## Volts per Count (LSB) and PGA

- For `±4.096 V`: `LSB = 4.096 / 32768` volts.
- For `±2.048 V`: `LSB = 2.048 / 32768` volts.

If you change PGA, update `ads1115_scale_to_volts()` to use the matching LSB so voltage values remain correct.

## Switching Modes or Channels

- Single-shot: set `continuous_mode = false` when building config and pulse OS (bit 15) to start conversions.
- Channel: choose a different `ads1115_mux_t` (e.g., `ADS1115_MUX_AIN1_GND`).
- Data rate: choose another `ads1115_dr_t` (e.g., `ADS1115_DR_475`).
