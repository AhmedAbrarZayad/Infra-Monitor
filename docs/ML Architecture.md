# ML Service Architecture

## 1. School-project decision

The ML component is a small FastAPI service dedicated to Isolation Forest
training and inference. Django remains the application backend and owns users,
organizations, servers, services, lifecycle state, detections, alerts, and
incidents.

The detailed task split and API plan are in
[Simple ML Backend Plan](ML%20Backend%20Work%20Split.md).

## 2. Runtime topology

```text
VictoriaMetrics
      |
      | service-scoped metric queries
      v
   Django
      |
      | POST /train and POST /infer
      | Authorization: Bearer <ML_SERVICE_TOKEN>
      v
FastAPI ML service
      |
      +-- Isolation Forest
      +-- /code/artifacts persistent volume
      |
      | POST /api/internal/ml/detections/
      | Authorization: Bearer <ML_SERVICE_TOKEN>
      v
   Django
      |
      | authenticated anomaly list/detail API
      v
   Flutter
```

Flutter never calls FastAPI and never receives the shared ML token.

## 3. Responsibilities

| Component | Responsibility |
| --- | --- |
| Django | Query service metrics, trigger training/inference, validate resource relationships, store detections, authorize Flutter reads, and detect service crashes |
| FastAPI | Train Isolation Forest, persist its artifact, load it, run inference, and submit results to Django |
| VictoriaMetrics | Store time-series telemetry |
| Artifact volume | Preserve `model.joblib` and small model metadata across restarts |
| Flutter | Display Django-authorized lifecycle and anomaly data |

FastAPI does not maintain users, tenants, incidents, alerts, dataset registries,
job registries, model promotion, readiness state, or correlation workers.

## 4. Model inputs

The model uses complete service/container-level rows in this fixed order:

1. `cpu_r`
2. `mem_u`
3. `disk_r`
4. `disk_w`
5. `eth1_fi`
6. `eth1_fo`

Django aligns these features by timestamp. Incomplete rows are omitted; host
fallbacks and fabricated zero values are not used.

## 5. Security boundary

FastAPI `/train` and `/infer`, plus Django's internal detection endpoint, require:

```http
Authorization: Bearer <ML_SERVICE_TOKEN>
```

Both services load the same random secret from environment configuration.
Django compares it in constant time. This is sufficient for the private Docker
network used by the school project. HTTPS, workload identity, token rotation,
and a secrets manager are future production improvements.

Flutter uses the existing Django login/JWT authorization for anomaly reads. A
shared service token must never be included in Flutter source or responses.

## 6. Lifecycle boundary

Django's deterministic evaluator remains the authority for `HEALTHY`, `STALE`,
and `OFFLINE`. FastAPI returns only an anomaly decision and score. An Isolation
Forest anomaly may indicate degradation but does not confirm a crash and cannot
change lifecycle state.

### Flutter presentation

- The five latest anomalous detections appear as warning-level evidence in
  **Overview → Needs Attention**.
- Server detail shows the latest twenty anomalous detections for that server in
  **Anomaly History**.
- Normal inference windows remain queryable through Django but are hidden from
  attention UI.
- Only Django lifecycle confirmation creates critical offline incidents shown
  in **Overview** and **Incidents**. There is no separate Anomalies tab.

## 7. Persistence

For the simple version, FastAPI needs no PostgreSQL or Redis. It stores one model
artifact and metadata file per service in the persistent `ml_artifacts` volume.
Django stores inference results in its existing `AnomalyDetection` model.

## 8. Deferred production features

The following are deliberately deferred:

- immutable dataset APIs and lineage;
- readiness and automated 72-hour warm-up;
- durable training/inference job records;
- Redis-backed ML workers;
- a model registry, validation, activation, and rollback;
- object storage;
- automatic weekly retraining;
- detection correlation and ML-created incidents; and
- direct FastAPI access from Flutter.

They may be added later without changing the current rule that Django owns
application authorization and service lifecycle state.
