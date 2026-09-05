import httpx
from django.test import SimpleTestCase, override_settings

from ml_model.services import MLServiceClient, MLServiceError, ModelNotFoundError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ml/infer")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@override_settings(
    ML_SERVICE_URL="http://ml:80",
    ML_SERVICE_TOKEN="test-token",
    ML_REQUEST_TIMEOUT_SECONDS=12,
)
class MLServiceClientTests(SimpleTestCase):
    def test_sends_shared_bearer_token_and_timeout(self):
        transport = FakeClient(FakeResponse(payload={"status": "trained"}))
        result = MLServiceClient(client=transport).train(service_id="service", rows=[])
        self.assertEqual(result["status"], "trained")
        _, kwargs = transport.calls[0]
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-token")
        self.assertEqual(kwargs["timeout"], 12)

    def test_maps_missing_model_and_transport_failures(self):
        missing = FakeClient(FakeResponse(404, {"detail": {"code": "model_not_found"}}))
        with self.assertRaises(ModelNotFoundError):
            MLServiceClient(client=missing)._post("/infer", {})

        request = httpx.Request("POST", "http://ml/infer")
        failed = FakeClient(httpx.ConnectTimeout("timeout", request=request))
        with self.assertRaises(MLServiceError):
            MLServiceClient(client=failed)._post("/infer", {})
