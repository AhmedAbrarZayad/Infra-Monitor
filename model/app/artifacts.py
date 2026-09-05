import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import joblib

from app.schemas import FEATURE_NAMES


class ModelNotFoundError(FileNotFoundError):
    pass


class ArtifactStore:
    def __init__(self, root=None):
        self.root = Path(root or os.getenv("ML_ARTIFACT_DIR", "artifacts"))
        self._locks_guard = threading.Lock()
        self._locks = {}

    def _lock(self, service_id):
        key = str(service_id)
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _directory(self, service_id):
        return self.root / str(service_id)

    def save(self, service_id, model, *, contamination):
        with self._lock(service_id):
            directory = self._directory(service_id)
            directory.mkdir(parents=True, exist_ok=True)
            model_version = uuid4().hex
            metadata = {
                "model_version": model_version,
                "feature_names": list(FEATURE_NAMES),
                "trained_at": datetime.now(UTC).isoformat(),
                "contamination": contamination,
                "random_state": 42,
            }
            model_temp = directory / f"model.{model_version}.tmp"
            metadata_temp = directory / f"metadata.{model_version}.tmp"
            joblib.dump(model, model_temp)
            metadata_temp.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            os.replace(model_temp, directory / "model.joblib")
            os.replace(metadata_temp, directory / "metadata.json")
            return metadata

    def load(self, service_id):
        directory = self._directory(service_id)
        model_path = directory / "model.joblib"
        metadata_path = directory / "metadata.json"
        with self._lock(service_id):
            if not model_path.is_file() or not metadata_path.is_file():
                raise ModelNotFoundError(str(service_id))
            model = joblib.load(model_path)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if tuple(metadata.get("feature_names", ())) != FEATURE_NAMES:
            raise ValueError("Stored model uses an incompatible feature schema.")
        return model, metadata
