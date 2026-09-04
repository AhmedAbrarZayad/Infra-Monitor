from datetime import timedelta

import httpx
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Organization, VictoriaMetricsTenant
from servers.models import Servers, Service
from servers.services.victoriametrics import (
    METRIC_DEFINITIONS,
    InvalidMetricError,
    VictoriaMetricsQueryAdapter,
    bounded_range,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://vmselect")
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(self.status_code, request=request))

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@override_settings(VICTORIAMETRICS_SELECT_URL="http://vmselect:8481")
class VictoriaMetricsQueryAdapterTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="A", summary="A")
        self.other_organization = Organization.objects.create(name="B", summary="B")
        self.tenant = VictoriaMetricsTenant.objects.create(organization=self.organization)
        self.other_tenant = VictoriaMetricsTenant.objects.create(organization=self.other_organization)
        self.server = Servers.objects.create(
            organization=self.organization,
            name="API",
            host_name="api-01",
            environment="prod",
        )
        self.service = Service.objects.create(
            server_id=self.server,
            service_name="payments",
            display_name="payments",
        )

    def test_all_normalized_server_metric_expressions_are_scoped_and_have_units(self):
        adapter = VictoriaMetricsQueryAdapter(client=FakeClient(None))
        for code, definition in METRIC_DEFINITIONS.items():
            expression, unit = adapter.expression(server=self.server, code=code)
            self.assertIn(f'server_id="{self.server.server_id}"', expression)
            self.assertEqual(unit, definition.unit)

    def test_service_metrics_use_trusted_service_id_and_unsupported_is_empty(self):
        adapter = VictoriaMetricsQueryAdapter(client=FakeClient(None))
        expression, unit = adapter.expression(server=self.server, service=self.service, code="cpu_r")
        self.assertIn(f'service_id="{self.service.service_id}"', expression)
        self.assertEqual(unit, "percent")
        result = adapter.range(server=self.server, service=self.service, code="disk_u")
        self.assertTrue(result["available"])
        self.assertEqual(result["points"], [])

    def test_unknown_metric_is_exact_and_invalid_name_is_rejected(self):
        adapter = VictoriaMetricsQueryAdapter(client=FakeClient(None))
        expression, unit = adapter.expression(server=self.server, code="http_requests_total")
        self.assertIn('__name__="http_requests_total"', expression)
        self.assertIsNone(unit)
        with self.assertRaises(InvalidMetricError):
            adapter.expression(server=self.server, code='up} or {secret="x"')

    def test_latest_uses_trusted_tenant_url_and_parses_recent_matrix(self):
        client = FakeClient(FakeResponse({
            "status": "success",
            "data": {"resultType": "matrix", "result": [{
                "metric": {"server_id": str(self.server.server_id)},
                "values": [[1_700_000_000, "42.5"]],
            }]},
        }))
        result = VictoriaMetricsQueryAdapter(client=client).latest(server=self.server, code="cpu_r")
        self.assertTrue(result["available"])
        self.assertEqual(result["point"]["value"], 42.5)
        self.assertEqual(result["point"]["unit"], "percent")
        self.assertIn(f"/select/{self.tenant.account_id}%3A0/", client.calls[0][0])
        self.assertNotIn(str(self.other_tenant.account_id), client.calls[0][0])

    def test_range_parses_matrix_units_and_empty_result_is_available(self):
        client = FakeClient(FakeResponse({
            "status": "success",
            "data": {"resultType": "matrix", "result": [{
                "metric": {"unit": "requests_per_second", "server_id": str(self.server.server_id)},
                "values": [[1_700_000_000, "1"], [1_700_000_015, "2"]],
            }]},
        }))
        result = VictoriaMetricsQueryAdapter(client=client).range(
            server=self.server,
            code="http_requests_total",
        )
        self.assertEqual([point["value"] for point in result["points"]], [1.0, 2.0])
        self.assertEqual(result["unit"], "requests_per_second")

        client.response = FakeResponse({"status": "success", "data": {"result": []}})
        empty = VictoriaMetricsQueryAdapter(client=client).range(server=self.server, code="cpu_r")
        self.assertTrue(empty["available"])
        self.assertEqual(empty["points"], [])

    def test_timeout_and_malformed_response_are_unavailable(self):
        request = httpx.Request("GET", "http://vmselect")
        timeout = VictoriaMetricsQueryAdapter(client=FakeClient(httpx.ConnectTimeout("timeout", request=request)))
        self.assertFalse(timeout.latest(server=self.server, code="cpu_r")["available"])
        malformed = VictoriaMetricsQueryAdapter(client=FakeClient(FakeResponse({"status": "error"})))
        self.assertFalse(malformed.range(server=self.server, code="cpu_r")["available"])

    def test_range_bounds_and_step_validation(self):
        now = timezone.now()
        with self.assertRaises(ValueError):
            bounded_range(start=now, end=now)
        with self.assertRaises(ValueError):
            bounded_range(start=now - timedelta(days=31), end=now)
        start, end, step = bounded_range(start=now - timedelta(hours=1), end=now)
        self.assertEqual(step, 15)
        with self.assertRaises(ValueError):
            bounded_range(start=start, end=end, step="bad")
