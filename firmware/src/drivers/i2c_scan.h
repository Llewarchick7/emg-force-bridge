/*
i2c_scan.h
*/
#ifndef I2C_SCAN_H
#define I2C_SCAN_H

// Scan the I2C bus configured on I2C_NUM_0 and log with provided pin labels
void i2c_scan_bus(int sda_gpio, int scl_gpio);

#endif
