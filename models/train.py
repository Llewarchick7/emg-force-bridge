import os
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib

def load_features_from_csv(path):
    df = pd.read_csv(path)
    if 'label' not in df.columns:
        raise ValueError("CSV must contain 'label' column.")
    X = df[[c for c in df.columns if c != 'label']].values
    y = df['label'].values
    return X, y

def train_baseline(csv_path, model_out='models/baseline_svm.joblib'):
    X, y = load_features_from_csv(csv_path)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = SVC(kernel='rbf', probability=True)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print("Accuracy:", acc)
    print("Confusion matrix:\\n", confusion_matrix(y_test, preds))
    os.makedirs(os.path.dirname(model_out), exist_ok=True)
    joblib.dump(clf, model_out)
    return clf

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--out', default='models/baseline_svm.joblib')
    args = parser.parse_args()
    train_baseline(args.csv, model_out=args.out)