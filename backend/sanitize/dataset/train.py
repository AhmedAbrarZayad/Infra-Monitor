"""Build an offline Request Shield inference artifact from preprocessed data.

The production ML service only loads the resulting joblib artifact; it never
trains or accepts training data over HTTP.

Usage:
    python -m sanitize.dataset.train

Prerequisites:
    1. Run `python -m sanitize.dataset.preprocess` first
    2. Install the model service's Python dependencies
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)


def train_from_processed(
    data_path: str | Path,
    output_dir: str | Path = "",
    n_estimators: int = 200,
    max_depth: int = 20,
):
    """Load processed data and write the model and metadata bundle."""
    data_path = Path(data_path)
    if not data_path.is_file():
        logger.error(
            "Processed data not found at %s. Run preprocessing first:\n"
            "  python -m sanitize.dataset.preprocess",
            data_path,
        )
        sys.exit(1)

    data = np.load(data_path, allow_pickle=True)
    X = data["X"]
    y = data["y"]
    feature_names = list(data["feature_names"])

    logger.info("Loaded training data: X=%s, y=%s", X.shape, y.shape)
    logger.info(
        "Class distribution: GREEN=%d, GRAY=%d, RED=%d",
        (y == 0).sum(),
        (y == 1).sum(),
        (y == 2).sum(),
    )

    output_dir = Path(
        output_dir or os.getenv(
            "REQUEST_SHIELD_ARTIFACT_DIR", "model/artifacts/request_shield"
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X.astype(np.float64), y.astype(np.int32))
    metadata = {
        "model_version": os.getenv("REQUEST_SHIELD_MODEL_VERSION", "offline-baseline"),
        "feature_names": feature_names,
        "artifact_format_version": 1,
        "training_samples": int(len(X)),
        "n_estimators": n_estimators,
        "max_depth": max_depth,
    }
    joblib.dump(model, output_dir / "model.joblib")
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    logger.info("Wrote Request Shield artifact to %s", output_dir)


def __main__():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    base = Path(__file__).resolve().parent
    data_path = base / "processed" / "training_data.npz"
    train_from_processed(data_path)


if __name__ == "__main__":
    __main__()
