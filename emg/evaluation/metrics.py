"""Evaluation metrics for EMG models."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error


def classification_metrics(y_true, y_pred) -> dict:
    """Compute accuracy and weighted F1."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, average="weighted")),
    }


def regression_metrics(y_true, y_pred) -> dict:
    """Compute MAE and RMSE."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }
