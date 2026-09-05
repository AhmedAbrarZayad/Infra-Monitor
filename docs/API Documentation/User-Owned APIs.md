# User-Owned APIs

## 1. Purpose

This is the project owner's end-to-end implementation backlog for automatic exporter installation and telemetry ingestion, ML training/inference, and Gemini chat. The canonical contracts and shared conventions remain in [Complete API Inventory](Complete%20API%20Inventory.md). All remaining platform APIs are assigned in [Agent-Owned APIs](Agent-Owned%20APIs.md).

Ownership includes the necessary Flutter-facing APIs, Django control-plane behavior, internal services/workers, gateway/realtime interfaces, persistence, and tests. `INTERNAL` describes a non-public service API, not an API called by an application user. The ML service boundary and data ownership are defined in [ML Service Architecture](../ML%20Architecture.md).

## 2. Exporter enrollment and telemetry

### 2.2 Installer and data-plane APIs

| Status | Method and path | Authentication | Deliverable |
| --- | --- | --- | --- |
| `INTERNAL` | `GET /api/monitoring/install.sh` | Public, rate-limited | Serve an immutable, versioned, signed Linux installer. |
| `INTERNAL` | `GET /api/monitoring/install.sh.sha256` | Public, rate-limited | Serve the checksum matching the installer response. |
| `INTERNAL` | `POST /api/internal/monitoring/enroll/` | Single-use enrollment token | Consume the token transactionally; create organization-owned server, hashed credential, and Alloy configuration. |
| `INTERNAL` | `POST /api/internal/monitoring/enrollments/{enrollment_id}/status/` | Server write credential | Persist bounded installer stages after credential/enrollment validation. |
| `INTERNAL` | `POST /api/metrics/write` | Server write credential | Accept `remote_write`, derive trusted tenant identity, overwrite edge identity, and route to VictoriaMetrics. |

### 2.3 Required background behavior

- Install Alloy with checksum/signature verification and a dedicated service user.
- Collect host metrics even without Docker; disclose Docker-socket privilege before enabling container monitoring.
- Collect cAdvisor resource metrics for accessible containers and separately discover labeled application `/metrics` endpoints.
- Create servers during enrollment and upsert services from stable discovered identities.
- Transition disappeared services to `OFFLINE`/`STALE`; never delete their telemetry or incident history.
- Authenticate ingestion by hashed server credential. Edge organization/server labels are untrusted and must be overwritten or validated.
- Keep Django in the control plane. A later vmauth/dedicated gateway routes data to `/insert/{account_id}:{project_id}/prometheus/api/v1/write`.
- Update enrollment connection state when the first valid metric batch arrives.

## 3. ML training, inference, and correlation

> **School-project scope:** The production-grade APIs previously planned in
> this section are deferred. The current implementation requires only FastAPI
> `POST /train`, FastAPI `POST /infer`, and Django
> `POST /api/internal/ml/detections/`, protected by a shared Bearer token.
> Flutter reads detections through the existing authenticated Django anomaly
> endpoints and never calls FastAPI. Dataset registries, readiness APIs, job
> registries, model activation, correlation, and automatic ML-created incidents
> are future work. See [Simple ML Backend Plan](../ML%20Backend%20Work%20Split.md).

The internal endpoints in this section are implemented by the FastAPI ML service,
not Django. Django triggers or composes ML work using authenticated
service-to-service calls. FastAPI and its workers query VictoriaMetrics directly
with trusted tenant mappings, keep durable ML metadata in an ML-owned PostgreSQL
schema/database, use Redis only for dispatch, and place model binaries in object
storage. They must never write Django-owned alert or incident tables directly.

### 3.1 Flutter-facing readiness APIs

| Status | Method and path | Permission | Deliverable |
| --- | --- | --- | --- |
| `MISSING` | `GET /api/organizations/{organization_id}/ml/readiness/` | Approved member | Organization/service progress, valid baseline duration, training state, active model, last inference, and next retraining. |
| `MISSING` | `GET /api/organizations/{organization_id}/services/{service_id}/ml/readiness/` | Approved member | Per-service readiness and explicit insufficiency reasons. |

### 3.2 Internal control APIs

| Status | Method and path | Authentication | Deliverable |
| --- | --- | --- | --- |
| `INTERNAL` | `POST /api/internal/ml/datasets/` | Django scheduler/ML operator | Persist an immutable tenant-scoped dataset definition, dispatch its VictoriaMetrics build, and return `202` with dataset UUID/version. No dataset payload passes through Django. |
| `INTERNAL` | `GET /api/internal/ml/datasets/{dataset_id}/` | Django/ML operator | Return durable build state, counts, validation, split boundaries, source-window lineage, and definition hash. |
| `INTERNAL` | `POST /api/internal/ml/training-jobs/` | Django scheduler/ML operator | Queue idempotent training for a completed dataset and versioned algorithm/configuration. |
| `INTERNAL` | `GET /api/internal/ml/training-jobs/?state=&page=` | ML service/operator | List training progress. |
| `INTERNAL` | `GET /api/internal/ml/training-jobs/{job_id}/` | ML service/operator | Return training state, metrics, artifact/model reference, and safe failure. |
| `INTERNAL` | `POST /api/internal/ml/training-jobs/{job_id}/cancel/` | ML service/operator | Cancel supported queued/running work. |
| `INTERNAL` | `GET /api/internal/ml/models/?state=&page=` | ML service/operator | List model versions, lineage, metrics, compatibility, and active state. |
| `INTERNAL` | `GET /api/internal/ml/models/{model_id}/` | ML service/operator | Return one model version's safe metadata. |
| `INTERNAL` | `POST /api/internal/ml/models/{model_id}/activate/` | ML operator | Atomically activate a validated compatible model. |
| `INTERNAL` | `POST /api/internal/ml/models/{model_id}/deactivate/` | ML operator | Stop new inference with a version while retaining lineage. |
| `INTERNAL` | `POST /api/internal/ml/inference-jobs/` | Django scheduler/ML service | Queue idempotent inference for a trusted organization/resource, active model, and completed metric window. |
| `INTERNAL` | `GET /api/internal/ml/inference-jobs/{job_id}/` | ML service/operator | Return model/window provenance, state, detections, and safe failure. |
| `INTERNAL` | `POST /api/internal/ml/correlation-jobs/` | Django scheduler/ML service | Queue correlation of bounded detections/alert references into idempotent incident candidates. |
| `INTERNAL` | `GET /api/internal/ml/correlation-jobs/{job_id}/` | Django/ML operator | Return candidate links, Django submission outcome, incident UUIDs, and conflicts. |

### 3.3 Fixed automatic lifecycle

- Detect service crashes/offline state with deterministic application `up`, container last-seen/health/restart/OOM/exit, and heartbeat rules; this path must not depend on ML readiness.
- Use Isolation Forest only for service-level container degradation/anomaly detection. An anomaly alone never changes lifecycle state to `OFFLINE`.
- Begin readiness accounting when a discovered service first supplies valid health metrics.
- Require 72 hours of usable baseline data before automatic first training.
- Start continuous inference only after a compatible model successfully validates and becomes active.
- Retrain every seven days by default while the previous active model continues inference.
- Never activate a failed or incompatible candidate.
- Preserve dataset, feature, model, and metric-window lineage for every detection.
- Build `container_iforest_v1` only from `cpu_r`, `mem_u`, `disk_r`, `disk_w`, `eth1_fi`, and `eth1_fo` series carrying trusted `service_id`; never substitute host metrics or zeros.
- Submit idempotent incident candidates through Django's authenticated internal incident boundary. Django revalidates tenant/resource ownership and uses the shared incident domain service; ML never writes incident tables.

The public anomaly list/detail endpoints are agent-owned consumers of the detections produced here.

## 4. Gemini anomaly assistant

### 4.1 HTTP APIs

| Status | Method and path | Permission | Deliverable |
| --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/assistant/context/?anomaly_id=` | Approved member | Return the latest 20 anomalous detections, selected six-feature evidence, lifecycle context, and prompts. |
| `EXISTING` | `POST /api/organizations/{organization_id}/assistant/conversations/` | Approved member | Create or resume the caller's single conversation for `anomaly_id`. |
| `EXISTING` | `GET /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/messages/?limit=` | Conversation owner | Return the canonical persisted transcript. |
| `EXISTING` | `POST /api/organizations/{organization_id}/assistant/websocket-tickets/` | Approved member, throttled | Return a hashed-at-rest, short-lived, single-use ticket bound to user, organization, and conversation. |
| `DEFERRED` | Incident analysis, general chat, multiple threads, and conversation deletion | — | Outside the school-project anomaly-assistant scope. |

### 4.2 WebSocket protocol

| Status | Socket path | Permission | Deliverable |
| --- | --- | --- | --- |
| `EXISTING` | `WS(S) /ws/organizations/{organization_id}/assistant/conversations/{conversation_id}/?ticket={ticket}` | Single-use ticket + conversation owner | Receive `user_message`; emit `message_ack`, `generation_started`, `token_delta`, `citation`, `generation_completed`, and safe `generation_error`. |

- Use HTTP for context, conversation management, and canonical history; use WebSocket only for live messages/generation.
- Persist a user message before `message_ack` and the complete assistant message before `generation_completed`.
- Deduplicate client retries by `client_message_id`.
- On reconnect, issue a new ticket and reload HTTP history rather than replaying the socket.
- Assemble Gemini context only from the authorized anomaly's stored six-feature window, score, model version, identity, timestamps, current lifecycle state, and latest 20 messages.
- Keep Gemini credentials, system prompts, raw provider errors, and unrestricted evidence server-side.
- Gemini is advisory and never creates incidents, changes lifecycle state, or confirms a crash from an anomaly.

## 5. Required handoffs to agent-owned APIs

- Enrollment must expose organization-owned servers/services and stable state for inventory, health, Overview, and Analytics reads.
- The telemetry query layer must return normalized bounded series to the agent-owned metric APIs without exposing internal tenant IDs.
- ML must persist model/version provenance and detections consumed by anomaly, evidence, alert, incident, and analytics APIs.
- Correlation must submit candidates to Django's authenticated tenant-safe incident boundary so manually and automatically managed incidents behave identically; only Django persists incidents.
- AI may consume the agent-owned evidence API/service but must independently recheck organization/conversation authorization.

## 6. Completion rule

Ownership is end to end: persistence, migrations, secure credentials, worker/gateway or Channels infrastructure, API/socket contracts, Flutter integration, tenant isolation, retries, failure states, and tests. Agent-owned endpoints must not be reimplemented or shadowed here.
