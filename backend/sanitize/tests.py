"""Tests for the Request Shield (sanitize) feature.

Covers feature extraction, ingestion, classification flow, threat suggestion
generation, and the API views.
"""

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts.models import Organization
from sanitize.features import FEATURE_NAMES, extract_features, extract_threat_signals
from sanitize.middleware import (
    RequestShieldMiddleware,
    _platform_self_monitor_cache_key,
)
from sanitize.models import RequestLog, ShieldConfig
from sanitize.services import top_offending_ips, zone_distribution, zone_trend


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


class PlatformSelfMonitoringMiddlewareTest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Shield middleware test",
            summary="Middleware tests",
        )
        self.cache_key = _platform_self_monitor_cache_key(self.organization.id)
        cache.delete(self.cache_key)
        self.path = (
            f"/api/organizations/{self.organization.id}/overview/"
        )
        self.middleware = RequestShieldMiddleware(lambda request: HttpResponse())

    def tearDown(self):
        cache.delete(self.cache_key)

    def test_logging_is_disabled_when_config_is_absent(self):
        self.middleware(RequestFactory().get(self.path))

        self.assertFalse(
            RequestLog.objects.filter(organization=self.organization).exists()
        )

    def test_logging_is_disabled_when_self_monitoring_is_off(self):
        ShieldConfig.objects.create(
            organization=self.organization,
            platform_self_monitor=False,
        )

        self.middleware(RequestFactory().get(self.path))

        self.assertFalse(
            RequestLog.objects.filter(organization=self.organization).exists()
        )

    def test_request_shield_endpoints_are_not_self_logged(self):
        ShieldConfig.objects.create(
            organization=self.organization,
            platform_self_monitor=True,
        )
        path = (
            f"/api/organizations/{self.organization.id}/request-shield/requests/"
        )

        self.middleware(RequestFactory().get(path))

        self.assertFalse(
            RequestLog.objects.filter(organization=self.organization).exists()
        )

    def test_logging_is_enabled_when_self_monitoring_is_on(self):
        ShieldConfig.objects.create(
            organization=self.organization,
            platform_self_monitor=True,
        )

        self.middleware(RequestFactory().get(self.path, REMOTE_ADDR="192.0.2.1"))

        self.assertEqual(
            RequestLog.objects.filter(
                organization=self.organization,
                source=RequestLog.Source.PLATFORM,
            ).count(),
            1,
        )


class SourceFilteredAnalyticsTest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Shield analytics test",
            summary="Analytics tests",
        )
        self._create_log(
            source=RequestLog.Source.EXTERNAL,
            zone=RequestLog.Zone.RED,
            source_ip="192.0.2.10",
        )
        self._create_log(
            source=RequestLog.Source.PLATFORM,
            zone=RequestLog.Zone.GRAY,
            source_ip="192.0.2.20",
        )

    def _create_log(self, *, source, zone, source_ip):
        return RequestLog.objects.create(
            organization=self.organization,
            timestamp=timezone.now(),
            source_ip=source_ip,
            method="GET",
            path="/",
            source=source,
            zone=zone,
        )

    def test_analytics_helpers_filter_by_source(self):
        organization_id = self.organization.id

        self.assertEqual(
            zone_distribution(organization_id, source="external"),
            {RequestLog.Zone.RED: 1},
        )
        self.assertEqual(
            top_offending_ips(organization_id, source="external"),
            [
                {
                    "source_ip": "192.0.2.10",
                    "red_count": 1,
                    "gray_count": 0,
                    "total": 1,
                }
            ],
        )
        trend = zone_trend(organization_id, source="external")
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["zone"], RequestLog.Zone.RED)
        self.assertEqual(trend[0]["count"], 1)
