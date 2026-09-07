"""Tests for the Request Shield (sanitize) feature.

Covers feature extraction, ingestion, classification flow, threat suggestion
generation, and the API views.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from sanitize.features import FEATURE_NAMES, extract_features, extract_threat_signals


class FeatureExtractionTest(TestCase):
    """Verify the feature extraction engine."""

    def test_vector_length_matches_feature_names(self):
        features = extract_features(
            method="GET",
            path="/api/users",
            query_string="page=1",
            status_code=200,
            user_agent="Mozilla/5.0 Chrome/120",
            content_length=0,
            response_time_ms=42.5,
        )
        self.assertEqual(len(features), len(FEATURE_NAMES))

    def test_all_features_are_numeric(self):
        features = extract_features(
            method="POST",
            path="/login",
            query_string="",
            status_code=401,
            user_agent="",
        )
        for i, value in enumerate(features):
            self.assertIsInstance(
                value, float, f"Feature {FEATURE_NAMES[i]} is not a float"
            )

    def test_sql_injection_detected_in_query(self):
        features = extract_features(
            method="GET",
            path="/search",
            query_string="q=1' OR 1=1--",
        )
        # Feature index 7 = query_has_sql_injection
        self.assertEqual(features[7], 1.0)

    def test_xss_detected_in_query(self):
        features = extract_features(
            method="GET",
            path="/page",
            query_string='q=<script>alert("xss")</script>',
        )
        # Feature index 8 = query_has_xss
        self.assertEqual(features[8], 1.0)

    def test_path_traversal_detected(self):
        features = extract_features(
            method="GET",
            path="/files/../../etc/passwd",
        )
        # Feature index 3 = path_has_traversal
        self.assertEqual(features[3], 1.0)

    def test_bot_user_agent_detected(self):
        features = extract_features(
            method="GET",
            path="/",
            user_agent="sqlmap/1.5",
        )
        # Feature index 13 = ua_is_bot
        self.assertEqual(features[13], 1.0)
        # Feature index 12 = ua_is_known_browser (should be 0)
        self.assertEqual(features[12], 0.0)

    def test_known_browser_detected(self):
        features = extract_features(
            method="GET",
            path="/",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        self.assertEqual(features[12], 1.0)  # ua_is_known_browser
        self.assertEqual(features[14], 0.0)  # ua_is_empty

    def test_empty_user_agent_flagged(self):
        features = extract_features(method="GET", path="/", user_agent="")
        self.assertEqual(features[14], 1.0)  # ua_is_empty

    def test_suspicious_extension_detected(self):
        features = extract_features(method="GET", path="/config/.env")
        self.assertEqual(features[4], 1.0)  # path_has_suspicious_ext

    def test_clean_request(self):
        features = extract_features(
            method="GET",
            path="/api/v1/users",
            query_string="page=1&limit=20",
            status_code=200,
            user_agent="Mozilla/5.0 Chrome/120",
            content_length=0,
        )
        # No attack signals should fire
        self.assertEqual(features[3], 0.0)   # path_has_traversal
        self.assertEqual(features[7], 0.0)   # query_has_sql_injection
        self.assertEqual(features[8], 0.0)   # query_has_xss
        self.assertEqual(features[13], 0.0)  # ua_is_bot
        self.assertEqual(features[14], 0.0)  # ua_is_empty


class ThreatSignalExtractionTest(TestCase):
    """Verify human-readable threat signal extraction."""

    def test_sql_injection_signal(self):
        signals = extract_threat_signals(
            path="/search",
            query_string="q=1' OR 1=1--",
        )
        self.assertIn("sql_injection", signals)

    def test_xss_signal(self):
        signals = extract_threat_signals(
            path="/page",
            query_string="q=<script>alert(1)</script>",
        )
        self.assertIn("xss", signals)

    def test_path_traversal_signal(self):
        signals = extract_threat_signals(path="/../../etc/passwd")
        self.assertIn("path_traversal", signals)

    def test_bot_signal(self):
        signals = extract_threat_signals(
            path="/", user_agent="Nikto/2.1"
        )
        self.assertIn("known_scanner_or_bot", signals)

    def test_empty_ua_signal(self):
        signals = extract_threat_signals(path="/", user_agent="")
        self.assertIn("empty_user_agent", signals)

    def test_clean_request_no_signals(self):
        signals = extract_threat_signals(
            path="/api/v1/users",
            query_string="page=1",
            user_agent="Mozilla/5.0 Chrome/120",
        )
        self.assertEqual(signals, [])

    def test_command_injection_signal(self):
        signals = extract_threat_signals(
            path="/api/exec",
            query_string="cmd=; cat /etc/passwd",
        )
        self.assertIn("command_injection", signals)

    def test_multiple_signals(self):
        signals = extract_threat_signals(
            path="/../../admin/.env",
            query_string="q=1' OR 1=1--",
            user_agent="sqlmap/1.5",
        )
        self.assertIn("sql_injection", signals)
        self.assertIn("path_traversal", signals)
        self.assertIn("suspicious_extension", signals)
        self.assertIn("known_scanner_or_bot", signals)
