from datetime import UTC, datetime, timedelta
from uuid import uuid4

import app.main as main_module
from app.artifacts import ArtifactStore
from app.schemas import FEATURE_NAMES
from fastapi.testclient import TestClient


class CallbackResponse:
    status_code = 201

    def raise_for_status(self):
        return None

    def json(self):
        return {"id": str(uuid4())}


def rows(count=4):
    start = datetime(2026, 9, 5, 10, 0, tzinfo=UTC)
    return [
        {
            "timestamp": (start + timedelta(minutes=index)).isoformat(),
            "values": {
                feature: float(index + feature_index + 1)
                for feature_index, feature in enumerate(FEATURE_NAMES)
            },
        }
        for index in range(count)
    ]


def train_payload(service_id):
    return {
        "service_id": str(service_id),
        "feature_names": list(FEATURE_NAMES),
        "rows": rows(),
        "contamination": 0.25,
    }


def infer_payload(service_id):
    samples = rows()
    return {
        "organization_id": str(uuid4()),
        "server_id": str(uuid4()),
        "service_id": str(service_id),
        "window_started_at": samples[0]["timestamp"],
        "window_ended_at": (
            datetime.fromisoformat(samples[-1]["timestamp"]) + timedelta(minutes=1)
        ).isoformat(),
        "rows": samples,
    }


def test_health_and_authorization(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "artifacts", ArtifactStore(tmp_path))
    monkeypatch.setenv("ML_SERVICE_TOKEN", "secret")
    client = TestClient(main_module.app)

    assert client.get("/health").status_code == 200
    assert client.post("/train", json=train_payload(uuid4())).status_code == 401
    response = client.post(
        "/train",
        json=train_payload(uuid4()),
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_train_persists_and_infer_posts_detection(monkeypatch, tmp_path):
    service_id = uuid4()
    monkeypatch.setattr(main_module, "artifacts", ArtifactStore(tmp_path))
    monkeypatch.setenv("ML_SERVICE_TOKEN", "secret")
    callback_calls = []

    def callback(url, **kwargs):
        callback_calls.append((url, kwargs))
        return CallbackResponse()

    monkeypatch.setattr(main_module.httpx, "post", callback)
    client = TestClient(main_module.app)
    headers = {"Authorization": "Bearer secret"}

    trained = client.post("/train", json=train_payload(service_id), headers=headers)
    assert trained.status_code == 200
    assert (tmp_path / str(service_id) / "model.joblib").is_file()
    assert (tmp_path / str(service_id) / "metadata.json").is_file()

    inferred = client.post("/infer", json=infer_payload(service_id), headers=headers)
    assert inferred.status_code == 200
    assert inferred.json()["model_version"] == trained.json()["model_version"]
    assert isinstance(inferred.json()["is_anomaly"], bool)
    assert callback_calls[0][0].endswith("/api/internal/ml/detections/")
    assert callback_calls[0][1]["headers"] == {"Authorization": "Bearer secret"}
    assert tuple(callback_calls[0][1]["json"]["feature_values"]) == FEATURE_NAMES


def test_missing_model_and_invalid_feature_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "artifacts", ArtifactStore(tmp_path))
    monkeypatch.setenv("ML_SERVICE_TOKEN", "secret")
    client = TestClient(main_module.app)
    headers = {"Authorization": "Bearer secret"}

    missing = client.post("/infer", json=infer_payload(uuid4()), headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "model_not_found"

    payload = train_payload(uuid4())
    payload["feature_names"] = list(reversed(payload["feature_names"]))
    assert client.post("/train", json=payload, headers=headers).status_code == 422


def test_django_callback_failure_fails_inference(monkeypatch, tmp_path):
    service_id = uuid4()
    monkeypatch.setattr(main_module, "artifacts", ArtifactStore(tmp_path))
    monkeypatch.setenv("ML_SERVICE_TOKEN", "secret")
    client = TestClient(main_module.app)
    headers = {"Authorization": "Bearer secret"}
    assert (
        client.post(
            "/train", json=train_payload(service_id), headers=headers
        ).status_code
        == 200
    )

    def callback_failure(*args, **kwargs):
        raise main_module.httpx.ConnectError("failed")

    monkeypatch.setattr(main_module.httpx, "post", callback_failure)
    response = client.post("/infer", json=infer_payload(service_id), headers=headers)
    assert response.status_code == 502
