import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

import httpx
from django.conf import settings
from django.utils import timezone

from accounts.models import VictoriaMetricsTenant

METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")


@dataclass(frozen=True)
class MetricDefinition:
    unit: str
    server_expression: str
    service_expression: str | None = None


METRIC_DEFINITIONS = {
    "cpu_r": MetricDefinition(
        "percent",
        "100 - (avg(rate(node_cpu_seconds_total{{{filters},mode=\"idle\"}}[5m])) * 100)",
        "sum(rate(container_cpu_usage_seconds_total{{{filters}}}[5m])) * 100",
    ),
    "load_1": MetricDefinition("load", "max(node_load1{{{filters}}})"),
    "load_5": MetricDefinition("load", "max(node_load5{{{filters}}})"),
    "mem_u": MetricDefinition(
        "percent",
        "(1 - (max(node_memory_MemAvailable_bytes{{{filters}}}) / max(node_memory_MemTotal_bytes{{{filters}}}))) * 100",
        "(sum(container_memory_working_set_bytes{{{filters}}}) / sum(container_spec_memory_limit_bytes{{{filters}}})) * 100",
    ),
    "disk_q": MetricDefinition(
        "seconds_per_second",
        "sum(rate(node_disk_io_time_weighted_seconds_total{{{filters},device!~\"^(loop|ram|fd).*\"}}[5m]))",
    ),
    "disk_r": MetricDefinition(
        "bytes_per_second",
        "sum(rate(node_disk_read_bytes_total{{{filters},device!~\"^(loop|ram|fd).*\"}}[5m]))",
        "sum(rate(container_fs_reads_bytes_total{{{filters},device!=\"\"}}[5m]))",
    ),
    "disk_w": MetricDefinition(
        "bytes_per_second",
        "sum(rate(node_disk_written_bytes_total{{{filters},device!~\"^(loop|ram|fd).*\"}}[5m]))",
        "sum(rate(container_fs_writes_bytes_total{{{filters},device!=\"\"}}[5m]))",
    ),
    "disk_u": MetricDefinition(
        "percent",
        "clamp_max(sum(rate(node_disk_io_time_seconds_total{{{filters},device!~\"^(loop|ram|fd).*\"}}[5m])) * 100, 100)",
    ),
    "eth1_fi": MetricDefinition(
        "bytes_per_second",
        "sum(rate(node_network_receive_bytes_total{{{filters},device!~\"^(lo|veth.*|docker.*)$\"}}[5m]))",
        "sum(rate(container_network_receive_bytes_total{{{filters},interface!=\"lo\"}}[5m]))",
    ),
    "eth1_fo": MetricDefinition(
        "bytes_per_second",
        "sum(rate(node_network_transmit_bytes_total{{{filters},device!~\"^(lo|veth.*|docker.*)$\"}}[5m]))",
        "sum(rate(container_network_transmit_bytes_total{{{filters},interface!=\"lo\"}}[5m]))",
    ),
    "tcp_timeouts": MetricDefinition(
        "timeouts_per_second",
        "sum(rate(node_netstat_TcpExt_TCPTimeouts{{{filters}}}[5m]))",
    ),
}


class MetricsQueryError(Exception):
    pass


class InvalidMetricError(ValueError):
    pass


def _quoted(value):
    return json.dumps(str(value))


def bounded_range(*, start=None, end=None, step=None):
    end = end or timezone.now()
    start = start or end - timedelta(hours=1)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, datetime_timezone.utc)
    if timezone.is_naive(end):
        end = timezone.make_aware(end, datetime_timezone.utc)
    if start >= end:
        raise ValueError("The 'from' timestamp must be earlier than 'to'.")
    if end - start > timedelta(days=30):
        raise ValueError("Metric ranges cannot exceed 30 days.")

    duration_seconds = (end - start).total_seconds()
    minimum_step = max(1, math.ceil(duration_seconds / 4999))
    if step is None:
        step_seconds = max(15, minimum_step)
    else:
        try:
            step_seconds = int(step)
        except (TypeError, ValueError) as exc:
            raise ValueError("Step must be an integer number of seconds.") from exc
        if step_seconds < minimum_step or step_seconds > 3600:
            raise ValueError(
                f"Step must be between {minimum_step} and 3600 seconds for this range."
            )
    return start, end, step_seconds


class VictoriaMetricsQueryAdapter:
    def __init__(self, client=None):
        self.client = client or httpx
        self.base_url = getattr(
            settings,
            "VICTORIAMETRICS_SELECT_URL",
            "http://vmselect:8481",
        ).rstrip("/")
        self.timeout = getattr(settings, "VICTORIAMETRICS_QUERY_TIMEOUT_SECONDS", 10)

    def _tenant_url(self, organization, endpoint):
        try:
            tenant = organization.victoriametrics_tenant
        except VictoriaMetricsTenant.DoesNotExist as exc:
            raise MetricsQueryError("Metrics tenant is not configured.") from exc
        return (
            f"{self.base_url}/select/{tenant.account_id}%3A{tenant.project_id}"
            f"/prometheus/api/v1/{endpoint}"
        )

    def expression(self, *, server, code, service=None):
        filters = [f"server_id={_quoted(server.server_id)}"]
        if service is not None:
            filters.append(f"service_id={_quoted(service.service_id)}")
        filter_text = ",".join(filters)

        definition = METRIC_DEFINITIONS.get(code)
        if definition is not None:
            template = (
                definition.service_expression
                if service is not None
                else definition.server_expression
            )
            if template is None:
                return None, definition.unit
            return template.format(filters=filter_text), definition.unit

        if not METRIC_NAME.fullmatch(code):
            raise InvalidMetricError("Metric must be a valid Prometheus metric name.")
        return f"{{__name__={_quoted(code)},{filter_text}}}", None

    def _request(self, url, params):
        # Dashboard reads must include metrics written in the last few seconds.
        # VictoriaMetrics otherwise applies its default latency offset and may
        # temporarily hide a newly ingested sample from an immediate query.
        params = {**params, "nocache": 1, "latency_offset": "1ms"}
        try:
            response = self.client.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MetricsQueryError("VictoriaMetrics is unavailable.") from exc
        if payload.get("status") != "success" or not isinstance(payload.get("data"), dict):
            raise MetricsQueryError("VictoriaMetrics returned an invalid response.")
        return payload["data"].get("result", [])

    @staticmethod
    def _point(sample, labels, known_unit):
        try:
            timestamp, raw_value = sample
            value = float(raw_value)
            if not math.isfinite(value):
                return None
            recorded_at = datetime.fromtimestamp(float(timestamp), tz=datetime_timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None
        unit = known_unit or labels.get("unit") or "unknown"
        public_labels = {
            key: value
            for key, value in labels.items()
            if key not in {"organization_id", "server_id", "service_id"}
        }
        return {
            "timestamp": recorded_at,
            "recorded_at": recorded_at,
            "value": value,
            "unit": unit,
            "labels": public_labels,
        }

    def latest(self, *, server, code, service=None):
        expression, unit = self.expression(server=server, code=code, service=service)
        if expression is None:
            return {"available": True, "availability": "available", "unit": unit, "point": None}
        now = timezone.now()
        try:
            result = self._request(
                self._tenant_url(server.organization, "query_range"),
                {
                    "query": expression,
                    "start": (now - timedelta(minutes=10)).timestamp(),
                    "end": now.timestamp(),
                    "step": 15,
                },
            )
        except MetricsQueryError:
            return {"available": False, "availability": "unavailable", "unit": unit, "point": None}

        points = []
        for series in result:
            for sample in series.get("values", []):
                point = self._point(sample, series.get("metric", {}), unit)
                if point is not None:
                    points.append(point)
        point = max(points, key=lambda item: item["timestamp"]) if points else None
        return {"available": True, "availability": "available", "unit": unit, "point": point}

    def range(self, *, server, code, service=None, start=None, end=None, step=None):
        start, end, step = bounded_range(start=start, end=end, step=step)
        expression, unit = self.expression(server=server, code=code, service=service)
        if expression is None:
            return {"available": True, "availability": "available", "unit": unit, "points": []}
        try:
            result = self._request(
                self._tenant_url(server.organization, "query_range"),
                {
                    "query": expression,
                    "start": start.timestamp(),
                    "end": end.timestamp(),
                    "step": step,
                },
            )
        except MetricsQueryError:
            return {"available": False, "availability": "unavailable", "unit": unit, "points": []}

        points = []
        units = set()
        for series in result:
            labels = series.get("metric", {})
            for sample in series.get("values", []):
                point = self._point(sample, labels, unit)
                if point is not None:
                    points.append(point)
                    units.add(point["unit"])
        points.sort(key=lambda item: item["timestamp"])
        points = points[-5000:]
        response_unit = unit or (next(iter(units)) if len(units) == 1 else None)
        return {
            "available": True,
            "availability": "available",
            "unit": response_unit,
            "points": points,
        }

    def healthy(self):
        try:
            response = self.client.get(f"{self.base_url}/health", timeout=self.timeout)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
