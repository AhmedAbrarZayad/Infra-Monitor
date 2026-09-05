from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.models import Organization
from ml_model.services import InsufficientTelemetryError, ModelNotFoundError
from ml_model.tasks import completed_window, dispatch_service_ml, orchestrate_service_ml
from servers.models import Servers, Service


@override_settings(
    ML_INFERENCE_WINDOW_SECONDS=300,
    ML_METRIC_STEP_SECONDS=60,
    ML_TRAINING_LOOKBACK_HOURS=24,
)
class MLTaskTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="A", summary="A")
        server = Servers.objects.create(
            organization=organization,
            name="API",
            host_name="api-1",
            environment="test",
        )
        self.service = Service.objects.create(
            server_id=server,
            service_name="web",
            display_name="Web",
        )

    def test_completed_window_is_previous_aligned_five_minute_bucket(self):
        start, end = completed_window(datetime(2026, 9, 5, 10, 7, 42, tzinfo=UTC))
        self.assertEqual(end, datetime(2026, 9, 5, 10, 5, tzinfo=UTC))
        self.assertEqual(start, datetime(2026, 9, 5, 10, 0, tzinfo=UTC))

    @patch("ml_model.tasks.orchestrate_service_ml.delay")
    def test_dispatcher_enqueues_each_service_independently(self, delay):
        result = dispatch_service_ml.run()
        self.assertEqual(result, {"dispatched": 1})
        delay.assert_called_once_with(str(self.service.service_id))

    @patch("ml_model.tasks.MLServiceClient")
    @patch("ml_model.tasks.ServiceFeatureBuilder")
    def test_missing_model_trains_once_then_retries_inference(self, builder_class, client_class):
        inference_rows = [{"timestamp": "inference", "values": {}}]
        training_rows = [{"timestamp": "training", "values": {}}]
        builder_class.return_value.build.side_effect = [
            inference_rows,
            training_rows,
        ]
        client = client_class.return_value
        client.infer.side_effect = [
            ModelNotFoundError("missing"),
            {"detection_id": "detection-1"},
        ]

        result = orchestrate_service_ml.run(str(self.service.service_id))

        self.assertEqual(result["status"], "completed")
        client.train.assert_called_once_with(
            service_id=self.service.service_id,
            rows=training_rows,
        )
        self.assertEqual(client.infer.call_count, 2)

    @patch("ml_model.tasks.ServiceFeatureBuilder")
    def test_insufficient_inference_data_skips_only_that_service(self, builder_class):
        builder_class.return_value.build.side_effect = InsufficientTelemetryError("missing")
        result = orchestrate_service_ml.run(str(self.service.service_id))
        self.assertEqual(result["status"], "insufficient_inference_data")

    def test_deleted_service_is_safely_ignored(self):
        missing_id = self.service.service_id
        self.service.delete()
        self.assertEqual(
            orchestrate_service_ml.run(str(missing_id)),
            {"status": "service_not_found"},
        )
