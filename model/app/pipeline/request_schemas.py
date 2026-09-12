"""Request threat classifier for the FastAPI ML service.

Loads a pre-trained Random Forest / XGBoost model from the artifact store
and classifies batches of HTTP request feature vectors into GREEN / GRAY / RED
threat zones.
"""

from __future__ import annotations

from pydantic import BaseModel

# Must stay in the same order as ``backend/sanitize/features.py``.  This is a
# separate schema from the infrastructure telemetry features in app.schemas.
REQUEST_FEATURE_NAMES = [
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
]


class ClassifyRequest(BaseModel):
    """Batch classification request."""

    feature_names: list[str]
    vectors: list[list[float]]


class ClassificationResult(BaseModel):
    """Single classification result."""

    zone: str  # GREEN, GRAY, RED
    confidence: float


class ClassifyResponse(BaseModel):
    """Batch classification response."""

    classifications: list[ClassificationResult]
    model_version: str


# ── Zone label mapping ──────────────────────────────────────────────

ZONE_LABELS = {0: "GREEN", 1: "GRAY", 2: "RED"}
LABEL_TO_ZONE = {
    "BENIGN": 0,
    "GREEN": 0,
    "GRAY": 1,
    "SUSPICIOUS": 1,
    "RED": 2,
    "MALICIOUS": 2,
}

# CICIDS2017 attack type → zone mapping
CICIDS_LABEL_MAP = {
    "BENIGN": 0,  # GREEN
    "FTP-Patator": 2,  # RED — brute force
    "SSH-Patator": 2,  # RED — brute force
    "DoS slowloris": 2,  # RED — DoS
    "DoS Slowhttptest": 2,  # RED — DoS
    "DoS Hulk": 2,  # RED — DoS
    "DoS GoldenEye": 2,  # RED — DoS
    "Heartbleed": 2,  # RED — critical vuln exploit
    "Web Attack \u2013 Brute Force": 2,  # RED
    "Web Attack \u2013 XSS": 2,  # RED — XSS
    "Web Attack \u2013 Sql Injection": 2,  # RED — SQLi
    "Infiltration": 2,  # RED
    "Bot": 1,  # GRAY — automated but not always malicious
    "PortScan": 1,  # GRAY — reconnaissance
    "DDoS": 2,  # RED — distributed denial of service
}
