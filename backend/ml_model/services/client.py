import httpx
from django.conf import settings


class MLServiceError(RuntimeError):
    pass


class ModelNotFoundError(MLServiceError):
    pass


class MLServiceClient:
    def __init__(self, client=None):
        self.client = client or httpx
        self.base_url = settings.ML_SERVICE_URL.rstrip("/")
        self.token = settings.ML_SERVICE_TOKEN
        self.timeout = settings.ML_REQUEST_TIMEOUT_SECONDS

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _post(self, path, payload):
        if not self.token:
            raise MLServiceError("ML service token is not configured.")
        try:
            response = self.client.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise MLServiceError("ML service is unavailable.") from exc

        if response.status_code == 404:
            try:
                detail = response.json().get("detail", {})
            except ValueError:
                detail = {}
            if isinstance(detail, dict) and detail.get("code") == "model_not_found":
                raise ModelNotFoundError("No trained model exists for this service.")
        try:
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MLServiceError("ML service returned an invalid response.") from exc

    def train(self, *, service_id, rows, contamination=0.05):
        return self._post(
            "/train",
            {
                "service_id": str(service_id),
                "feature_names": [
                    "cpu_r",
                    "mem_u",
                    "disk_r",
                    "disk_w",
                    "eth1_fi",
                    "eth1_fo",
                ],
                "rows": rows,
                "contamination": contamination,
            },
        )

    def infer(self, *, service, start, end, rows):
        return self._post(
            "/infer",
            {
                "organization_id": str(service.server_id.organization_id),
                "server_id": str(service.server_id_id),
                "service_id": str(service.service_id),
                "window_started_at": start.isoformat(),
                "window_ended_at": end.isoformat(),
                "rows": rows,
            },
        )
