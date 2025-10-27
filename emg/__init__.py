"""EMG processing pipeline package.

Modules are organized by pipeline stages:
- acquisition: device/file/serial input
- preprocessing: filters, rectify, envelope, calibration
- features: time and frequency domain
- artifacts: artifact detection
- modeling: models and IO
- evaluation: metrics and cross-validation helpers
- realtime: streaming pipeline stages
- io: logging/sinks
- utils: small helpers
"""
