# Request Shield Production Integration Plan

## 1. Purpose

This document defines the work required to turn the existing `sanitize` Django
app, presented as **Request Shield** in Flutter, into a complete production
feature that analyzes HTTP access traffic from services monitored by
Infra-Monitor.

The target design uses one shared, versioned machine-learning model. Model
training is an offline release activity. Production request processing performs
inference only; it must never train a model as part of ingestion, application
startup, or a Celery classification cycle.

This plan is based on the current repository. It extends rather than replaces:

- `backend/sanitize/`
- `model/app/pipeline/request_classifier.py`
- `backend/installer/`
- `frontend/lib/features/request_shield/`
- `scripts/sanitize-e2e.ps1`

## 2. Current state and confirmed gaps

### 2.1 Already implemented

- Django stores external and platform `RequestLog` records.
- Ingestion eagerly extracts a fixed 26-value feature vector and readable threat
  signals.
- Celery periodically sends unclassified vectors to the private ML service.
- The ML service lazily loads `request_shield/model.joblib` and performs batch
  inference.
- Results are stored as `GREEN`, `GRAY`, or `RED` with confidence and classifier
  metadata.
- Optional Gemini escalation exists for ML-classified gray requests.
- Threshold-based threat suggestions and organization APIs exist.
- Flutter has a Request Shield dashboard and review actions.
- Django middleware captures organization-scoped traffic to Infra-Monitor itself.
- The Docker smoke test validates internal ingestion, model classification, and
  suggestion generation using synthetic data.

### 2.2 Missing or incomplete

- The normal enrollment-generated Alloy configuration sends metrics only.
- No installed component currently converts real service access logs into the
  JSON accepted by `POST /api/internal/request-logs/`.
- `scripts/alloy_request_shield.alloy` is a reference only. `loki.write` sends
  Loki protocol payloads, not the custom Django batch schema, and the snippet
  uses `Token` while the endpoint requires `Bearer` authentication.
- External request logs are linked to a server but not a specific `Service`.
- Docker stdout access logs and configurable host files are not integrated.
- The initial model workflow derives HTTP-like features from CICIDS2017 network
  flows; this must not be treated as sufficient production validation.
- The ML endpoint does not strictly reject incompatible feature names/order.
- Deployment does not guarantee that a validated baseline Request Shield model
  exists before workers begin classification.
- `ShieldConfig.enabled` and `platform_self_monitor` are not consistently
  enforced across capture, ingestion, classification, and suggestions.
- Dashboard source filtering is not consistently applied to all analytics, and
  the zone-filter state must be wired into the request-list provider argument.
- The UI has providers for configuration but no complete administrator settings
  experience.
- The local WSL lab does not prove service request -> collection -> ingestion ->
  classification -> dashboard behavior.

## 3. Scope

### In scope

- A single shared Request Shield model artifact used across organizations,
  servers, and services.
- Offline model training, evaluation, versioning, packaging, deployment, and
  rollback.
- HTTP access-event collection from WSL/Linux services, including services in
  Docker.
- Secure, tenant-bound batch ingestion with server and service attribution.
- Asynchronous inference, retries, observability, retention, and redaction.
- Request Shield API and Flutter integration.
- Unit, integration, Docker, and real WSL end-to-end verification.

### Out of scope for the first release

- Automatic firewall changes, IP bans, or request blocking.
- Training a separate model per service, server, or organization.
- Sending every request to Gemini.
- Treating arbitrary application logs or stack traces as HTTP access events.
- Replacing the existing metrics pipeline.
- Online or automatic production retraining.

## 4. Required architecture

```text
HTTP service / reverse proxy
    -> structured access event
    -> Infra-Monitor access-log forwarder
    -> authenticated batch ingestion API
    -> validation, redaction, deduplication and feature extraction
    -> RequestLog in PostgreSQL (UNCLASSIFIED)
    -> Celery classification task
    -> private ML service with saved shared artifact
    -> GREEN / GRAY / RED result
    -> optional Gemini review for selected GRAY entries
    -> analytics, suggestions and administrator review in Flutter
```

HTTP request metadata is the input to this feature. General application logs
must remain in a separate log pipeline unless a producer can explicitly emit the
canonical access-event schema.

## 5. Architectural decisions

### 5.1 One shared model

Use one production model version at a time for all tenants. Service identity may
be retained for attribution and analytics but must not change the feature schema
or select a service-specific model in the first release.

### 5.2 Offline training, production inference only

The training endpoint must not be part of the public production workflow.
Training should run in a controlled CI/ML release job and produce an immutable
artifact bundle. Production containers load that bundle and expose inference.

The existing `/train-request-classifier` endpoint should be disabled in
production or restricted to a separate internal training deployment. Possession
of the inference token alone must not authorize replacing a production model.

### 5.3 Purpose-built access-log forwarder

Implement a small Infra-Monitor forwarder instead of pointing Alloy
`loki.write` at the current custom API. Alloy should continue collecting metrics.
The forwarder may run as a systemd service installed alongside Alloy and should:

- tail one or more configured files;
- optionally consume Docker JSON/stdout logs for explicitly enabled services;
- parse supported access formats;
- create the canonical access-event payload;
- batch, retry, spool, and submit events;
- use the existing server credential from `/etc/alloy/credential`;
- expose local health/status information without exposing the credential.

If the team deliberately chooses Loki as the log protocol instead, it must add a
real Loki-compatible authenticated ingestion endpoint. Merely changing the URL
in the current reference Alloy file is not sufficient.

### 5.4 Identity comes from trusted enrollment state

The server credential determines the organization and server. Never trust an
organization ID supplied by a collector. If a service ID is supplied, validate
that the service belongs to the authenticated server; otherwise reject the
batch or entry.

## 6. Canonical ingestion contract

Version the route or body before rollout. Recommended endpoint:

```text
POST /api/internal/request-logs/v1/batches/
Authorization: Bearer <server credential>
Content-Type: application/json
```

Recommended payload:

```json
{
  "schema_version": 1,
  "batch_id": "018f4f80-94bb-7e30-a7c1-f34349c55c90",
  "server_id": "c34793ec-175a-43b9-9103-269899555e11",
  "sent_at": "2026-09-08T12:00:10Z",
  "entries": [
    {
      "event_id": "018f4f80-a733-72e1-82c8-34f57af36d7e",
      "service_id": "dba66cf5-6357-408a-8095-13488226ef52",
      "timestamp": "2026-09-08T12:00:00Z",
      "source_ip": "203.0.113.10",
      "method": "GET",
      "path": "/search",
      "query_string": "q=example",
      "status_code": 200,
      "user_agent": "Mozilla/5.0",
      "content_length": 431,
      "response_time_ms": 18.4,
      "referer": "",
      "protocol": "HTTP/1.1",
      "headers_digest": {}
    }
  ]
}
```

Response:

```json
{
  "batch_id": "018f4f80-94bb-7e30-a7c1-f34349c55c90",
  "accepted": 1,
  "duplicates": 0,
  "rejected": 0,
  "errors": []
}
```

Contract requirements:

- Maximum entries per batch: configurable, initially 500.
- Maximum uncompressed request size: configurable, initially 1 MiB.
- `batch_id` and `event_id` must support idempotent retry.
- The server ID must match the authenticated credential.
- The service must belong to that server.
- Accept UTC timestamps within a bounded past/future window.
- Split URL path and query before feature extraction.
- Never accept request bodies, authorization values, cookies, session IDs, or
  raw credentials.
- Return bounded per-entry errors without echoing sensitive fields.
- Prefer all-or-nothing batch validation for identity errors and per-entry
  rejection for malformed event data.

Maintain the existing route temporarily for compatibility, then remove it after
all collectors use the versioned contract.

## 7. Database changes

Extend `RequestLog` with:

- nullable `service` foreign key to `servers.Service`;
- unique indexed `event_id` scoped appropriately for collector idempotency;
- optional `batch_id` for operations/debugging;
- `model_version` used for the stored verdict;
- optional `ingestion_schema_version`;
- optional redacted `collector_source` such as `nginx_file`, `apache_file`, or
  `docker_stdout`.

Recommended constraints and indexes:

- unique `(server, event_id)` for external events;
- `(organization, service, zone, -timestamp)`;
- `(server, -timestamp)`;
- keep the existing organization/IP/source indexes.

Add a collector status model or extend monitoring connection state with:

- last successful request-log ingestion time;
- last batch size;
- last bounded error code/time;
- collector version and schema version;
- access-log collection state: `UNCONFIGURED`, `HEALTHY`, `STALE`, or `ERROR`.

Do not store credentials or complete rejected payloads in status records.

## 8. Model artifact lifecycle

### 8.1 Artifact bundle

Publish an immutable bundle containing at least:

```text
request_shield/
  model.joblib
  metadata.json
  checksums.sha256
```

`metadata.json` must contain:

- stable semantic model version;
- artifact format version;
- exact feature names in exact order;
- feature-schema version or hash;
- label mapping;
- training dataset identity/version;
- training code revision;
- training timestamp;
- library/runtime versions;
- evaluation metrics per class and macro averages;
- confidence/decision policy;
- validation status and approver/release reference.

Do not use a random UUID alone as the operational model version.

### 8.2 Training and validation gate

Training must be reproducible and occur outside production. Split data by a
meaningful boundary such as application/source/time rather than randomly mixing
near-duplicate requests. Report at minimum:

- per-class precision, recall, and F1;
- macro F1;
- confusion matrix;
- RED false-negative rate;
- GREEN false-positive rate;
- confidence calibration;
- results on previously unseen services or datasets.

CICIDS2017-derived data may bootstrap development, but production approval
requires evaluation against representative labelled HTTP request traffic.
Administrator verdicts can later form part of a curated retraining dataset, but
must never trigger automatic training.

### 8.3 Deployment and rollback

- Package a validated baseline artifact with the ML release, or fetch a pinned
  version from an authenticated artifact store during deployment.
- Verify its checksum before activation.
- Load and validate the artifact during readiness checks, not only upon the first
  classification request.
- Fail readiness when the artifact is missing, corrupt, or feature-incompatible.
- Keep the previous approved artifact available for rollback.
- Activate a new model atomically; never overwrite a live artifact in place.
- Store `model_version` on every classified `RequestLog`.

### 8.4 Inference contract hardening

The ML service must reject requests when:

- feature names/order differ from artifact metadata;
- a vector has the wrong length;
- a value is not numeric or violates configured bounds;
- batch size exceeds the limit;
- model output has an unknown class or invalid probability.

The Django client must validate response count, zones, confidence range, and
model version before updating rows. A partial or invalid response must leave the
affected rows retryable.

## 9. Forwarder and service discovery

### 9.1 Configuration source

Add Request Shield collection configuration to server enrollment/re-enrollment.
Each explicitly enabled service needs:

- stable service ID;
- access-log source type;
- file path or Docker container selector;
- parser format;
- optional parser-specific fields;
- enabled state.

Do not silently scan every file or every container. Collection must be explicit.

### 9.2 Initially supported inputs

Support a deliberately small first set:

1. nginx combined access-log file;
2. Apache combined access-log file;
3. structured JSON access logs matching a documented schema;
4. Docker stdout only when it contains one of those supported formats.

Multiline application logs, arbitrary JSON, and framework exceptions are not
Request Shield inputs.

### 9.3 Reliability

The forwarder must:

- persist file offsets;
- handle rotation and truncation;
- spool bounded batches to disk while the backend is unavailable;
- use exponential backoff with jitter;
- preserve event IDs across retry;
- cap spool disk usage and report dropped-event counts;
- avoid logging credentials or full query strings;
- send over TLS outside local development;
- run as a dedicated non-root user with only necessary log-read access.

### 9.4 Installation

Update the existing installer to install/configure the forwarder alongside Alloy.
The backend-generated configuration should use the verified ingestion origin and
existing credential file. Re-enrollment must safely replace configuration and
restart only the affected collector components.

For WSL2 testing, systemd must be enabled. The forwarder must be able to reach the
Windows/Docker-hosted backend using the same verified address already used for
monitoring enrollment.

## 10. Backend behavior

### 10.1 Ingestion

- Authenticate before parsing large batches where possible.
- Derive organization/server from the credential.
- Resolve and validate service ownership in a bounded number of queries.
- Apply redaction and canonicalization before persistence.
- Bulk-create new events and safely count duplicates.
- Extract features using `sanitize.features` as the only source of truth.
- Return quickly; do not invoke ML synchronously from the HTTP request.

### 10.2 Configuration enforcement

Define and enforce these semantics:

- `enabled=false`: reject or acknowledge-without-storing new external events,
  stop classifying pending events, stop suggestions, and clearly show disabled
  state. Select one ingestion behavior and document it; rejecting with a stable
  status is easier to observe.
- `platform_self_monitor=false`: middleware does not store platform traffic.
- `gemini_escalation=false`: no Gemini calls.
- `notify_on_red`: controls notification creation only.

Cache configuration briefly if required, but configuration changes must take
effect within a documented interval.

### 10.3 Classification concurrency

- Claim rows so multiple workers do not classify the same batch concurrently.
- Use transaction-safe selection such as `select_for_update(skip_locked=True)`
  or an explicit claimed state/time.
- Track attempts and last bounded error.
- Add exponential retry/backoff or rely on scheduled retry with a minimum delay.
- Mark permanently invalid vectors as failed instead of retrying forever.
- Expose counts for pending, classified, retrying, and failed events.

### 10.4 Privacy and retention

- Never store request bodies.
- Strip or hash sensitive query parameters based on configurable key names.
- Continue excluding authorization, cookies, and CSRF values.
- Respect trusted-proxy configuration before accepting `X-Forwarded-For`.
- Add a scheduled retention task with an organization-level or deployment-level
  retention period.
- Ensure logs, traces, and error reporting use redacted URLs.

## 11. API and Flutter work

### 11.1 API

Add `service_id`, safe service display fields, `model_version`, and collector
source to request presenters. Extend analytics and list filters with:

- server;
- service;
- zone;
- source;
- model version;
- time range;
- IP, method, and path search where already supported.

Apply the same filters consistently to totals, zone distribution, trends, and
top IPs. Validate enums/UUIDs and return `400` for invalid filters rather than
silently returning misleading data.

Restrict configuration changes, verdicts, and suggestion actions to the intended
owner/admin roles. Read access should follow the application's documented
organization and service permissions.

### 11.2 Flutter

Complete the Request Shield experience with:

- functional server and service filters;
- correctly wired zone and source filters;
- time-range selector;
- configuration page for authorized users;
- model version and classification time in request details;
- collector health/last-ingestion state;
- distinct empty states for disabled, unconfigured, collector unhealthy, no
  traffic, awaiting classification, and genuinely no threats;
- retry/error presentation that does not expose secrets;
- clear wording that accepting a suggestion records acknowledgement and does not
  block an IP.

## 12. Observability

Add structured metrics and bounded logs for:

- batches/events accepted, duplicated, rejected, and dropped;
- ingestion latency and response codes;
- pending queue age and size;
- inference batch size, duration, success, retry, and failure;
- result counts by zone and model version;
- model readiness and artifact version;
- forwarder spool size/age and last successful upload;
- suggestion and Gemini processing outcomes.

Do not use organization, server, service, IP, or URL as unbounded metric labels.
Those belong in secured logs/database records.

## 13. Testing strategy

### 13.1 Unit tests

- Every supported parser format and malformed-line behavior.
- URL/query splitting and redaction.
- Feature vector length, numeric type, names, and order.
- SQL injection, XSS, traversal, command injection, suspicious extension,
  scanner, and clean-request representatives.
- Artifact metadata and feature compatibility checks.
- Service/server ownership validation.
- Idempotent duplicate handling.
- configuration enforcement and permission checks.
- correct UI provider filter arguments.

### 13.2 Backend/ML integration tests

- Valid batch creates attributed unclassified rows.
- Wrong server or cross-server service returns `403` without persistence.
- Duplicate retry does not create duplicate rows.
- Saved artifact is loaded without invoking training.
- Worker classifies rows and stores model version.
- Missing/corrupt/incompatible artifact leaves rows recoverable and fails ML
  readiness.
- Invalid or short ML responses do not partially corrupt classification state.
- Multiple workers do not double-claim rows.
- disabled configurations behave according to the documented contract.

### 13.3 Docker smoke test

Revise `scripts/sanitize-e2e.ps1` so the default production-like test uses a
pinned baseline artifact. Keep temporary training only as a separately named ML
training test. Start the worker and beat where asynchronous behavior is under
test instead of calling every service function directly.

The smoke test must verify:

1. artifact checksum and readiness;
2. authenticated ingestion;
3. asynchronous classification;
4. stored model version;
5. analytics and filtering;
6. suggestion generation;
7. duplicate retry behavior.

### 13.4 WSL2 end-to-end test

Add a new Request Shield section to
`docs/local-physical-device-monitoring-lab.md` covering:

1. Start the complete backend, ML service, Redis, worker, beat, database, and
   Flutter client.
2. Verify the ML readiness endpoint reports the expected model version.
3. Enroll the Ubuntu WSL2 host through the normal application flow.
4. Deploy a labelled nginx test service with access logging enabled.
5. Enable Request Shield collection for that service.
6. Verify forwarder status, configuration, file permissions, and backend reachability.
7. Generate ordinary and safely encoded test requests, for example:
   - `/health`
   - `/search?q=normal`
   - a URL-encoded SQL-injection-shaped query;
   - a URL-encoded traversal-shaped query;
   - a URL-encoded XSS-shaped query.
8. Confirm events appear under Shield -> External with the correct organization,
   server, and service.
9. Wait for classification and confirm zone, confidence, signals, and model
   version are populated.
10. Stop backend connectivity temporarily, generate traffic, restore connectivity,
    and verify spooled events arrive once without duplicates.
11. Rotate the nginx access log and verify collection continues.
12. Attempt cross-tenant/cross-server service attribution and verify rejection.
13. Verify configuration disable/enable behavior.
14. Clean up the test service and any generated data using documented bounded commands.

The test must explicitly distinguish request shapes from real exploitation and
must run only against the local test service.

## 14. Delivery phases

### Phase 0: Contract and model release decisions

- Approve the canonical event schema and endpoint version.
- Approve service attribution and idempotency design.
- Pin `FEATURE_NAMES` as feature-schema version 1.
- Define model evaluation thresholds and release ownership.
- Decide whether production training endpoint is removed or separately deployed.

Exit: reviewed API contract, model metadata schema, and threat/privacy review.

### Phase 1: Saved-model inference hardening

- Produce a reproducible baseline artifact and evaluation report.
- Validate artifact during ML readiness.
- Enforce feature compatibility and response validation.
- Store model version on classified logs.
- Separate production inference testing from training testing.

Exit: a clean deployment performs inference without any training operation.

### Phase 2: Backend ingestion and attribution

- Add schema/version/idempotency/service fields and migrations.
- Implement the versioned ingestion API and ownership checks.
- Add redaction, limits, configuration enforcement, and collector status.
- Harden worker concurrency/retry behavior.

Exit: manually submitted events are safely attributed, deduplicated, classified,
and queryable.

### Phase 3: WSL/Docker collection

- Build/package the forwarder.
- Support nginx, Apache, structured JSON, and explicitly configured Docker logs.
- Extend enrollment and re-enrollment configuration.
- Add spool, retry, rotation handling, health, and secure service permissions.

Exit: real WSL service access traffic reaches Request Shield without manual POSTs.

### Phase 4: API and Flutter completion

- Add consistent service/server/time/source/zone filters.
- Add settings and collector-health UI.
- Fix empty/error/pending states and permissions.

Exit: administrators can configure, observe, filter, and review the complete flow.

### Phase 5: Validation and controlled rollout

- Complete unit, integration, Docker, and WSL lab tests.
- Run privacy/security review and load testing.
- Enable for an internal/canary organization first.
- Monitor ingestion, queue age, model outcomes, false positives, and storage growth.
- Document rollback for collector config and model artifact.

Exit: acceptance criteria pass and operational owners approve broader rollout.

## 15. Definition of done

The integration is complete only when all statements below are true:

- Production starts and classifies requests using a pinned, validated saved model
  without training.
- Missing or incompatible artifacts fail readiness clearly.
- A newly enrolled WSL server can be configured through the supported application
  flow to collect access events from an explicitly selected service.
- Normal and suspiciously shaped requests appear in the correct organization's
  dashboard and are attributed to the correct server and service.
- Retries do not duplicate events.
- Cross-tenant and cross-server attribution is rejected.
- Collector outage, no traffic, pending inference, and no threats are visibly
  distinguishable.
- UI filters change all displayed aggregates consistently.
- Disabling Request Shield and platform self-monitoring has the documented effect.
- Request bodies and sensitive credentials are neither stored nor logged.
- Model version and inference state are auditable per request.
- The WSL lab document can be followed from a clean setup and passes end to end.
- Rollback procedures for both the model and collector configuration have been tested.

## 16. Developer handoff checklist

Before coding, the developer should confirm these choices with the technical owner:

- baseline model dataset and minimum acceptance metrics;
- artifact distribution mechanism;
- forwarder implementation language/package format;
- supported first-release access-log formats;
- behavior when Request Shield is disabled;
- request-log retention duration and sensitive query-key policy;
- batch and spool limits;
- permissions for configuration, verdicts, and suggestion actions;
- whether Gemini remains enabled as optional GRAY escalation.

Implementation should be delivered in reviewable phases. Database/API contracts
and model compatibility checks should land before collector rollout, and the
real WSL end-to-end test must be part of the feature acceptance rather than a
post-release follow-up.
