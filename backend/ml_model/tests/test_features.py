from datetime import UTC, datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from ml_model.services import FEATURE_NAMES, InsufficientTelemetryError, ServiceFeatureBuilder


class FakeAdapter:
    def __init__(self, points=None, unavailable=None):
        self.points = points or {}
        self.unavailable = unavailable
        self.calls = []

    def range(self, **kwargs):
        self.calls.append(kwargs)
        code = kwargs["code"]
        return {
            "available": code != self.unavailable,
            "points": self.points.get(code, []),
        }


class ServiceFeatureBuilderTests(SimpleTestCase):
    def test_aligns_only_complete_finite_service_rows(self):
        first = datetime(2026, 9, 5, 10, 0, tzinfo=UTC)
        second = datetime(2026, 9, 5, 10, 1, tzinfo=UTC)
        points = {
            feature: [
                {"timestamp": first, "value": index + 1},
                {"timestamp": second, "value": index + 2},
            ]
            for index, feature in enumerate(FEATURE_NAMES)
        }
        points["eth1_fo"] = [{"timestamp": first, "value": 6}]
        adapter = FakeAdapter(points)
        service = SimpleNamespace(server_id=object())

        rows = ServiceFeatureBuilder(adapter=adapter).build(
            service=service,
            start=first,
            end=second,
            step=60,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0]["values"]), FEATURE_NAMES)
        self.assertEqual(rows[0]["values"]["cpu_r"], 1.0)
        self.assertEqual(len(adapter.calls), 6)
        self.assertTrue(all(call["service"] is service for call in adapter.calls))
        self.assertTrue(all(call["step"] == 60 for call in adapter.calls))

    def test_rejects_unavailable_or_incomplete_telemetry(self):
        service = SimpleNamespace(server_id=object())
        now = datetime(2026, 9, 5, tzinfo=UTC)
        with self.assertRaises(InsufficientTelemetryError):
            ServiceFeatureBuilder(adapter=FakeAdapter(unavailable="disk_r")).build(
                service=service,
                start=now,
                end=now,
            )
        with self.assertRaises(InsufficientTelemetryError):
            ServiceFeatureBuilder(adapter=FakeAdapter()).build(
                service=service,
                start=now,
                end=now,
            )

    def test_rejects_memory_values_that_are_not_percentages(self):
        now = datetime(2026, 9, 5, tzinfo=UTC)
        points = {
            feature: [{"timestamp": now, "value": 1}]
            for feature in FEATURE_NAMES
        }
        points["mem_u"] = [{"timestamp": now, "value": 43_008_000}]

        with self.assertRaises(InsufficientTelemetryError):
            ServiceFeatureBuilder(adapter=FakeAdapter(points)).build(
                service=SimpleNamespace(server_id=object()),
                start=now,
                end=now,
            )
