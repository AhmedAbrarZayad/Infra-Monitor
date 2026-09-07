"""Request threat classifier for the FastAPI ML service.

Loads a pre-trained Random Forest / XGBoost model from the artifact store
and classifies batches of HTTP request feature vectors into GREEN / GRAY / RED
threat zones.
"""

from __future__ import annotations

from pydantic import BaseModel


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
LABEL_TO_ZONE = {"BENIGN": 0, "GREEN": 0, "GRAY": 1, "SUSPICIOUS": 1, "RED": 2, "MALICIOUS": 2}

# CICIDS2017 attack type → zone mapping
CICIDS_LABEL_MAP = {
    "BENIGN": 0,                        # GREEN
    "FTP-Patator": 2,                   # RED — brute force
    "SSH-Patator": 2,                   # RED — brute force
    "DoS slowloris": 2,                 # RED — DoS
    "DoS Slowhttptest": 2,             # RED — DoS
    "DoS Hulk": 2,                      # RED — DoS
    "DoS GoldenEye": 2,                # RED — DoS
    "Heartbleed": 2,                    # RED — critical vuln exploit
    "Web Attack \u2013 Brute Force": 2,       # RED
    "Web Attack \u2013 XSS": 2,              # RED — XSS
    "Web Attack \u2013 Sql Injection": 2,    # RED — SQLi
    "Infiltration": 2,                  # RED
    "Bot": 1,                           # GRAY — automated but not always malicious
    "PortScan": 1,                      # GRAY — reconnaissance
    "DDoS": 2,                          # RED — distributed denial of service
}
