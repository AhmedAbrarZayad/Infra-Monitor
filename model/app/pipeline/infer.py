import numpy as np


def infer_window(model, matrix):
    scores = model.decision_function(matrix)
    predictions = model.predict(matrix)
    evidence_index = int(np.argmin(scores))
    anomaly_score = float(scores[evidence_index])
    return {
        "evidence_index": evidence_index,
        "is_anomaly": bool((predictions == -1).any()),
        "anomaly_score": anomaly_score,
        "confidence_score": min(1.0, abs(anomaly_score)),
    }
