# User Implementation Integration Contract

## Purpose

This contract defines what exporter enrollment, VictoriaMetrics, ML, and Gemini implementations must provide so the agent-owned APIs and current Flutter screens continue working without contract changes. The ownership lists remain [User-Owned APIs](User-Owned%20APIs.md) and [Agent-Owned APIs](Agent-Owned%20APIs.md).

## Telemetry identity and lifecycle

- Enrollment creates a `Servers` row with a required trusted organization, stable UUID, unique organization/hostname pair, environment, and `UNKNOWN` status.
- Discovery upserts `Service` by `(server_id, service_name)`. Restarts reuse the same service identity.
- Every referenced server/service must belong to the credential-derived organization. Request-body and edge labels never select the tenant.
- Successful samples update last-seen fields and health. Missing telemetry transitions resources to `STALE`, then `OFFLINE`; it never deletes records or history.
- VictoriaMetrics account/project identifiers remain internal. Django/Flutter receive organization UUIDs only.

## Monitoring credential contract

- Internal enrollment creates or updates the server's single `MonitoringConnection`, then calls `MonitoringCredentialService.issue()` for its initial write credential.
- Credential wire format is `srv_<credential UUID without hyphens>.<random secret>`. Only the SHA-256 secret hash is persisted; the complete value is delivered once.
- Ingestion authenticates with `MonitoringCredentialService.verify()`. Only `ACTIVE` credentials and unexpired `GRACE` credentials are accepted; `REVOKED` and expired credentials fail without revealing tenant identity.
- Successful authenticated callbacks update `last_callback_at`; accepted metric batches update `last_metric_at`, ingestion health, server last-seen state, and the enrollment's first-metric timestamp.
- Disconnect and cancelled partial enrollment states are authoritative. Internal endpoints must not recreate or reactivate credentials for them without a new enrollment.

## Metric sample contract

Every normalized sample/series point provides:

```json
{
  "metric_type": "cpu_r",
  "value": 42.5,
  "unit": "percent",
  "recorded_at": "2026-09-03T12:00:00Z",
  "organization_id": "trusted organization UUID",
  "server_id": "trusted server UUID",
  "service_id": "optional service UUID",
  "labels": {"quality": "complete"}
}
```

The mandatory initial Isolation Forest feature subset is exactly:

```text
cpu_r, mem_u, disk_r, disk_w, eth1_fi, eth1_fo
```

These codes are governed by feature schema `container_iforest_v1` and must be
container/service scoped. Host `node_*` values are not valid fallbacks. See
[Container Isolation Forest Integration](../Container%20Isolation%20Forest%20Integration.md)
for metric derivations, known collector gaps, dataset rules, and readiness gates.

- Codes are case-sensitive and must not be renamed.
- Each series carries an explicit stable unit. Unknown units are returned but never guessed or silently converted.
- `cpu_r`, `mem_u`, and `disk_u` populate percentage cards only for `percent`, `%`, or `percentage` units.
- Additional application/derived metrics such as latency, error rate, availability, and uptime are allowed.
- Timestamps are UTC, windows are ordered/non-overlapping, values are finite numbers, and duplicate delivery is idempotent.
- `load_1`, `load_5`, `disk_q`, `disk_u`, and `tcp_timeouts` are excluded from `container_iforest_v1`; host values must never fill those or any missing service feature.

## Metrics query adapter

The future VictoriaMetrics adapter must preserve the database adapter behavior:

- Fetch latest metric by organization, server, optional service, and exact code.
- Fetch an ordered bounded range using `from`, `to`, and requested step.
- Return code, per-point unit, timestamp, value, labels, availability, and completeness.
- Aggregate only compatible units and never mix tenants.
- Represent no samples as an available empty result rather than fabricated zeros.

## ML handoff

- Deterministic lifecycle rules, not ML, are authoritative for service crashes, restarts, staleness, and offline state. They operate before ML warm-up and without an active model.
- Isolation Forest detects unusual service-level container behaviour and possible pre-crash degradation; an anomaly alone does not mark a service offline.
- The FastAPI ML service owns `/api/internal/ml/*`, durable dataset/job/model/detection/correlation metadata, and worker coordination. Redis is dispatch only; model artifacts live in object storage.
- FastAPI/workers query VictoriaMetrics directly with server-generated bounded queries and trusted tenant mappings. Django does not proxy training data or model artifacts.
- Readiness begins with the first valid service-health sample and requires 72 hours of usable data.
- First inference starts only after successful validation and activation; retraining defaults to every seven days while the prior model keeps serving.
- Each anomaly persists organization, server/service, window, the exact feature-value map, score, confidence, decision, model/version provenance, and detection timestamp.
- Candidate failure never replaces the active model.
- Alert/incident correlation uses stable fingerprints and submits incident candidates to Django's authenticated internal boundary. Django revalidates ownership and calls the shared tenant-scoped domain service; ML never writes Django incident tables.

See [ML Service Architecture](../ML%20Architecture.md) for the runtime topology,
data ownership, workflow, and failure contract.

## AI handoff

- Gemini reads incidents/evidence only through organization-scoped services after rechecking the active membership and conversation owner.
- Missing analysis is `null`, displayed as “Not analyzed”; it is never replaced by placeholder confidence.
- Persist user messages before socket acknowledgement and completed assistant messages before completion events.
- Citations identify authorized evidence records without exposing secrets, credentials, unrestricted logs, provider errors, or cross-tenant identifiers.

## Acceptance checks

1. A credential for organization A cannot write/query organization B data even with forged labels or known UUIDs.
2. Replayed samples, training triggers, inference windows, and correlation jobs are idempotent.
3. Stopping/restarting a container changes one existing service's lifecycle without deleting history or creating a duplicate.
4. All eleven required feature codes arrive with stable explicit units throughout a valid 72-hour window.
5. Empty/not-configured telemetry and ML return deterministic availability states; core API readiness remains healthy.
