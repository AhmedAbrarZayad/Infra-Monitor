"""Feature extraction for request threat classification.

Transforms raw HTTP request metadata into a numeric feature vector suitable
for the ML classifier (Random Forest / XGBoost). Each feature is documented
with its index in the output vector.

The same extraction logic runs in two places:
1. Django (backend) — when preparing batches for the ML service.
2. FastAPI (model service) — when training from the CICIDS-derived dataset.

This module is the single source of truth. The FastAPI service imports
a compatible copy.
"""

from __future__ import annotations

import math
import re
from collections import Counter

# ── Threat pattern regexes ──────────────────────────────────────────

_SQL_INJECTION_PATTERNS = re.compile(
    r"((\%27)|(\'))\s*((\%6F)|o|(\%4F))((\%72)|r|(\%52))"  # 'or
    r"|(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b)"
    r"|(--\s)"
    r"|(\b(AND|OR)\b\s+\d+\s*=\s*\d+)"
    r"|(\bWAITFOR\s+DELAY\b)"
    r"|(\bBENCHMARK\s*\()",
    re.IGNORECASE,
)

_XSS_PATTERNS = re.compile(
    r"(<\s*script)"
    r"|(javascript\s*:)"
    r"|(on(error|load|click|mouseover|focus|blur)\s*=)"
    r"|(<\s*img\s+.*?src\s*=)"
    r"|(<\s*iframe)",
    re.IGNORECASE,
)

_PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.[\\/])")

_COMMAND_INJECTION_PATTERNS = re.compile(
    r"(\|\s*\w+)"
    r"|(;\s*(ls|cat|rm|wget|curl|nc|bash|sh|python|perl|ruby)\b)"
    r"|(`[^`]+`)"
    r"|(\$\([^)]+\))",
    re.IGNORECASE,
)

_SUSPICIOUS_EXTENSIONS = re.compile(
    r"\.(php|asp|aspx|jsp|cgi|env|git|svn|bak|sql|conf|ini|log|yml|yaml|xml|"
    r"htaccess|htpasswd|DS_Store|swp|old|orig|save|dist|config)\b",
    re.IGNORECASE,
)

_KNOWN_BROWSERS = re.compile(
    r"(Chrome|Firefox|Safari|Edge|Opera|MSIE|Trident)/", re.IGNORECASE
)

_BOT_KEYWORDS = re.compile(
    r"(bot|crawler|spider|scraper|scanner|nmap|nikto|sqlmap|burp|dirbuster|"
    r"gobuster|wfuzz|masscan|zap|acunetix|nessus|openvas|metasploit|hydra|"
    r"curl|wget|python-requests|go-http-client|java/|libwww-perl|httpclient)",
    re.IGNORECASE,
)

# ── Feature name registry (matches ML model column order) ──────────

FEATURE_NAMES = [
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

_METHOD_MAP = {
    "GET": 0,
    "POST": 1,
    "PUT": 2,
    "PATCH": 3,
    "DELETE": 4,
    "HEAD": 5,
    "OPTIONS": 6,
    "TRACE": 7,
    "CONNECT": 8,
}


def _entropy(text: str) -> float:
    """Shannon entropy of a string."""
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
        if count > 0
    )


def _safe_log(value: float | int | None, base: float = 1.0) -> float:
    """Log-transform with fallback for None / zero / negative."""
    if value is None or value <= 0:
        return 0.0
    return math.log1p(value - base) if value > base else 0.0


def extract_features(
    *,
    method: str,
    path: str,
    query_string: str = "",
    status_code: int | None = None,
    user_agent: str = "",
    content_length: int | None = None,
    response_time_ms: float | None = None,
    referer: str = "",
    protocol: str = "",
    headers_digest: dict | None = None,
) -> list[float]:
    """Extract a fixed-length numeric feature vector from request metadata.

    Returns a list of floats in the order defined by ``FEATURE_NAMES``.
    """
    path = path or "/"
    query_string = query_string or ""
    user_agent = user_agent or ""
    referer = referer or ""
    protocol = protocol or ""
    headers_digest = headers_digest or {}

    full_url_part = path + ("?" + query_string if query_string else "")

    return [
        # 0: method_encoded
        float(_METHOD_MAP.get(method.upper(), 9)),
        # 1: path_depth — number of non-empty segments
        float(len([seg for seg in path.split("/") if seg])),
        # 2: path_length
        float(len(path)),
        # 3: path_has_traversal
        float(bool(_PATH_TRAVERSAL_PATTERN.search(path))),
        # 4: path_has_suspicious_ext
        float(bool(_SUSPICIOUS_EXTENSIONS.search(path))),
        # 5: query_param_count
        float(query_string.count("=")) if query_string else 0.0,
        # 6: query_length
        float(len(query_string)),
        # 7: query_has_sql_injection
        float(bool(_SQL_INJECTION_PATTERNS.search(query_string))),
        # 8: query_has_xss
        float(bool(_XSS_PATTERNS.search(query_string))),
        # 9: query_has_cmd_injection
        float(bool(_COMMAND_INJECTION_PATTERNS.search(full_url_part))),
        # 10: path_has_sql_injection
        float(bool(_SQL_INJECTION_PATTERNS.search(path))),
        # 11: path_has_xss
        float(bool(_XSS_PATTERNS.search(path))),
        # 12: ua_is_known_browser
        float(bool(_KNOWN_BROWSERS.search(user_agent))),
        # 13: ua_is_bot
        float(bool(_BOT_KEYWORDS.search(user_agent))),
        # 14: ua_is_empty
        float(not user_agent.strip()),
        # 15: ua_length
        float(len(user_agent)),
        # 16: content_length_log
        _safe_log(content_length),
        # 17: has_content_length
        float(content_length is not None and content_length > 0),
        # 18: status_code_class  (2xx=0, 3xx=1, 4xx=2, 5xx=3, other=4)
        float(
            (status_code // 100 - 2) if status_code and 200 <= status_code < 600 else 4
        ),
        # 19: response_time_log
        _safe_log(response_time_ms),
        # 20: has_referer
        float(bool(referer.strip())),
        # 21: protocol_version  (1.0→1, 1.1→1.1, 2→2, 3→3)
        _parse_protocol_version(protocol),
        # 22: header_count
        float(len(headers_digest)),
        # 23: has_special_chars_in_path
        float(
            bool(
                re.search(
                    r"[<>{}|\\^~\[\]`]",
                    path,
                )
            )
        ),
        # 24: path_entropy
        _entropy(path),
        # 25: query_entropy
        _entropy(query_string),
    ]


def _parse_protocol_version(protocol: str) -> float:
    """Extract numeric version from protocol strings like 'HTTP/1.1'."""
    match = re.search(r"(\d+(?:\.\d+)?)", protocol)
    if match:
        return float(match.group(1))
    return 0.0


def extract_threat_signals(
    *,
    path: str,
    query_string: str = "",
    user_agent: str = "",
) -> list[str]:
    """Return human-readable threat signal codes found in the request."""
    signals = []
    full = path + ("?" + query_string if query_string else "")

    if _SQL_INJECTION_PATTERNS.search(full):
        signals.append("sql_injection")
    if _XSS_PATTERNS.search(full):
        signals.append("xss")
    if _COMMAND_INJECTION_PATTERNS.search(full):
        signals.append("command_injection")
    if _PATH_TRAVERSAL_PATTERN.search(path):
        signals.append("path_traversal")
    if _SUSPICIOUS_EXTENSIONS.search(path):
        signals.append("suspicious_extension")
    if _BOT_KEYWORDS.search(user_agent):
        signals.append("known_scanner_or_bot")
    if not user_agent.strip():
        signals.append("empty_user_agent")

    return signals
