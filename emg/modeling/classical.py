"""Classical ML models for EMG features.

Provides quick pipelines for common classifiers/regressors with scaling.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier


@dataclass
class ModelSpec:
    """Specification for model creation.

    kind: "svc" | "logreg" | "rf" | "ridge".
    """
    kind: str = "svc"  # svc|logreg|rf|ridge
    C: float = 1.0


def create_classifier(spec: ModelSpec) -> Pipeline:
    """Create a classification pipeline with standardization."""
    if spec.kind == "svc":
        clf = SVC(C=spec.C, probability=True)
    elif spec.kind == "logreg":
        clf = LogisticRegression(max_iter=200)
    elif spec.kind == "rf":
        clf = RandomForestClassifier(n_estimators=200)
    else:
        raise ValueError(f"Unknown classifier kind: {spec.kind}")
    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


def create_regressor() -> Pipeline:
    """Create a regression pipeline with standardization and Ridge."""
    return Pipeline([("scaler", StandardScaler()), ("reg", Ridge(alpha=1.0))])
