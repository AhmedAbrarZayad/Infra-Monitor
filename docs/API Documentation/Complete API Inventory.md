# Complete Platform API Inventory

## 1. Purpose

This document is the canonical inventory of HTTP APIs required by the current Flutter application and the planned Prometheus, anomaly-detection, incident, analytics, and Gemini workflows.

It is an evaluation document, not an implementation contract. Important inputs and outputs are listed so endpoints can be selected and implemented in coherent vertical slices. Exact serializers and complete JSON schemas should be defined when an endpoint is approved for implementation.

## 2. Status legend

| Status | Meaning |
| --- | --- |
| `EXISTING` | Registered in Django and currently callable. |
| `MISSING` | Required by a current app screen or core workflow but not implemented. |
| `INTERNAL` | Required for operators or service-to-service workflows; never called directly by Flutter. |
| `DEFERRED` | Useful later, but not required for the current UI or first complete pipeline. |
| `NON-HTTP` | A background/scheduled operation that should not become an application API. |

Having a Django model does not make an endpoint `EXISTING`. At the time of this audit, only authentication and organization routes are registered in `infra_monitor/urls.py`.

### 2.1 Implementation ownership

- **Agent-owned:** remaining platform APIs that Codex will implement. See [Agent-Owned APIs](Agent-Owned%20APIs.md).
- **User-owned:** exporter installation/telemetry ingestion, ML training/inference, and Gemini chat APIs that the project owner will implement end to end. See [User-Owned APIs](User-Owned%20APIs.md).
- `EXISTING` endpoints belong to neither implementation backlog. `DEFERRED` endpoints are also unassigned until promoted into scope.
- The companion documents are exhaustive ownership views of this canonical inventory. A `MISSING` or `INTERNAL` endpoint must appear in exactly one of them.

## 3. Shared API conventions

### 3.1 Paths, identifiers, and tenancy

- All application endpoints use the `/api/` prefix.
- Operational Flutter endpoints live below `/api/organizations/{organization_id}/`.
- `{organization_id}`, server, service, alert, incident, conversation, job, detection, and model identifiers are UUIDs unless an existing endpoint explicitly uses an integer user ID.
- The backend derives organization ownership from the scoped URL. Creation payloads must not be trusted to provide an organization ID.
- Every operational lookup starts from an approved membership. An object belonging to another organization returns `404`, even when its identifier exists.
- The active organization is a client-side selection validated against `/api/organizations/context/`; switching it does not require a backend endpoint.

### 3.2 Authentication and permissions

- Flutter APIs use `Authorization: Bearer <access-token>` except registration, verification, login, password recovery, liveness, and readiness.
- Verified email is required for organization creation, discovery, joining, and any future server registration.
- Operational reads require an approved organization membership.
- Operational writes are capability-based. `OWNER` and `ADMIN` manage infrastructure and incidents; `ENGINEER` may perform explicitly allowed incident actions. The exact permission is recorded per endpoint.
- Internal APIs require a separately configured service credential or workload identity, not a user JWT. They are network-restricted and must record the calling service.
- Gemini and Prometheus credentials remain server-side and are never returned to Flutter.

### 3.3 Collections and filtering

- Collections use DRF pagination: `count`, `next`, `previous`, and `results`.
- Standard query parameters are `page`, `page_size`, `ordering`, and `q` where applicable. Maximum page size must be bounded.
- Time-series endpoints accept ISO-8601 UTC `from` and `to`, plus a bounded `step` such as `1m`, `5m`, or `1h`.
- List filters use stable values such as `status`, `severity`, `environment`, `server_id`, `service_id`, and `assigned_to`.
- Timestamps are ISO-8601 UTC strings ending in `Z`. Display-oriented values such as “5 minutes ago” are calculated by Flutter.

### 3.4 Errors, conflicts, and idempotency

- Native DRF field-validation errors remain field keyed.
- Domain conflicts use `{"detail": "Description", "code": "stable_code"}`.
- `400` means invalid input or transition, `401` invalid authentication, `403` insufficient capability, `404` absent or cross-organization resource, `409` duplicate/stale operation, and `429` throttled.
- Retriable creation and trigger endpoints accept an `Idempotency-Key` header. Reusing a key with a different payload returns `409`.
- Search, join requests, enrollment creation, chat messages, training triggers, and inference triggers are throttled independently.

## 4. Flutter-facing APIs

### 4.1 Authentication, profile, and preferences

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `POST /api/auth/register/` | Public | Input account fields; creates an unverified user and starts email verification. | Registration screen; email delivery. |
| `EXISTING` | `POST /api/auth/verify-email/` | Public | Input email and OTP; verifies email and returns the established auth result. | Verification screen. |
| `EXISTING` | `POST /api/auth/resend-otp/` | Public, throttled | Input email; issues another verification OTP. | Verification screen; email delivery. |
| `EXISTING` | `POST /api/auth/login/` | Public | Input credentials; returns access/refresh tokens and user data. | Login and session bootstrap. |
| `EXISTING` | `POST /api/auth/logout/` | JWT | Input refresh token; blacklists it. | Sign-out flow. |
| `EXISTING` | `POST /api/auth/token/refresh/` | Refresh token | Input refresh token; returns a new access token. | Restored/expired sessions. |
| `EXISTING` | `POST /api/auth/forgot-password/` | Public, throttled | Input email; starts password reset without disclosing account existence. | Forgot-password screen. |
| `EXISTING` | `POST /api/auth/reset-password/` | Public | Input email, OTP, and new password; resets credentials. | Reset-password screen. |
| `EXISTING` | `GET /api/auth/me/` | JWT | Returns `id`, username, email, names, legacy global role, verification state, and creation time. Membership role must come from organization context, not the legacy role. | Navbar and More profile. |
| `EXISTING` | `GET /api/auth/me/preferences/` | JWT | Returns notification setting, refresh interval, timezone, theme, default environment, and optional stream-display preference. | More preferences; existing `UserPreference` only covers some fields. |
| `EXISTING` | `PATCH /api/auth/me/preferences/` | JWT | Partially updates validated preference fields and returns the complete preference object. | More preferences; requires deciding whether UI-only theme/stream/environment settings remain local or become persisted fields. |

### 4.2 Organization context and membership

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/context/` | JWT | Returns approved memberships, pending memberships, `can_create_organization`, and recommended organization UUID. | Post-auth routing, startup, More switcher. |
| `EXISTING` | `GET /api/organizations/search/?q=&page=` | JWT + verified email, throttled | Paginated public metadata: UUID, name, summary, logo. | Join search. Flutter must compare IDs with context because the current response has no membership flag. |
| `EXISTING` | `POST /api/organizations/` | JWT + verified email | Input name, summary, optional logo URL; atomically returns organization and approved `OWNER` membership. | Onboarding and More create action. |
| `EXISTING` | `GET /api/organizations/{organization_id}/` | Approved member | Returns member-visible organization details. | Active organization card. |
| `EXISTING` | `POST /api/organizations/{organization_id}/memberships/` | JWT + verified email, throttled | Creates a pending `ENGINEER` membership; duplicate/stale requests conflict. | Join action. |
| `EXISTING` | `GET /api/organizations/{organization_id}/memberships/?approved=false` | Owner or admin | Paginated pending requests. | Future membership administration. |
| `EXISTING` | `POST /api/organizations/{organization_id}/memberships/{membership_id}/approve/` | Owner or admin | Transactionally approves a pending membership. | Future membership administration. |
| `EXISTING` | `DELETE /api/organizations/{organization_id}/memberships/{membership_id}/reject/` | Owner or admin | Deletes a pending membership; stale decisions conflict. | Future membership administration. |
| `EXISTING` | `GET /api/organizations/{organization_id}/members/` | Approved member | Paginated approved memberships with user identity and membership role. | More member list and incident assignee choices. |
| `EXISTING` | `PATCH /api/organizations/{organization_id}/members/{user_id}/role/` | Owner | Input `ADMIN` or `ENGINEER`; cannot change the owner. | Future membership administration. |
| `EXISTING` | `DELETE /api/organizations/{organization_id}/members/{user_id}/` | Owner, or admin targeting engineer | Removes membership and immediately revokes organization access. | Future membership administration. |
| `DEFERRED` | `DELETE /api/organizations/{organization_id}/memberships/me/` | Approved non-owner member | Leaves an organization. Must reject owner departure until transfer/deletion exists. | No current UI action. |
| `DEFERRED` | `PATCH /api/organizations/{organization_id}/` | Owner | Updates name, summary, or logo URL. | No current edit UI. |

There is deliberately no “switch organization” API. Flutter persists the selected approved organization UUID and validates it whenever context is refreshed.

### 4.3 Overview

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/overview/?environment=` | Approved member | Returns `server_count`, `open_incident_count`, `updated_at`, fleet status counts, critical/high incident summaries, attention items, recent alerts, and platform-health items in one consistent snapshot. | Overview page; depends on tenant-scoped servers, metrics, alerts, incidents, and pipeline-health data. |

The overview is intentionally one aggregate endpoint. Separate server, alert, and incident endpoints remain the sources for drill-down screens, but making the mobile client assemble the dashboard would cause inconsistent timestamps and excessive requests.

### 4.4 Servers, services, and metrics

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/servers/?q=&status=&environment=&usage_above=&page=` | Approved member | Paginated server cards with UUID, name/host, environment, status, active-alert count, latest CPU/memory/disk, last seen, uptime, and compact CPU history. | Servers page. Requires `Servers.organization`. |
| `EXISTING` | `GET /api/organizations/{organization_id}/servers/{server_id}/` | Approved member | Returns inventory metadata, latest health, resource summary, and scrape state. | Server detail/drill-down. |
| `EXISTING` | `PATCH /api/organizations/{organization_id}/servers/{server_id}/` | Owner or admin | Updates display name, environment, and other safe metadata; never changes organization, credential, or collector configuration. | Server administration; monitoring configuration is user-owned. |
| `EXISTING` | `GET /api/organizations/{organization_id}/servers/{server_id}/health/` | Approved member | Returns current status, last heartbeat/scrape, uptime, latest CPU/memory/disk, and active alert summary. | Server detail and targeted refresh. |
| `EXISTING` | `GET /api/organizations/{organization_id}/servers/{server_id}/metrics/?metric=&from=&to=&step=` | Approved member | Returns normalized time-series points, unit, labels, interval, and completeness metadata. | Server charts; backed by Prometheus or persisted aggregates. |
| `EXISTING` | `GET /api/organizations/{organization_id}/servers/{server_id}/services/?status=&page=` | Approved member | Lists services on a server with UUID, name/display name, port, status, and last report time. | Server/service drill-down. |
| `EXISTING` | `GET /api/organizations/{organization_id}/services/{service_id}/` | Approved member | Returns service metadata, parent server, current health, and alert count. | Incident and server drill-down. |
| `EXISTING` | `PATCH /api/organizations/{organization_id}/services/{service_id}/` | Owner or admin | Updates display name and safe metadata; never changes discovered identity or tenant ownership. | Service administration. |
| `EXISTING` | `GET /api/organizations/{organization_id}/services/{service_id}/health/` | Approved member | Returns status, last report, latency/error/resource summary, and active alerts. | Service drill-down and incident evidence. |
| `EXISTING` | `GET /api/organizations/{organization_id}/services/{service_id}/metrics/?metric=&from=&to=&step=` | Approved member | Returns normalized service time series. | Service charts, analytics, AI evidence. |

Servers and services are created by the user-owned enrollment/discovery pipeline, not generic CRUD endpoints. When telemetry stops, records remain addressable and transition to `OFFLINE` or `STALE`; historical metrics and incident evidence are retained. Current blockers: `Servers` has no organization foreign key, while `Service` and `Metrics` inherit scope through server. UUID defaults and timestamp/nullability across these early models also require an audit before writes can safely operate.

### 4.5 Alerts

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/alerts/?q=&state=&severity=&server_id=&service_id=&from=&to=&page=` | Approved member | Paginated alert summaries with source resource, category, severity, state, fingerprint, detection reference, and lifecycle timestamps. | Overview latest-alert feed and alert drill-down. |
| `EXISTING` | `GET /api/organizations/{organization_id}/alerts/{alert_id}/` | Approved member | Returns full description, labels/evidence, source resource, linked detection, linked incidents, and lifecycle. | Incident evidence and alert detail. |
| `EXISTING` | `POST /api/organizations/{organization_id}/alerts/{alert_id}/acknowledge/` | Approved member | Idempotently acknowledges an active alert and records actor/time. | Future alert action. Current `Alert` lacks actor storage. |
| `EXISTING` | `POST /api/organizations/{organization_id}/alerts/{alert_id}/resolve/` | Owner or admin | Resolves/clears an alert with optional note when an operator override is allowed. | Future alert action; automatic Prometheus recovery remains internal. |

Current blocker: an alert may have null server/service references and has no direct organization field. It needs immutable tenant ownership before any organization-scoped endpoint is exposed.

### 4.6 Logs and evidence

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/logs/?q=&level=&source=&server_id=&service_id=&from=&to=&page=` | Approved member | Paginated log search with timestamp, level, source, message, safe metadata, server, and service. | Incident investigation and Gemini context. |
| `EXISTING` | `GET /api/organizations/{organization_id}/logs/{log_id}/` | Approved member | Returns one complete sanitized log record and resource links. | Evidence drill-down. |
| `EXISTING` | `GET /api/organizations/{organization_id}/incidents/{incident_id}/evidence/` | Approved member | Aggregates linked alerts, anomaly windows, relevant metric excerpts, logs, and AI log findings with provenance. | Incident detail and AI assistant context. |

Current blocker: logs can exist without server/service and have no direct organization field. Add immutable tenant ownership before exposing them. Secrets and personal data must be redacted during ingestion, not only at response time.

### 4.7 Incidents

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/incidents/?q=&severity=&status=&environment=&assigned_to=&acknowledged=&page=` | Approved member | Paginated incident cards with code/UUID, severity, status, title, server/service/environment, detected age source, assignee, acknowledgement, and latest AI confidence. | Incidents and Overview pages. |
| `EXISTING` | `GET /api/organizations/{organization_id}/incidents/{incident_id}/` | Approved member | Returns description, category, lifecycle timestamps, resolution, assignee, resource links, alert count, and latest analysis summary. | Incident detail and AI context. |
| `EXISTING` | `POST /api/organizations/{organization_id}/incidents/{incident_id}/acknowledge/` | Approved member | Idempotently records acknowledgement and an incident update. | Incident action. |
| `EXISTING` | `POST /api/organizations/{organization_id}/incidents/bulk-acknowledge/` | Approved member | Input explicit incident UUIDs or validated filter; acknowledges visible matching incidents and returns success/conflict counts. | “Acknowledge all critical”; idempotency required. |
| `EXISTING` | `PATCH /api/organizations/{organization_id}/incidents/{incident_id}/assignment/` | Owner or admin | Input approved member user ID or `null`; validates same-organization membership and records update. | Assignment administration. |
| `EXISTING` | `POST /api/organizations/{organization_id}/incidents/{incident_id}/assign-to-me/` | Approved member | Assigns the caller when self-assignment is permitted and records update. | Current “Assign to me” action. |
| `EXISTING` | `PATCH /api/organizations/{organization_id}/incidents/{incident_id}/status/` | Assignee, owner, or admin | Input target status and optional resolution note; enforces transition vocabulary and timestamps. | Incident workflow. |
| `EXISTING` | `GET /api/organizations/{organization_id}/incidents/{incident_id}/updates/?page=` | Approved member | Paginated status, assignment, acknowledgement, and comment history. | Incident audit/timeline. |
| `EXISTING` | `POST /api/organizations/{organization_id}/incidents/{incident_id}/feedback/` | Assignee, owner, or admin | Adds investigation/resolution feedback and records actor/time. | Incident workflow and future model feedback. |
| `EXISTING` | `GET /api/organizations/{organization_id}/incidents/{incident_id}/alerts/?page=` | Approved member | Lists alerts linked through `IncidentAlert`. | Incident evidence. |

Current blockers: incidents lack a direct organization field and can lose inferred tenancy when the server is null. The status vocabulary, transition matrix, nullable lifecycle timestamps, assignment capabilities, and unique incident-code scope must be finalized during implementation.

### 4.8 Analytics

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/organizations/{organization_id}/analytics/?range=&environment=&step=` | Approved member | One dashboard snapshot containing MTTA, MTTR, open and recently resolved counts; CPU/memory/latency series; incident frequency/opened/resolved; uptime; category/server breakdowns; and generated insight strings. | Analytics page; depends on scoped telemetry and incident data. |
| `DEFERRED` | `GET /api/organizations/{organization_id}/analytics/export/?range=&format=` | Owner or admin | Streams a CSV/JSON export from the same authorized aggregate definitions. | No current UI. |

The aggregate endpoint is the v1 choice because the current page renders all panels together. More granular analytics endpoints should be introduced only if independent refresh or materially different retention requires them.

### 4.9 AI analyses and Gemini assistant

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `MISSING` | `GET /api/organizations/{organization_id}/incidents/{incident_id}/analysis/` | Approved member | Returns latest summary, explanation, confidence, ranked root causes, recommendations, findings, generation time, and model/provider metadata safe for display. | Incident detail and assistant context. |
| `MISSING` | `POST /api/organizations/{organization_id}/incidents/{incident_id}/analysis/` | Owner or admin | Enqueues or refreshes an analysis and returns `202` with job/reference state; idempotency prevents duplicate work. | Future explicit re-analysis action; automatic analysis remains internal. |
| `MISSING` | `PATCH /api/organizations/{organization_id}/incidents/{incident_id}/recommendations/{recommendation_id}/` | Assignee, owner, or admin | Input completion state; returns updated recommendation. | Future recommendation checklist. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/context/?incident_id=` | Approved member | Returns selectable incident summaries, selected title, authorized evidence preview, and suggested prompts. | Current AI Assistant page. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/conversations/?incident_id=&page=` | Approved member | Lists only the caller’s conversations with title, incident reference, and timestamps. | Conversation history. |
| `MISSING` | `POST /api/organizations/{organization_id}/assistant/conversations/` | Approved member | Input optional incident UUID/title; creates a caller-owned conversation after tenant validation. | Start chat. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/` | Conversation owner | Returns conversation metadata and incident context. | Restore chat. |
| `MISSING` | `DELETE /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/` | Conversation owner | Deletes or archives conversation history according to retention policy. | Future history management. |
| `MISSING` | `GET /api/organizations/{organization_id}/assistant/conversations/{conversation_id}/messages/?page=` | Conversation owner | Paginated user/assistant messages, safe evidence citations, and timestamps. | Chat history. |
| `MISSING` | `POST /api/organizations/{organization_id}/assistant/websocket-tickets/` | Approved member, throttled | Input conversation UUID; returns a single-use, short-lived ticket bound to user, organization, and conversation. | Authenticates Flutter Web and mobile socket connections without putting a JWT in the URL. |

#### WebSocket contract

| Status | Socket path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `MISSING` | `WSS /ws/organizations/{organization_id}/assistant/conversations/{conversation_id}/?ticket={ticket}` | Single-use socket ticket + conversation owner | Bidirectional Gemini chat. Client sends `user_message` with `client_message_id` and text. Server emits `message_ack`, `generation_started`, `token_delta`, `citation`, `generation_completed`, and safe `generation_error` events. | AI Assistant live chat; Django Channels/ASGI and a channel layer are required. |

User and completed assistant messages are persisted before acknowledgement/completion. After reconnect, Flutter obtains a new ticket and recovers the canonical transcript through the HTTP messages endpoint; it does not request replay over the socket. Gemini is an implementation detail. Prompts and citations must be assembled only from organization-filtered incidents, logs, metrics, analyses, and evidence. The current AI models lack direct organization ownership; conversation scoping must be guaranteed through an immutable organization relation and validated incident parent before chat is exposed.

## 5. Internal service APIs

These endpoints are for operations, workers, and controlled development tooling. They are not added to Flutter repositories.

### 5.1 Exporter enrollment and telemetry ingestion

#### Flutter/control-plane APIs

| Status | Method and path | Authorization | Purpose and key contract | Dependency |
| --- | --- | --- | --- | --- |
| `MISSING` | `POST /api/organizations/{organization_id}/monitoring/enrollments/` | Owner or admin + verified email | Input server display name, environment, and safe installation options; returns enrollment UUID, single-use token, expiry, and generated install command. | Enrollment persistence and secure token hashing. |
| `MISSING` | `GET /api/organizations/{organization_id}/monitoring/enrollments/?state=&page=` | Owner or admin | Lists pending, connected, expired, cancelled, and failed enrollments without returning token or permanent credential material. | Connect-infrastructure UI and recovery. |
| `EXISTING` | `GET /api/organizations/{organization_id}/monitoring/enrollments/{enrollment_id}/` | Owner or admin | Polls coarse installer stage, expiry, server UUID, first-metric state, sanitized failure, and connection state; cross-organization IDs return `404`. | Flutter connection progress. |
| `EXISTING` | `DELETE /api/organizations/{organization_id}/monitoring/enrollments/{enrollment_id}/` | Owner or admin | Soft-cancels an incomplete enrollment, invalidates its token, and revokes partially issued credentials; connected/expired cancellation conflicts. | Flutter cancel action. |
| `EXISTING` | `GET /api/organizations/{organization_id}/servers/{server_id}/monitoring/` | Approved member | Returns sanitized connection method, collector/version, credential state, last metric, last callback, and connection health, including `UNCONFIGURED`. | Server monitoring settings/status. |
| `EXISTING` | `POST /api/organizations/{organization_id}/servers/{server_id}/monitoring/credentials/rotate/` | Owner or admin | Requires `Idempotency-Key`, returns the replacement credential once, and retains prior credentials for a configurable 15-minute grace period. Replays return `409`. | Credential rotation UI. |
| `EXISTING` | `DELETE /api/organizations/{organization_id}/servers/{server_id}/monitoring/` | Owner or admin | Idempotently revokes ingestion, marks monitoring disconnected/server offline, and retains all history. | Disconnect monitoring action. |

#### Installer and data-plane APIs

| Status | Method and path | Authorization | Purpose and key contract | Dependency |
| --- | --- | --- | --- | --- |
| `INTERNAL` | `GET /api/monitoring/install.sh` | Public, rate-limited | Returns the versioned Linux installer; production releases are signed and immutable. | Installer distribution/CDN. |
| `INTERNAL` | `GET /api/monitoring/install.sh.sha256` | Public, rate-limited | Returns the checksum for the exact installer release. | Supply-chain verification. |
| `INTERNAL` | `POST /api/internal/monitoring/enroll/` | Single-use enrollment token | Transactionally consumes the token, derives organization ownership, creates the server and scoped write credential, and returns server UUID, ingestion URL, and Alloy configuration. | Organization-owned server, hashed credential, generated HCL. |
| `INTERNAL` | `POST /api/internal/monitoring/enrollments/{enrollment_id}/status/` | Server write credential | Accepts bounded installer stages and sanitized errors only when credential and enrollment server match. | Flutter polling state; metric arrival remains authoritative. |
| `INTERNAL` | `POST /api/metrics/write` | Server write credential | Accepts Prometheus `remote_write`; the gateway resolves the trusted tenant from the credential, overwrites identity labels, and routes to `/insert/{account_id}:{project_id}/prometheus/api/v1/write`. | Later VictoriaMetrics cluster plus vmauth/dedicated gateway; Django is not the payload proxy. |

Enrollment automatically creates servers. Alloy host/cAdvisor telemetry and labeled application endpoints automatically upsert services using stable discovered identity. Docker is optional for host monitoring. Missing containers transition to `OFFLINE`/`STALE` rather than being deleted. The current repository still uses central Prometheus; VictoriaMetrics cluster and vmauth are proposed later dependencies, not existing components.

### 5.2 ML training, models, inference, and correlation

| Status | Method and path | Authorization | Purpose and key contract | Dependency |
| --- | --- | --- | --- | --- |
| `MISSING` | `GET /api/organizations/{organization_id}/ml/readiness/` | Approved member | Returns organization/service collection progress, valid-data duration, 72-hour warm-up target, first-training state, active model, last inference, and next weekly retraining time. | Flutter learning/readiness states. |
| `MISSING` | `GET /api/organizations/{organization_id}/services/{service_id}/ml/readiness/` | Approved member | Returns the same lifecycle for one service plus insufficiency reasons such as gaps or unsupported metrics. | Service detail and troubleshooting. |
| `INTERNAL` | `POST /api/internal/ml/datasets/` | ML service/operator | Defines a reproducible dataset from organization scope, metric selectors, time range, labels, and split policy; returns dataset UUID/version. | Dataset/version storage is absent. |
| `INTERNAL` | `GET /api/internal/ml/datasets/{dataset_id}/` | ML service/operator | Returns immutable definition, build state, counts, lineage, and validation report. | Durable dataset metadata. |
| `INTERNAL` | `POST /api/internal/ml/training-jobs/` | ML service/operator | Input dataset, algorithm/config, and idempotency key; queues training and returns job UUID. | Worker queue, artifact storage, job model. |
| `INTERNAL` | `GET /api/internal/ml/training-jobs/?state=&page=` | ML service/operator | Lists training jobs and concise progress. | Durable job model. |
| `INTERNAL` | `GET /api/internal/ml/training-jobs/{job_id}/` | ML service/operator | Returns state, progress, metrics, artifact/model reference, timestamps, and sanitized failure. | Worker/job state. |
| `INTERNAL` | `POST /api/internal/ml/training-jobs/{job_id}/cancel/` | ML service/operator | Cancels a queued/running job when supported. | Worker cancellation semantics. |
| `INTERNAL` | `GET /api/internal/ml/models/?state=&page=` | ML service/operator | Lists model versions, lineage, evaluation metrics, active state, and compatibility metadata. | No current model registry schema. |
| `INTERNAL` | `GET /api/internal/ml/models/{model_id}/` | ML service/operator | Returns one model version’s metadata, not raw secrets or unrestricted artifact paths. | Model registry/artifact storage. |
| `INTERNAL` | `POST /api/internal/ml/models/{model_id}/activate/` | ML operator | Atomically activates a compatible version and records previous version. | Activation/rollback policy. |
| `INTERNAL` | `POST /api/internal/ml/models/{model_id}/deactivate/` | ML operator | Stops new inference using a version while retaining lineage. | Safe fallback policy. |
| `INTERNAL` | `POST /api/internal/ml/inference-jobs/` | ML/telemetry service | Input model or active alias, organization/resource scope, and metric window; queues inference. | Model registry, feature parity, job storage. |
| `INTERNAL` | `GET /api/internal/ml/inference-jobs/{job_id}/` | ML service/operator | Returns progress, model version, input window, detection IDs, and failure state. | Durable inference jobs. |
| `INTERNAL` | `POST /api/internal/ml/correlation-jobs/` | ML/incident service | Correlates selected detections/alerts into organization incidents and returns job state. | Correlation rules, tenant-safe incident creation. |
| `INTERNAL` | `GET /api/internal/ml/correlation-jobs/{job_id}/` | ML/incident service | Returns linked detections, alerts, created/updated incidents, and conflicts. | Durable correlation jobs. |
| `EXISTING` | `GET /api/organizations/{organization_id}/anomalies/?server_id=&service_id=&is_anomaly=&from=&to=&page=` | Approved member | Exposes authorized detection results with score, confidence, feature summary, model version, and window. | Future anomaly drill-down; current `AnomalyDetection` lacks organization/model version. |
| `EXISTING` | `GET /api/organizations/{organization_id}/anomalies/{detection_id}/` | Approved member | Returns one detection, feature contributions, linked alert/incident, and provenance. | Future evidence UI. |

The default lifecycle starts when a discovered service first supplies valid health metrics. It requires 72 hours of usable baseline data before the first automatic training job. Inference starts only after a compatible model completes validation and becomes active, then runs continuously on completed metric windows. Retraining runs every seven days by default while the current active model continues serving inference; a failed candidate never replaces it. Dataset creation, initial training, scheduled retraining, automatic inference, and correlation are background workflows that use the same durable job records exposed above.

The existing `AnomalyDetection` model stores scores and feature values but not training jobs, datasets, model versions, artifacts, inference jobs, model readiness, or direct organization ownership. Those are implementation blockers, not implicit APIs.

### 5.3 Supporting ingestion

| Status | Method and path | Authorization | Purpose and key contract | Dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `POST /api/internal/logs/batches/` | Approved log collector | Accepts bounded, sanitized log batches with immutable organization/server/service provenance and idempotency identity. | Log collector, redaction, and direct log tenancy. |

## 6. Operational health APIs

| Status | Method and path | Permission | Purpose and key contract | Consumer / dependency |
| --- | --- | --- | --- | --- |
| `EXISTING` | `GET /api/health/live/` | Public, network/rate restricted | Returns success when the web process is alive; does not query dependencies. | Container/orchestrator liveness probe. |
| `EXISTING` | `GET /api/health/ready/` | Public or infrastructure-only | Returns readiness and a generic failure when required dependencies are unavailable. | Load balancer/readiness probe. |
| `EXISTING` | `GET /api/internal/health/dependencies/` | Operator/service | Detailed PostgreSQL, cache/queue, Prometheus, artifact store, Gemini, email, and worker status with no credentials. | Operations diagnostics. |
| `EXISTING` | `GET /api/internal/health/workers/` | Operator/service | Worker heartbeat, queue depth, oldest job age, and last successful telemetry/training/inference/correlation run. | Requires durable worker heartbeat/job telemetry. |

## 7. Workflows that should not be HTTP APIs

| Status | Operation | Reason and observable interface |
| --- | --- | --- |
| `NON-HTTP` | Alloy host/container/application collection | The enrolled collector discovers and sends telemetry continuously; its installation and connection state are observable through enrollment/monitoring APIs. |
| `NON-HTTP` | Credential-based tenant routing and metric normalization | The ingestion data plane overwrites trusted identity, routes to VictoriaMetrics, and performs rollups without involving Flutter or Django request handlers. |
| `NON-HTTP` | Initial dataset and model training | Begins automatically after each service accumulates 72 hours of valid health metrics and creates durable dataset/training records. |
| `NON-HTTP` | Weekly model retraining | Creates a candidate every seven days while the active model remains available; promotes only a successfully validated candidate. |
| `NON-HTTP` | Continuous inference on completed windows | Begins only after first-model activation. Detection results are exposed through anomaly/evidence APIs. |
| `NON-HTTP` | Alert lifecycle evaluation | Prometheus/Alertmanager and workers create/update tenant-owned alerts. Manual override endpoints remain explicit. |
| `NON-HTTP` | Detection/alert incident correlation | Worker operation with idempotent fingerprints. Internal job endpoints exist for replay and diagnosis. |
| `NON-HTTP` | Automatic incident analysis | Triggered by incident creation/material evidence changes. The client reads results; explicit refresh is optional. |
| `NON-HTTP` | Gemini prompt construction and safety filtering | Backend-only execution inside a chat/analysis job. Prompts, API keys, and unrestricted raw evidence never reach Flutter. |

## 8. Current Flutter coverage map

| Current surface/action | Required API |
| --- | --- |
| Login, registration, verification, password reset, restored session | Existing `/api/auth/*` endpoints and `/api/auth/me/` |
| Navbar identity and role | `/api/auth/me/` for identity; active membership from `/api/organizations/context/` for `OWNER`/`ADMIN`/`ENGINEER` |
| Organization onboarding, pending gate, create, join, switch | Existing organization context/search/create/join APIs; switching remains local |
| More organization card, pending list, member list | Existing context and member APIs |
| More preferences | Missing `/api/auth/me/preferences/` read/update APIs, unless selected settings remain local |
| Connect-infrastructure installation and progress | Missing enrollment create/list/detail/cancel, installer, callback, and monitoring-status APIs |
| Credential rotation and disconnect | Missing organization-scoped server monitoring actions |
| Overview counters, fleet, incidents, attention, alerts, platform health | Missing organization overview aggregate |
| Server search, filters, cards, utilization and sparkline | Missing organization server collection and metric summaries |
| Incident search, filters, cards | Missing incident collection |
| “Acknowledge all critical” | Missing bulk incident acknowledgement |
| “Assign to me” | Missing self-assignment endpoint |
| Analytics metrics and charts | Missing analytics aggregate |
| AI incident selector, evidence and suggested prompts | Missing assistant context and incident evidence APIs |
| ML warm-up/training visibility | Missing organization/service ML readiness APIs |
| AI prompt send and streamed response | Missing conversation/history, WebSocket-ticket, and organization-scoped chat socket contracts |

The operational frontend data sources currently return hard-coded data. No registered operational backend endpoint is available to replace them yet.

## 9. Data and architecture blockers

Before organization-scoped operational APIs are exposed:

1. Add required organization ownership to `Servers`.
2. Add direct immutable organization ownership to nullable-root records such as alerts, incidents, logs, and anomaly detections; a null server must never imply global access.
3. Audit early UUID fields for automatic generation and early lifecycle timestamps for correct nullability/server management.
4. Define stable status/severity/environment vocabularies shared by serializers, Prometheus normalization, ML features, and Flutter.
5. Add durable schemas for enrollments, hashed server credentials, VictoriaMetrics tenant mappings, training/inference/correlation jobs, dataset lineage, model registry/versioning, readiness, and worker health.
6. Guarantee AI conversation tenancy and define retention/deletion policy before Gemini chat is exposed.
7. Keep the current Prometheus development stack operational while treating VictoriaMetrics cluster plus vmauth/dedicated ingestion gateway as a later data-plane dependency.

These changes are not part of this inventory task.

## 10. Recommended implementation sequence

1. **Tenant foundation and operational reads:** add tenant ownership and invariants, then implement servers, services, metrics, alerts, logs, incidents, and evidence reads.
2. **Operational actions and dashboards:** implement incident/alert actions, Overview, and Analytics using the same scoped query services.
3. **Exporter enrollment and ingestion (user-owned):** build installation, enrollment, credentials, edge-push collection, trusted tenant routing, discovery, and connection reporting.
4. **ML pipeline (user-owned):** introduce 72-hour readiness, dataset/model/job lineage, weekly retraining, activation, continuous inference, and idempotent incident correlation.
5. **Gemini workflows (user-owned):** implement incident analysis, evidence-safe context, conversations, persisted messages, WebSocket tickets, streamed socket events, and HTTP reconnect recovery.
6. **Remaining account/administration work:** decide preference persistence, then add preferences and deferred organization/infrastructure management only where the product needs them.

Every slice should include cross-organization isolation tests, permission-matrix tests, conflict/idempotency tests, serializer tests, and matching Flutter repository/parsing/state tests before replacing its dummy data source.

## 11. Audit result

- Registered application endpoints after this implementation: **57** total: 19 pre-existing authentication/organization endpoints and 38 agent-owned operational/internal endpoints.
- Registered servers, services, metrics, alerts, logs, incidents, analytics, ML, AI, telemetry, or health endpoints: **0**.
- Backend models exist for servers, services, metrics, alerts, logs, incidents/updates/links, anomaly detections, analyses/root causes/recommendations/findings, and assistant conversations/messages.
- The existing models do not yet provide sufficient tenant isolation or job/model lineage for all proposed APIs.
- Every current Flutter screen and action is mapped above; operational screens remain backed by dummy sources until selected API slices are implemented.
