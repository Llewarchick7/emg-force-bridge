"""Moved: use ml.models.classical instead.

This module has been relocated to ml/models/classical.py.
"""
from __future__ import annotations

from importlib import import_module

_mod = import_module("ml.models.classical")

ModelSpec = _mod.ModelSpec
create_classifier = _mod.create_classifier
create_regressor = _mod.create_regressor
