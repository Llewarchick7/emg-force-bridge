"""Moved: use ml.train.train instead.

This module has been relocated to ml/train/train.py.
"""
from __future__ import annotations

from importlib import import_module

_mod = import_module("ml.train.train")

load_features_from_csv = _mod.load_features_from_csv
train_baseline_classifier = _mod.train_baseline_classifier
main = _mod.main