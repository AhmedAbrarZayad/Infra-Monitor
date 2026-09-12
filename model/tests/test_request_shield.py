import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from fastapi.testclient import TestClient

import app.main as main_module
from app.artifacts import ArtifactStore
from app.pipeline.request_shield import REQUEST_SHIELD_FEATURE_NAMES


def request_vectors(count=6):
    return [
        [float((row + column) % 5) for column in range(len(REQUEST_SHIELD_FEATURE_NAMES))]
        for row in range(count)
    ]


def install_artifact(root, *, metadata_overrides=None, labels=(0, 1, 2)):
    vectors = request_vectors(len(labels) * 2)
    targets = list(labels) * 2
    model = RandomForestClassifier(n_estimators=3, random_state=42).fit(
        np.asarray(vectors), np.asarray(targets)
    )
    artifact_dir = root / "request_shield"
    artifact_dir.mkdir(parents=True)
    import joblib

    joblib.dump(model, artifact_dir / "model.joblib")
    metadata = {
        "model_version": "request-shield-test",
        "artifact_format_version": 1,
        "feature_names": list(REQUEST_SHIELD_FEATURE_NAMES),
        "training_samples": len(vectors),
    }
    metadata.update(metadata_overrides or {})
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")


def configure_client(monkeypatch, tmp_path):
    main_module._request_shield_model = None
    main_module._request_shield_metadata = None
    monkeypatch.setattr(main_module, "artifacts", ArtifactStore(tmp_path))
    monkeypatch.setenv("ML_SERVICE_TOKEN", "secret")
    return TestClient(main_module.app), {"Authorization": "Bearer secret"}


def test_request_shield_ready_and_classifies_26_features(monkeypatch, tmp_path):
    install_artifact(tmp_path)
    client, headers = configure_client(monkeypatch, tmp_path)

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["model_version"] == "request-shield-test"

    response = client.post(
        "/classify-requests",
        json={"feature_names": list(REQUEST_SHIELD_FEATURE_NAMES), "vectors": request_vectors(2)},
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()["classifications"]) == 2
    assert response.json()["model_version"] == "request-shield-test"


def test_request_shield_rejects_wrong_schema_and_invalid_vectors(monkeypatch, tmp_path):
    install_artifact(tmp_path)
    client, headers = configure_client(monkeypatch, tmp_path)
    endpoint = "/classify-requests"

    wrong_schema = client.post(
        endpoint,
        json={"feature_names": ["cpu_r"], "vectors": [[1.0]]},
        headers=headers,
    )
    assert wrong_schema.status_code == 422

    short_vector = client.post(
        endpoint,
        json={
            "feature_names": list(REQUEST_SHIELD_FEATURE_NAMES),
            "vectors": [[1.0] * 25],
        },
        headers=headers,
    )
    assert short_vector.status_code == 422

    non_finite = client.post(
        endpoint,
        json={
            "feature_names": list(REQUEST_SHIELD_FEATURE_NAMES),
            "vectors": [[float("nan")] + [1.0] * 25],
        },
        headers=headers,
    )
    assert non_finite.status_code in (400, 422)


def test_request_shield_readiness_rejects_incompatible_artifact(monkeypatch, tmp_path):
    install_artifact(
        tmp_path,
        metadata_overrides={"feature_names": ["cpu_r"], "artifact_format_version": 1},
    )
    client, _ = configure_client(monkeypatch, tmp_path)

    assert client.get("/ready").status_code == 503


def test_request_shield_training_route_is_removed(monkeypatch, tmp_path):
    install_artifact(tmp_path)
    client, headers = configure_client(monkeypatch, tmp_path)

    response = client.post("/train-request-classifier", headers=headers, json={})
    assert response.status_code == 404
