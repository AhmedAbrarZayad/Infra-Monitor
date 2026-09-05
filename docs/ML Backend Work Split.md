# Simple ML Backend Plan

## 1. Scope

This school-project version keeps ML intentionally small. The FastAPI service
only:

1. trains an Isolation Forest from service-level container metrics; and
2. runs inference with the trained model.

Django owns users, services, lifecycle state, detection storage, and the APIs
used by Flutter. FastAPI does not own datasets, readiness, incidents, alerts,
tenants, correlation, or crash state.

Django's deterministic lifecycle evaluator remains the only authority for
`HEALTHY`, `STALE`, and `OFFLINE`. An ML anomaly means unusual behaviour, not a
confirmed crash.

## 2. Features

Use this exact `container_iforest_v1` service-level feature order:

1. `cpu_r`
2. `mem_u`
3. `disk_r`
4. `disk_w`
5. `eth1_fi`
6. `eth1_fo`

Host-level fallbacks and fabricated zero values are forbidden. Django supplies
complete numeric rows for one service. FastAPI only performs basic request-shape
checks; a separate readiness or dataset-validation system is not required.

## 3. Architecture

```text
VictoriaMetrics
      |
      | Django reads six service-level features
      v
   Django  -------- train/infer JSON --------> FastAPI
      ^                                        Isolation Forest
      |                                               |
      +--- authenticated detection result ------------+
      |
      v
AnomalyDetection table
      |
      | existing authenticated anomaly API
      v
   Flutter
```

Flutter does not call FastAPI. FastAPI posts detections to Django using a shared
Bearer token, while Flutter continues using normal Django user/JWT
authentication. This avoids embedding the ML service secret in the app.

## 4. Django work

### 4.1 Build feature rows

Django queries VictoriaMetrics for one service and:

- uses Django-owned organization, server, and service IDs;
- requests a bounded time range;
- aligns the six metrics by timestamp;
- omits incomplete rows instead of inserting zeros; and
- sends ordinary JSON rows to FastAPI.

No dataset registry or dataset API is required.

### 4.2 Trigger training

Add a Django service function, management command, or simple Celery task that
calls:

```http
POST /train
Authorization: Bearer <ML_SERVICE_TOKEN>
Content-Type: application/json
```

The request contains `service_id`, the ordered feature names, training rows, and
optional Isolation Forest settings such as `contamination`. Training may be
triggered manually for the demonstration. Automated 72-hour readiness and
weekly retraining are out of scope.

### 4.3 Trigger inference

Add a Django service function or simple periodic Celery task that calls:

```http
POST /infer
Authorization: Bearer <ML_SERVICE_TOKEN>
Content-Type: application/json
```

Send the service ID, window timestamps, and complete feature rows. FastAPI
returns the decision, anomaly score, confidence, and model version.

### 4.4 Receive detections

Add one internal Django endpoint:

```http
POST /api/internal/ml/detections/
Authorization: Bearer <ML_SERVICE_TOKEN>
Content-Type: application/json
```

It accepts organization/server/service IDs, the anomaly decision and scores,
feature values, window timestamps, and model version. Django compares the token
with `ML_SERVICE_TOKEN` using a constant-time comparison and returns `401` when
it is missing or incorrect.

Django should verify that the referenced organization, server, and service
exist and belong together before saving. This is basic input integrity, not an
ML validation pipeline.

Add a small idempotency rule, such as uniqueness over service, window start,
window end, and model version, so retries do not duplicate detections.

### 4.5 Return detections to Flutter

Keep the existing endpoints:

- `GET /api/organizations/{organization_id}/anomalies/`
- `GET /api/organizations/{organization_id}/anomalies/{detection_id}/`

They continue using Django user/JWT authorization. Flutter needs no FastAPI URL
or ML shared secret.

Django also embeds the five newest anomalous detections in the Overview response
as `recent_anomalies`. Flutter renders these as warning-level **Needs Attention**
evidence and requests the newest twenty anomalous detections by `server_id` for
server detail. Raw ML detections never enter the incident queue; confirmed
offline/application-unreachable lifecycle events remain critical incidents.

### 4.6 Configuration

```text
ML_SERVICE_URL=http://ml_service:8000
ML_SERVICE_TOKEN=<shared-random-secret>
ML_REQUEST_TIMEOUT_SECONDS=30
```

The secret belongs in environment files and must not be committed.

## 5. FastAPI work

### 5.1 Authorization

Require this header on `/train` and `/infer`:

```http
Authorization: Bearer <ML_SERVICE_TOKEN>
```

Use the same environment-provided token as Django. `/health` may remain public
inside the Docker network.

### 5.2 Training endpoint

Implement `POST /train`:

1. check the Bearer token;
2. check that the six expected fields are present and numeric;
3. train `sklearn.ensemble.IsolationForest`;
4. save the artifact in the persistent artifact directory; and
5. return `service_id`, `model_version`, and success state.

A simple layout is sufficient:

```text
artifacts/
  <service_id>/
    model.joblib
    metadata.json
```

Metadata only needs the model version, feature order, training timestamp, and
Isolation Forest parameters. A model registry, promotion, rollback, object
storage, and formal validation are not required.

### 5.3 Inference endpoint

Implement `POST /infer`:

1. check the Bearer token;
2. load the model for the requested service;
3. apply the stored feature order;
4. run Isolation Forest prediction/scoring;
5. return the result; and
6. post the detection to Django's authenticated internal endpoint.

Posting from FastAPI to Django is the selected flow. Django should not also save
the direct `/infer` response, otherwise one inference could be stored twice.

### 5.4 Health and configuration

Implement `GET /health` with a basic running status and artifact-directory
check. Configure:

```text
ML_SERVICE_TOKEN=<same-shared-random-secret>
DJANGO_INTERNAL_URL=http://backend:8000
ML_ARTIFACT_DIR=/code/artifacts
```

The Compose volume `ml_artifacts:/code/artifacts` preserves trained models
across container restarts.

## 6. Out of scope

This version does not require:

- dataset create/list/detail APIs or dataset lineage;
- an ML PostgreSQL database;
- Redis or separate ML workers;
- readiness tracking or a 72-hour warm-up;
- automatic weekly retraining;
- model validation, activation, rollback, or A/B testing;
- correlation jobs or automatic incident creation;
- object storage;
- FastAPI user/organization management;
- direct FastAPI access from Flutter; or
- ML-based service crash decisions.

These are possible future production improvements, not school-project
requirements.

## 7. Minimal API contract

| Owner | Endpoint | Caller | Purpose |
| --- | --- | --- | --- |
| FastAPI | `GET /health` | Docker/Django | Basic health |
| FastAPI | `POST /train` | Django/operator | Train one service model |
| FastAPI | `POST /infer` | Django | Run inference |
| Django | `POST /api/internal/ml/detections/` | FastAPI | Store an authenticated detection |
| Django | `GET /api/organizations/{organization_id}/anomalies/` | Flutter | List authorized detections |
| Django | `GET /api/organizations/{organization_id}/anomalies/{detection_id}/` | Flutter | Read one authorized detection |

## 8. Implementation order

1. Confirm Django can build complete six-feature service rows.
2. Add shared Bearer-token authentication to FastAPI.
3. Implement `/train` and persistent artifacts.
4. Implement `/infer`.
5. Add Django's internal detection endpoint, model-version field, and
   idempotency constraint.
6. Connect FastAPI inference results to that endpoint.
7. Add a manual command or simple Celery schedule for training and inference.
8. Confirm Flutter can read saved results from the existing anomaly APIs.

## 9. Test plan

### Django

- Reject missing or incorrect ML tokens.
- Store a valid detection.
- Reject mismatched organization/server/service IDs.
- Deduplicate a repeated service/model/window detection.
- Enforce organization authorization on public anomaly reads.
- Confirm an anomaly never changes service lifecycle state.

### FastAPI

- Reject unauthorized training and inference.
- Train, save, and reload an Isolation Forest artifact.
- Reject missing or non-numeric features.
- Preserve feature order between training and inference.
- Return a clear error if the service has no model.
- Submit a detection to Django with the configured token.

## 10. Definition of done

The simplified backend is complete when:

1. Django sends service-level training rows to FastAPI.
2. FastAPI trains and persists an Isolation Forest in `ml_artifacts`.
3. Django sends a new metric window for inference.
4. FastAPI produces and submits an authenticated detection.
5. Django stores it without duplication.
6. Flutter reads it through Django's authorized anomaly API.
7. ML remains independent from crash/offline lifecycle decisions.

## 11. Related documents

- [ML Service Architecture](ML%20Architecture.md)
- [Container Isolation Forest Integration](Container%20Isolation%20Forest%20Integration.md)
- [User-Owned APIs](API%20Documentation/User-Owned%20APIs.md)
