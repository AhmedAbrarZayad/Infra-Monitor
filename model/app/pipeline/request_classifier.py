"""Request classifier — training and inference pipeline.

Trains a Random Forest (or XGBoost) multi-class classifier on HTTP request
feature vectors labeled as GREEN (0), GRAY (1), or RED (2).

Training data is derived from the CICIDS2017 dataset preprocessed into our
26-feature format, or from admin-labeled production request logs.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def train_request_classifier(
    X: list[list[float]],
    y: list[int],
    *,
    n_estimators: int = 200,
    max_depth: int = 20,
    class_weight: str = "balanced",
):
    """Train a Random Forest classifier for request zone classification.

    Args:
        X: Feature matrix — each row is a 26-dim feature vector.
        y: Labels — 0 (GREEN), 1 (GRAY), 2 (RED).
        n_estimators: Number of trees.
        max_depth: Maximum tree depth.
        class_weight: Strategy for class imbalance ('balanced' recommended).

    Returns:
        A fitted sklearn RandomForestClassifier.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score

    X_arr = np.array(X, dtype=np.float64)
    y_arr = np.array(y, dtype=np.int32)

    # Replace NaN / Inf with 0 (defensive)
    X_arr = np.nan_to_num(X_arr, nan=0.0, posinf=0.0, neginf=0.0)

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight=class_weight,
        random_state=42,
        n_jobs=-1,
    )

    # Quick cross-validation for logging
    scores = cross_val_score(clf, X_arr, y_arr, cv=min(5, len(set(y_arr))), scoring="f1_macro")
    logger.info(
        "Cross-val F1 (macro): mean=%.4f std=%.4f", scores.mean(), scores.std()
    )

    clf.fit(X_arr, y_arr)
    return clf


def classify_requests(model, vectors: list[list[float]]) -> list[dict]:
    """Classify a batch of feature vectors using a trained model.

    Returns a list of {"zone": str, "confidence": float} dicts.
    """
    from app.pipeline.request_schemas import ZONE_LABELS

    X = np.array(vectors, dtype=np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)

    results = []
    for i, pred in enumerate(predictions):
        zone = ZONE_LABELS.get(int(pred), "UNCLASSIFIED")
        confidence = float(probabilities[i].max())
        results.append({"zone": zone, "confidence": round(confidence, 4)})

    return results
