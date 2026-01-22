"""Deprecated: The streaming pipeline module has been removed from the runtime.

This module is no longer part of the production pipeline. If you relied on it,
consider implementing streaming directly in firmware or backend services.
"""
raise ImportError("emg.realtime.pipeline is deprecated and has been removed from the pipeline.")
