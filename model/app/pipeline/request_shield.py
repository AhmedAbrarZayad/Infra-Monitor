"""Request Shield model schema and artifact validation."""

from __future__ import annotations

import math

REQUEST_SHIELD_FEATURE_NAMES = (
    "method_encoded",
    "path_depth",
    "path_length",
    "path_has_traversal",
    "path_has_suspicious_ext",
    "query_param_count",
    "query_length",
    "query_has_sql_injection",
    "query_has_xss",
    "query_has_cmd_injection",
    "path_has_sql_injection",
    "path_has_xss",
    "ua_is_known_browser",
    "ua_is_bot",
    "ua_is_empty",
    "ua_length",
    "content_length_log",
    "has_content_length",
    "status_code_class",
    "response_time_log",
    "has_referer",
    "protocol_version",
    "header_count",
    "has_special_chars_in_path",
    "path_entropy",
    "query_entropy",
)
REQUEST_SHIELD_ARTIFACT_FORMAT_VERSION = 1
REQUEST_SHIELD_LABELS = {0, 1, 2}
REQUEST_SHIELD_MAX_BATCH_SIZE = 500


def validate_vectors(vectors: list[list[float]]) -> None:
    if len(vectors) > REQUEST_SHIELD_MAX_BATCH_SIZE:
        raise ValueError(
            f"Request Shield batches cannot exceed {REQUEST_SHIELD_MAX_BATCH_SIZE} vectors."
        )
    for vector in vectors:
        if len(vector) != len(REQUEST_SHIELD_FEATURE_NAMES):
            raise ValueError("Every vector must match the Request Shield feature schema.")
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("Request Shield feature values must be finite numbers.")


def validate_artifact(model, metadata: dict) -> None:
    if metadata.get("artifact_format_version") != REQUEST_SHIELD_ARTIFACT_FORMAT_VERSION:
        raise ValueError("Request Shield artifact format is unsupported.")
    if tuple(metadata.get("feature_names", ())) != REQUEST_SHIELD_FEATURE_NAMES:
        raise ValueError("Request Shield artifact uses an incompatible feature schema.")
    if not metadata.get("model_version"):
        raise ValueError("Request Shield model version is missing.")
    if not isinstance(metadata.get("training_samples"), int) or metadata["training_samples"] < 1:
        raise ValueError("Request Shield training sample metadata is invalid.")
    classes = getattr(model, "classes_", ())
    if set(int(label) for label in classes) != REQUEST_SHIELD_LABELS:
        raise ValueError("Request Shield artifact does not contain all threat zones.")
