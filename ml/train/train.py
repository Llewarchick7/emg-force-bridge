"""Training utilities for EMG classification models.

Moved from emg/modeling/train.py.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib


def load_features_from_csv(path: str | Path):
    """Load features and labels from CSV file.
    Args:
        path: Path to CSV with feature columns and a 'label' column.
    Returns:
        (X, y) where X is features array and y is labels array.
    """
    df = pd.read_csv(path)
    if 'label' not in df.columns:
        raise ValueError("CSV must contain 'label' column.")
    X = df[[c for c in df.columns if c != 'label']].values
    y = df['label'].values
    return X, y


def train_baseline_classifier(csv_path: str | Path, model_out: str | Path = 'models/baseline_svm.joblib', test_size: float = 0.2, random_state: int = 42):
    """Train a baseline SVM classifier from feature CSV."""
    X, y = load_features_from_csv(csv_path)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    clf = SVC(kernel='rbf', probability=True)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print(f"Accuracy: {acc:.3f}")
    print("Confusion matrix:")
    print(confusion_matrix(y_test, preds))

    # Save model
    Path(model_out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_out)

    return clf


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train EMG classification models")
    parser.add_argument('--csv', required=True, help="Path to feature CSV file")
    parser.add_argument('--out', default='models/baseline_svm.joblib', help="Output model path")
    parser.add_argument('--test-size', type=float, default=0.2, help="Test split fraction")
    args = parser.parse_args()

    train_baseline_classifier(args.csv, model_out=args.out, test_size=args.test_size)


if __name__ == "__main__":
    main()
