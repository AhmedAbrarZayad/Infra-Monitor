from datetime import UTC, datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ml_model.services import (
    InsufficientTelemetryError,
    MLServiceClient,
    MLServiceError,
    ModelNotFoundError,
    ServiceFeatureBuilder,
)
from servers.models import Service


def completed_window(now=None):
    now = now or timezone.now()
    window_seconds = settings.ML_INFERENCE_WINDOW_SECONDS
    end_timestamp = int(now.timestamp()) // window_seconds * window_seconds
    end = datetime.fromtimestamp(end_timestamp, tz=UTC)
    return end - timedelta(seconds=window_seconds), end


@shared_task(name="ml_model.dispatch_service_ml")
def dispatch_service_ml():
    service_ids = list(Service.objects.values_list("service_id", flat=True))
    for service_id in service_ids:
        orchestrate_service_ml.delay(str(service_id))
    return {"dispatched": len(service_ids)}


@shared_task(
    bind=True,
    name="ml_model.orchestrate_service_ml",
    autoretry_for=(MLServiceError,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 2},
    soft_time_limit=110,
    time_limit=120,
)
def orchestrate_service_ml(self, service_id):
    try:
        service = Service.objects.select_related("server_id__organization").get(
            service_id=service_id
        )
    except Service.DoesNotExist:
        return {"status": "service_not_found"}

    start, end = completed_window()
    builder = ServiceFeatureBuilder()
    try:
        inference_rows = builder.build(
            service=service,
            start=start,
            end=end,
            step=settings.ML_METRIC_STEP_SECONDS,
        )
    except InsufficientTelemetryError as exc:
        return {"status": "insufficient_inference_data", "detail": str(exc)}

    client = MLServiceClient()
    try:
        result = client.infer(
            service=service,
            start=start,
            end=end,
            rows=inference_rows,
        )
    except ModelNotFoundError:
        training_start = end - timedelta(hours=settings.ML_TRAINING_LOOKBACK_HOURS)
        try:
            training_rows = builder.build(
                service=service,
                start=training_start,
                end=end,
                step=settings.ML_METRIC_STEP_SECONDS,
                min_rows=2,
            )
        except InsufficientTelemetryError as exc:
            return {"status": "insufficient_training_data", "detail": str(exc)}
        client.train(service_id=service.service_id, rows=training_rows)
        result = client.infer(
            service=service,
            start=start,
            end=end,
            rows=inference_rows,
        )

    return {
        "status": "completed",
        "service_id": str(service.service_id),
        "detection_id": result.get("detection_id"),
    }
