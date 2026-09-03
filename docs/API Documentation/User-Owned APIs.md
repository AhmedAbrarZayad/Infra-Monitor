# User-Owned APIs

## 1. Purpose

This is the project owner's end-to-end implementation backlog for automatic exporter installation and telemetry ingestion, ML training/inference, and Gemini chat. The canonical contracts and shared conventions remain in [Complete API Inventory](Complete%20API%20Inventory.md). All remaining platform APIs are assigned in [Agent-Owned APIs](Agent-Owned%20APIs.md).

Ownership includes the necessary Flutter-facing APIs, Django control-plane behavior, internal services/workers, gateway/realtime interfaces, persistence, and tests.

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

### 3.1 Flutter-facing readiness APIs

| Status | Method and path | Permission | Deliverable |
| --- | --- | --- | --- |
| `MISSING` | `GET /api/organizations/{organization_id}/ml/readiness/` | Approved member | Organization/service progress, valid baseline duration, training state, active model, last inference, and next retraining. |
| `MISSING` | `GET /api/organizations/{organization_id}/services/{service_id}/ml/readiness/` | Approved member | Per-service readiness and explicit insufficiency reasons. |

### 3.2 Internal control APIs

| Status | Method and path | Authentication | Deliverable |
| --- | --- | --- | --- |
| `INTERNAL` | `POST /api/internal/ml/datasets/` | ML service/operator | Create an immutable dataset definition and build. |
| `INTERNAL` | `GET /api/internal/ml/datasets/{dataset_id}/` | ML service/operator | Return state, counts, validation, split, and lineage. |
| `INTERNAL` | `POST /api/internal/ml/training-jobs/` | ML service/operator | Queue idempotent training for a dataset/configuration. |
| `INTERNAL` | `GET /api/internal/ml/training-jobs/?state=&page=` | ML service/operator | List training progress. |
| `INTERNAL` | `GET /api/internal/ml/training-jobs/{job_id}/` | ML service/operator | Return training state, metrics, artifact/model reference, and safe failure. |
| `INTERNAL` | `POST /api/internal/ml/training-jobs/{job_id}/cancel/` | ML service/operator | Cancel supported queued/running work. |
| `INTERNAL` | `GET /api/internal/ml/models/?state=&page=` | ML service/operator | List model versions, lineage, metrics, compatibility, and active state. |
| `INTERNAL` | `GET /api/internal/ml/models/{model_id}/` | ML service/operator | Return one model version's safe metadata. |
| `INTERNAL` | `POST /api/internal/ml/models/{model_id}/activate/` | ML operator | Atomically activate a validated compatible model. |
| `INTERNAL` | `POST /api/internal/ml/models/{model_id}/deactivate/` | ML operator | Stop new inference with a version while retaining lineage. |
| `INTERNAL` | `POST /api/internal/ml/inference-jobs/` | ML/telemetry service | Queue idempotent inference for an organization/resource/window. |
| `INTERNAL` | `GET /api/internal/ml/inference-jobs/{job_id}/` | ML service/operator | Return model/window provenance, state, detections, and safe failure. |
| `INTERNAL` | `POST /api/internal/ml/correlation-jobs/` | ML/incident service | Correlate detections/alerts into tenant-safe incidents. |
| `INTERNAL` | `GET /api/internal/ml/correlation-jobs/{job_id}/` | ML/incident service | Return links, created/updated incidents, and conflicts. |

### 3.3 Fixed automatic lifecycle

- Begin readiness accounting when a discovered service first supplies valid health metrics.
- Require 72 hours of usable baseline data before automatic first training.
- Start continuous inference only after a compatible model successfully validates and becomes active.
- Retrain every seven days by default while the previous active model continues inference.
- Never activate a failed or incompatible candidate.
- Preserve dataset, feature, model, and metric-window lineage for every detection.
- Use idempotent fingerprints and the shared incident domain service when creating alerts/incidents.

The public anomaly list/detail endpoints are agent-owned consumers of the detections produced here.

## 4. Gemini analyses and chat

### 4.1 HTTP APIs

| Status | Method and path | Permission | Deliverable |
| --- | --- | --- | --- |
| `MISSING` | `GET /api/organizations/{organization_id}/incidents/{incident_id}/analysis/` | Approved member | Latest safe analysis, confidence, causes, recommendations, findings, and provenance. |
| `MISSING` | `POST /api/organizations/{organization_id}/incidents/{incident_id}/analysis/` | Owner or admin | Queue an idempotent explicit analysis/refresh. |
| `MISSING` | `PATCH /api/organizations/{organization_id}/incidents/{incident_id}/recommendations/{recommendation_id}/` | Assignee, owner, or admin | Update recommendation completion state. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/context/?incident_id=` | Approved member | Authorized incident choices, evidence preview, and suggested prompts. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/conversations/?incident_id=&page=` | Approved member | List only the caller's organization-scoped conversations. |
| `MISSING` | `POST /api/organizations/{organization_id}/assistant/conversations/` | Approved member | Create a caller-owned conversation after incident validation. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/` | Conversation owner | Restore conversation metadata and incident context. |
| `MISSING` | `DELETE /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/` | Conversation owner | Delete/archive according to the selected retention policy. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/messages/?page=` | Conversation owner | Return the canonical persisted transcript and citations. |
| `MISSING` | `POST /api/organizations/{organization_id}/assistant/websocket-tickets/` | Approved member, throttled | Return a short-lived single-use ticket bound to user, organization, and conversation. |

### 4.2 WebSocket protocol

| Status | Socket path | Permission | Deliverable |
| --- | --- | --- | --- |
| `MISSING` | `WSS /ws/organizations/{organization_id}/assistant/conversations/{conversation_id}/?ticket={ticket}` | Single-use ticket + conversation owner | Receive `user_message`; emit `message_ack`, `generation_started`, `token_delta`, `citation`, `generation_completed`, and safe `generation_error`. |

- Use HTTP for context, conversation management, and canonical history; use WebSocket only for live messages/generation.
- Persist a user message before `message_ack` and the complete assistant message before `generation_completed`.
- Deduplicate client retries by `client_message_id`.
- On reconnect, issue a new ticket and reload HTTP history rather than replaying the socket.
- Assemble Gemini context only from organization-authorized incidents, logs, metrics, anomalies, analyses, and evidence.
- Keep Gemini credentials, system prompts, raw provider errors, and unrestricted evidence server-side.

## 5. Required handoffs to agent-owned APIs

- Enrollment must expose organization-owned servers/services and stable state for inventory, health, Overview, and Analytics reads.
- The telemetry query layer must return normalized bounded series to the agent-owned metric APIs without exposing internal tenant IDs.
- ML must persist model/version provenance and detections consumed by anomaly, evidence, alert, incident, and analytics APIs.
- Correlation must call the shared tenant-safe incident service so manually and automatically managed incidents behave identically.
- AI may consume the agent-owned evidence API/service but must independently recheck organization/conversation authorization.

## 6. Completion rule

Ownership is end to end: persistence, migrations, secure credentials, worker/gateway or Channels infrastructure, API/socket contracts, Flutter integration, tenant isolation, retries, failure states, and tests. Agent-owned endpoints must not be reimplemented or shadowed here.
