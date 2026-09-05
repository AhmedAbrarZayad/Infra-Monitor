from django.test import SimpleTestCase

from installer.remote_write import WriteRequest, service_health_observations


class ServiceHealthObservationTests(SimpleTestCase):
    def _series(self, request, *, service, value):
        series = request.timeseries.add()
        for name, label_value in (
            ("__name__", "up"),
            ("service_name", service),
        ):
            label = series.labels.add()
            label.name = name
            label.value = label_value
        sample = series.samples.add()
        sample.value = value

    def test_extracts_latest_explicit_up_and_failure_wins(self):
        request = WriteRequest()
        self._series(request, service="payments", value=1)
        self._series(request, service="payments", value=0)

        self.assertEqual(service_health_observations(request), {"payments": False})

    def test_ignores_unlabelled_and_non_up_series(self):
        request = WriteRequest()
        series = request.timeseries.add()
        label = series.labels.add()
        label.name = "__name__"
        label.value = "container_last_seen"
        series.samples.add().value = 1

        self.assertEqual(service_health_observations(request), {})
