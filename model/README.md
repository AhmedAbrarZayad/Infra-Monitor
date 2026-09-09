# Infra Monitor ML Service

This FastAPI service loads approved model artifacts and runs inference for
completed metric windows and Request Shield access logs. Training is an offline
release operation and is not exposed by the production Request Shield API.

## Endpoints

- `GET /health`
- `GET /ready` (fails until the Request Shield artifact is valid)
- `POST /train` (shared Bearer token required)
- `POST /infer` (shared Bearer token required)
- `POST /classify-requests` (shared Bearer token required)

The fixed feature order is `cpu_r`, `mem_u`, `disk_r`, `disk_w`, `eth1_fi`, and
`eth1_fo`. Models are stored under `ML_ARTIFACT_DIR/<service_id>/`.

Copy `.env.example` to `model/.env`. Set its `ML_SERVICE_TOKEN` to the same
value used in `backend/.env`; Flutter must never receive it. The model
environment file is ignored by Git.

From the repository root:

```shell
docker compose build ml_service
docker compose up ml_service
```

Run tests inside the service image:

```shell
docker run --rm -v "${PWD}/model/tests:/code/tests:ro" infra-monitor-ml-test pytest -q
```
