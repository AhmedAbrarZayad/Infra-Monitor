import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import joblib
from fastapi import Depends, FastAPI, HTTPException, status

from app.artifacts import ArtifactStore, ModelNotFoundError
from app.pipeline.infer import infer_window
from app.pipeline.request_classifier import classify_requests, train_request_classifier
from app.pipeline.request_schemas import ClassifyRequest, ClassifyResponse, ZONE_LABELS
from app.pipeline.train import train_model
from app.schemas import FEATURE_NAMES, InferRequest, TrainRequest
from app.security import require_ml_token

app = FastAPI(title="Infra Monitor ML Service", version="1.0.0")
artifacts = ArtifactStore()


def matrix(rows):
    return [[row.values[feature] for feature in FEATURE_NAMES] for row in rows]


@app.get("/health")
def health():
    if not os.getenv("ML_SERVICE_TOKEN", ""):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service token is not configured.",
        )
    try:
        artifacts.root.mkdir(parents=True, exist_ok=True)
        if not os.access(artifacts.root, os.W_OK):
            raise OSError("Artifact directory is not writable.")
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Artifact storage is unavailable.",
        ) from exc
    return {"status": "ok", "artifact_storage": "ok"}


@app.post("/train", dependencies=[Depends(require_ml_token)])
def train(request: TrainRequest):
    model = train_model(matrix(request.rows), contamination=request.contamination)
    metadata = artifacts.save(
        request.service_id,
        model,
        contamination=request.contamination,
    )
    return {
        "status": "trained",
        "service_id": request.service_id,
        "model_version": metadata["model_version"],
    }


@app.post("/infer", dependencies=[Depends(require_ml_token)])
def infer(request: InferRequest):
    try:
        model, metadata = artifacts.load(request.service_id)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "model_not_found",
                "message": "No model exists for service.",
            },
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored model artifact is invalid or incompatible.",
        ) from exc

    result = infer_window(model, matrix(request.rows))
    evidence = request.rows[result.pop("evidence_index")]
    payload = {
        "organization_id": str(request.organization_id),
        "server_id": str(request.server_id),
        "service_id": str(request.service_id),
        **result,
        "feature_values": evidence.values,
        "window_started_at": request.window_started_at.isoformat(),
        "window_ended_at": request.window_ended_at.isoformat(),
        "model_version": metadata["model_version"],
    }
    django_url = os.getenv("DJANGO_INTERNAL_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("ML_SERVICE_TOKEN", "")
    try:
        response = httpx.post(
            f"{django_url}/api/internal/ml/detections/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=float(os.getenv("DJANGO_CALLBACK_TIMEOUT_SECONDS", "10")),
        )
        response.raise_for_status()
        detection = response.json()
        detection_id = detection["id"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Django rejected or did not store the detection.",
        ) from exc

    return {
        "status": "completed",
        "service_id": request.service_id,
        "model_version": metadata["model_version"],
        "detection_id": detection_id,
        **result,
    }


# ── Request Shield endpoints ────────────────────────────────────────

_request_shield_model = None
_request_shield_metadata = None


def _load_request_shield_model():
    """Load the request shield model from the artifact store (lazy singleton)."""
    global _request_shield_model, _request_shield_metadata
    if _request_shield_model is not None:
        return _request_shield_model, _request_shield_metadata
    model_dir = artifacts.root / "request_shield"
    model_path = model_dir / "model.joblib"
    metadata_path = model_dir / "metadata.json"
    if not model_path.is_file():
        raise ModelNotFoundError("request_shield")
    _request_shield_model = joblib.load(model_path)
    if metadata_path.is_file():
        _request_shield_metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
    else:
        _request_shield_metadata = {"model_version": "unknown"}
    return _request_shield_model, _request_shield_metadata


@app.post("/classify-requests", dependencies=[Depends(require_ml_token)])
def classify_request_batch(request: ClassifyRequest):
    """Classify a batch of HTTP request feature vectors into threat zones."""
    try:
        model, metadata = _load_request_shield_model()
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "request_shield_model_not_found",
                "message": "No trained request shield model found. Run /train-request-classifier first.",
            },
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The stored request shield model is invalid or incompatible.",
        ) from exc

    results = classify_requests(model, request.vectors)
    return ClassifyResponse(
        classifications=results,
        model_version=metadata.get("model_version", "unknown"),
    )


class TrainRequestClassifierRequest(ClassifyRequest):
    """Training request — vectors + labels."""
    labels: list[int]  # 0=GREEN, 1=GRAY, 2=RED
    n_estimators: int = 200
    max_depth: int = 20


@app.post("/train-request-classifier", dependencies=[Depends(require_ml_token)])
def train_request_classifier_endpoint(request: TrainRequestClassifierRequest):
    """Train the request shield classifier from labeled feature vectors."""
    global _request_shield_model, _request_shield_metadata

    if len(request.vectors) != len(request.labels):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vectors and labels must have the same length.",
        )
    if len(request.vectors) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 10 training samples are required.",
        )

    model = train_request_classifier(
        request.vectors,
        request.labels,
        n_estimators=request.n_estimators,
        max_depth=request.max_depth,
    )

    # Save artifact
    model_dir = artifacts.root / "request_shield"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_version = uuid4().hex
    metadata = {
        "model_version": model_version,
        "feature_names": request.feature_names,
        "trained_at": datetime.now(UTC).isoformat(),
        "n_estimators": request.n_estimators,
        "max_depth": request.max_depth,
        "training_samples": len(request.vectors),
    }
    joblib.dump(model, model_dir / "model.joblib")
    (model_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    # Clear cached model so next classify loads the new one
    _request_shield_model = None
    _request_shield_metadata = None

    return {
        "status": "trained",
        "model_version": model_version,
        "training_samples": len(request.vectors),
    }
