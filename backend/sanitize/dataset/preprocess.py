"""CICIDS2017 dataset preprocessor.

Converts raw CICIDS2017 CSV files into our 26-feature request classification
format. The CICIDS2017 dataset has 78 network flow features. We map a subset
of these to our HTTP-request-level features and synthesize the rest from the
network-level data.

Usage:
    python -m sanitize.dataset.preprocess

Input:  sanitize/dataset/raw/*.csv  (CICIDS2017 CSVs)
Output: sanitize/dataset/processed/training_data.npz
"""

from __future__ import annotations

import logging
import math
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ── CICIDS2017 label → zone mapping ────────────────────────────────

LABEL_TO_ZONE = {
    "BENIGN": 0,                          # GREEN
    "FTP-Patator": 2,                     # RED
    "SSH-Patator": 2,                     # RED
    "DoS slowloris": 2,                   # RED
    "DoS Slowhttptest": 2,               # RED
    "DoS Hulk": 2,                        # RED
    "DoS GoldenEye": 2,                  # RED
    "Heartbleed": 2,                      # RED
    "Web Attack \u2013 Brute Force": 2,         # RED
    "Web Attack \u2013 XSS": 2,                # RED
    "Web Attack \u2013 Sql Injection": 2,      # RED
    "Infiltration": 2,                    # RED
    "Bot": 1,                             # GRAY
    "PortScan": 1,                        # GRAY
    "DDoS": 2,                            # RED
}

# ── CICIDS2017 column names we use ──────────────────────────────────

# These are the actual column names in the CICIDS2017 CSV files.
# Many have a leading space because of how CICFlowMeter exports them.
CICIDS_COLUMNS = {
    "protocol": " Protocol",
    "flow_duration": " Flow Duration",
    "total_fwd_packets": " Total Fwd Packets",
    "total_bwd_packets": " Total Backward Packets",
    "fwd_packet_length_mean": " Fwd Packet Length Mean",
    "bwd_packet_length_mean": " Bwd Packet Length Mean",
    "flow_bytes_per_sec": "Flow Bytes/s",
    "flow_packets_per_sec": " Flow Packets/s",
    "fwd_iat_mean": " Fwd IAT Mean",
    "bwd_iat_mean": " Bwd IAT Mean",
    "fwd_psh_flags": " Fwd PSH Flags",
    "bwd_psh_flags": " Bwd PSH Flags",
    "fwd_urg_flags": " Fwd URG Flags",
    "bwd_urg_flags": " Bwd URG Flags",
    "fin_flag_count": " FIN Flag Count",
    "syn_flag_count": " SYN Flag Count",
    "rst_flag_count": " RST Flag Count",
    "ack_flag_count": " ACK Flag Count",
    "down_up_ratio": " Down/Up Ratio",
    "avg_packet_size": " Average Packet Size",
    "fwd_header_length": " Fwd Header Length",
    "bwd_header_length": " Bwd Header Length",
    "subflow_fwd_packets": " Subflow Fwd Packets",
    "subflow_bwd_packets": " Subflow Bwd Packets",
    "init_win_bytes_forward": " Init_Win_bytes_forward",
    "init_win_bytes_backward": " Init_Win_bytes_backward",
    "min_packet_length": " Min Packet Length",
    "max_packet_length": " Max Packet Length",
    "destination_port": " Destination Port",
    "label": " Label",
}


def _safe_float(value, default=0.0):
    """Convert a value to float, handling inf/nan/empty strings."""
    try:
        f = float(value)
        if math.isinf(f) or math.isnan(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _entropy(values):
    """Shannon entropy of a list of values."""
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum(
        (c / total) * math.log2(c / total) for c in counts.values() if c > 0
    )


def cicids_row_to_features(row: dict) -> list[float]:
    """Map a single CICIDS2017 CSV row to our 26-feature vector.

    Since CICIDS2017 is network-flow data (not HTTP access logs), we
    synthesize HTTP-like features from the network characteristics:

    - Destination port → simulates path depth / method hints
    - Packet counts → simulates header count, content length
    - Flow rates → simulates request rate
    - Flag patterns → simulates protocol behavior
    - Packet sizes → simulates content length and response time
    """
    dest_port = _safe_float(row.get(CICIDS_COLUMNS["destination_port"], 0))
    protocol = _safe_float(row.get(CICIDS_COLUMNS["protocol"], 0))
    flow_duration = _safe_float(row.get(CICIDS_COLUMNS["flow_duration"], 0))
    total_fwd = _safe_float(row.get(CICIDS_COLUMNS["total_fwd_packets"], 0))
    total_bwd = _safe_float(row.get(CICIDS_COLUMNS["total_bwd_packets"], 0))
    fwd_pkt_mean = _safe_float(row.get(CICIDS_COLUMNS["fwd_packet_length_mean"], 0))
    bwd_pkt_mean = _safe_float(row.get(CICIDS_COLUMNS["bwd_packet_length_mean"], 0))
    flow_bps = _safe_float(row.get(CICIDS_COLUMNS["flow_bytes_per_sec"], 0))
    flow_pps = _safe_float(row.get(CICIDS_COLUMNS["flow_packets_per_sec"], 0))
    fwd_iat = _safe_float(row.get(CICIDS_COLUMNS["fwd_iat_mean"], 0))
    syn_count = _safe_float(row.get(CICIDS_COLUMNS["syn_flag_count"], 0))
    rst_count = _safe_float(row.get(CICIDS_COLUMNS["rst_flag_count"], 0))
    ack_count = _safe_float(row.get(CICIDS_COLUMNS["ack_flag_count"], 0))
    fin_count = _safe_float(row.get(CICIDS_COLUMNS["fin_flag_count"], 0))
    avg_pkt_size = _safe_float(row.get(CICIDS_COLUMNS["avg_packet_size"], 0))
    fwd_header = _safe_float(row.get(CICIDS_COLUMNS["fwd_header_length"], 0))
    bwd_header = _safe_float(row.get(CICIDS_COLUMNS["bwd_header_length"], 0))
    down_up = _safe_float(row.get(CICIDS_COLUMNS["down_up_ratio"], 0))
    init_win_fwd = _safe_float(row.get(CICIDS_COLUMNS["init_win_bytes_forward"], 0))
    init_win_bwd = _safe_float(row.get(CICIDS_COLUMNS["init_win_bytes_backward"], 0))
    min_pkt = _safe_float(row.get(CICIDS_COLUMNS["min_packet_length"], 0))
    max_pkt = _safe_float(row.get(CICIDS_COLUMNS["max_packet_length"], 0))
    fwd_psh = _safe_float(row.get(CICIDS_COLUMNS["fwd_psh_flags"], 0))
    fwd_urg = _safe_float(row.get(CICIDS_COLUMNS["fwd_urg_flags"], 0))

    # Map to our 26 features:
    is_http_port = float(dest_port in (80, 443, 8080, 8443))

    return [
        # 0: method_encoded — approximate from protocol (6=TCP→POST-like, 17=UDP→GET-like)
        float(1 if protocol == 6 else 0),
        # 1: path_depth — approximate from port diversity
        float(min(dest_port / 1000, 10)),
        # 2: path_length — approximate from fwd packet mean length
        float(min(fwd_pkt_mean / 10, 200)),
        # 3: path_has_traversal — unusual ports or scanning behavior
        float(rst_count > 0 and syn_count > 5),
        # 4: path_has_suspicious_ext — unusual protocol/port combinations
        float(not is_http_port and dest_port < 1024 and dest_port > 0),
        # 5: query_param_count — approximate from total forward packets
        float(min(total_fwd, 50)),
        # 6: query_length — approximate from forward payload
        float(min(fwd_pkt_mean * total_fwd / 100, 500)),
        # 7: query_has_sql_injection — high byte rate + specific patterns
        float(flow_bps > 1e6 and total_fwd > 10),
        # 8: query_has_xss — not directly detectable from network flow
        0.0,
        # 9: query_has_cmd_injection — high packet rate + URG flags
        float(fwd_urg > 0 or (flow_pps > 1000 and total_fwd > 20)),
        # 10: path_has_sql_injection (network level → volume-based proxy)
        float(flow_bps > 5e5 and fwd_pkt_mean > 500),
        # 11: path_has_xss
        0.0,
        # 12: ua_is_known_browser — HTTP port + normal flow duration
        float(is_http_port and 0 < flow_duration < 30e6),
        # 13: ua_is_bot — high packet rate + scanning pattern
        float(flow_pps > 500 or (syn_count > 3 and ack_count == 0)),
        # 14: ua_is_empty — no backward traffic (one-way probe)
        float(total_bwd == 0 and total_fwd > 0),
        # 15: ua_length — approximate from header length
        float(min(fwd_header / 10, 500)),
        # 16: content_length_log
        float(math.log1p(avg_pkt_size)) if avg_pkt_size > 0 else 0.0,
        # 17: has_content_length — has meaningful payload
        float(avg_pkt_size > 40),
        # 18: status_code_class — approximate from response characteristics
        float(
            0 if (total_bwd > 0 and bwd_pkt_mean > 0)
            else 2 if (rst_count > 0)
            else 3 if (total_bwd == 0)
            else 1
        ),
        # 19: response_time_log
        float(math.log1p(flow_duration / 1000)) if flow_duration > 0 else 0.0,
        # 20: has_referer — approximate from established TCP (SYN+ACK present)
        float(syn_count > 0 and ack_count > 0 and fin_count > 0),
        # 21: protocol_version
        float(1.1 if protocol == 6 else 2.0 if protocol == 17 else 0.0),
        # 22: header_count — approximate from header bytes
        float(min((fwd_header + bwd_header) / 32, 30)),
        # 23: has_special_chars_in_path — flag anomalous packet sizes
        float(max_pkt > 10000 or (max_pkt > 0 and min_pkt == 0 and max_pkt > 1000)),
        # 24: path_entropy — use packet size distribution as entropy proxy
        float(
            _entropy([min_pkt, max_pkt, avg_pkt_size, fwd_pkt_mean, bwd_pkt_mean])
        ),
        # 25: query_entropy — use flow characteristic distribution
        float(
            _entropy(
                [flow_bps, flow_pps, fwd_iat, down_up, init_win_fwd]
            )
        ),
    ]


def preprocess_cicids(raw_dir: str | Path, output_path: str | Path):
    """Load all CICIDS2017 CSVs, convert to our feature format, and save.

    Args:
        raw_dir: Directory containing the raw CICIDS2017 CSV files.
        output_path: Path for the output .npz file.
    """
    import csv

    raw_dir = Path(raw_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        logger.error("No CSV files found in %s", raw_dir)
        logger.error(
            "Download CICIDS2017 MachineLearningCSV.zip from "
            "https://www.unb.ca/cic/datasets/ids-2017.html "
            "and extract into %s",
            raw_dir,
        )
        sys.exit(1)

    all_features = []
    all_labels = []
    label_counts = Counter()
    skipped = 0

    for csv_file in csv_files:
        logger.info("Processing %s ...", csv_file.name)
        with open(csv_file, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader):
                label_key = CICIDS_COLUMNS["label"]
                label = row.get(label_key, "").strip()
                if not label:
                    skipped += 1
                    continue

                zone = LABEL_TO_ZONE.get(label)
                if zone is None:
                    skipped += 1
                    continue

                try:
                    features = cicids_row_to_features(row)
                except Exception:
                    skipped += 1
                    continue

                all_features.append(features)
                all_labels.append(zone)
                label_counts[label] += 1

                if (row_num + 1) % 100000 == 0:
                    logger.info("  ... %d rows processed", row_num + 1)

    logger.info("Total rows: %d, skipped: %d", len(all_features), skipped)
    logger.info("Label distribution: %s", dict(label_counts))

    X = np.array(all_features, dtype=np.float64)
    y = np.array(all_labels, dtype=np.int32)

    # Replace any remaining NaN/Inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    # ── Balance the dataset ─────────────────────────────────────────
    # CICIDS2017 is heavily imbalanced (80% benign). We undersample the
    # majority class to create a more balanced training set.
    zone_counts = Counter(y)
    logger.info("Zone distribution before balancing: %s", dict(zone_counts))

    min_count = min(zone_counts.values())
    # Cap majority class at 3x the minority class
    max_per_class = max(min_count * 3, 5000)

    balanced_indices = []
    for zone_id in sorted(zone_counts.keys()):
        zone_indices = np.where(y == zone_id)[0]
        if len(zone_indices) > max_per_class:
            rng = np.random.RandomState(42)
            zone_indices = rng.choice(zone_indices, size=max_per_class, replace=False)
        balanced_indices.extend(zone_indices)

    rng = np.random.RandomState(42)
    rng.shuffle(balanced_indices)
    X_balanced = X[balanced_indices]
    y_balanced = y[balanced_indices]

    logger.info(
        "Zone distribution after balancing: %s",
        dict(Counter(y_balanced)),
    )
    logger.info("Final dataset shape: X=%s, y=%s", X_balanced.shape, y_balanced.shape)

    np.savez_compressed(
        output_path,
        X=X_balanced,
        y=y_balanced,
        feature_names=np.array([
            "method_encoded", "path_depth", "path_length", "path_has_traversal",
            "path_has_suspicious_ext", "query_param_count", "query_length",
            "query_has_sql_injection", "query_has_xss", "query_has_cmd_injection",
            "path_has_sql_injection", "path_has_xss", "ua_is_known_browser",
            "ua_is_bot", "ua_is_empty", "ua_length", "content_length_log",
            "has_content_length", "status_code_class", "response_time_log",
            "has_referer", "protocol_version", "header_count",
            "has_special_chars_in_path", "path_entropy", "query_entropy",
        ]),
    )
    logger.info("Saved processed data to %s", output_path)


def __main__():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    base = Path(__file__).resolve().parent
    raw_dir = base / "raw"
    output_path = base / "processed" / "training_data.npz"
    preprocess_cicids(raw_dir, output_path)


if __name__ == "__main__":
    __main__()
