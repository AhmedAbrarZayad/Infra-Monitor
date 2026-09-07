"""Train the Request Shield classifier from preprocessed CICIDS2017 data.

Loads the processed .npz file and sends it to the FastAPI ML service's
/train-request-classifier endpoint.

Usage:
    python -m sanitize.dataset.train

Prerequisites:
    1. Run `python -m sanitize.dataset.preprocess` first
    2. The FastAPI ML service must be running
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import httpx
import numpy as np

logger = logging.getLogger(__name__)


def train_from_processed(
    data_path: str | Path,
    ml_service_url: str = "",
    ml_service_token: str = "",
    n_estimators: int = 200,
    max_depth: int = 20,
):
    """Load processed data and send to the ML service for training."""
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

    if not ml_service_url:
        ml_service_url = os.getenv("ML_SERVICE_URL", "http://localhost:7001")
    if not ml_service_token:
        ml_service_token = os.getenv("ML_SERVICE_TOKEN", "")

    ml_service_url = ml_service_url.rstrip("/")

    payload = {
        "feature_names": feature_names,
        "vectors": X.tolist(),
        "labels": y.tolist(),
        "n_estimators": n_estimators,
        "max_depth": max_depth,
    }

    logger.info(
        "Sending %d training samples to %s/train-request-classifier ...",
        len(X),
        ml_service_url,
    )

    try:
        response = httpx.post(
            f"{ml_service_url}/train-request-classifier",
            json=payload,
            headers={"Authorization": f"Bearer {ml_service_token}"},
            timeout=300,  # Training can take a while
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Training complete: %s", json.dumps(result, indent=2))
    except httpx.HTTPStatusError as exc:
        logger.error(
            "ML service returned %d: %s",
            exc.response.status_code,
            exc.response.text,
        )
        sys.exit(1)
    except httpx.HTTPError as exc:
        logger.error("Failed to connect to ML service: %s", exc)
        sys.exit(1)


def __main__():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    base = Path(__file__).resolve().parent
    data_path = base / "processed" / "training_data.npz"
    train_from_processed(data_path)


if __name__ == "__main__":
    __main__()
