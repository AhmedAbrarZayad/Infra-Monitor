import math

from servers.services import VictoriaMetricsQueryAdapter

FEATURE_NAMES = ("cpu_r", "mem_u", "disk_r", "disk_w", "eth1_fi", "eth1_fo")


class InsufficientTelemetryError(RuntimeError):
    pass


class ServiceFeatureBuilder:
    def __init__(self, adapter=None):
        self.adapter = adapter or VictoriaMetricsQueryAdapter()

    def build(self, *, service, start, end, step=60, min_rows=1):
        values_by_feature = {}
        for feature in FEATURE_NAMES:
            result = self.adapter.range(
                server=service.server_id,
                service=service,
                code=feature,
                start=start,
                end=end,
                step=step,
            )
            if not result["available"]:
                raise InsufficientTelemetryError("VictoriaMetrics is unavailable.")
            values_by_feature[feature] = {
                point["timestamp"]: float(point["value"])
                for point in result["points"]
                if math.isfinite(float(point["value"]))
            }

        timestamps = set.intersection(
            *(set(values_by_feature[feature]) for feature in FEATURE_NAMES)
        )
        rows = [
            {
                "timestamp": timestamp.isoformat(),
                "values": {
                    feature: values_by_feature[feature][timestamp] for feature in FEATURE_NAMES
                },
            }
            for timestamp in sorted(timestamps)
        ]
        if len(rows) < min_rows:
            raise InsufficientTelemetryError(
                f"At least {min_rows} complete service-level feature rows are required."
            )
        return rows
