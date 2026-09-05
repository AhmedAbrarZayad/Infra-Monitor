import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, status

from app.artifacts import ArtifactStore, ModelNotFoundError
from app.pipeline.infer import infer_window
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
