# Container Isolation Forest Integration

> **Scope note:** The current school-project implementation uses the simplified
> training/inference design in
> [Simple ML Backend Plan](ML%20Backend%20Work%20Split.md). Dataset registries,
> readiness, validation/promotion, durable ML jobs, and correlation described
> below are deferred production enhancements.

## 1. Decision and current readiness

Infra Monitor will use deterministic lifecycle rules as the authority for service
crash/offline detection. Isolation Forest is the first anomaly-detection
algorithm for unusual container behaviour and degradation that may precede a
crash; it is not the source of truth for whether a service is running. Each model
row represents one stable monitored service on one server during one completed
UTC time bucket. Host-level samples must not be substituted when a container
feature is unavailable.

Integration is **partially ready**:

- Django already recognizes the notebook feature codes and queries
  VictoriaMetrics with trusted organization, server, and service identity.
- Alloy already enables its cAdvisor exporter when Docker is available, and the
  ingestion gateway replaces edge identity with trusted `organization_id`,
  `server_id`, and `service_id` labels.
- The service-level query implementation currently uses container series for
  `cpu_r` and `mem_u`. Container expressions must still be added for `disk_r`,
  `disk_w`, `eth1_fi`, and `eth1_fo`.
- The FastAPI dataset, training, inference, model registry, and worker pipeline
  described in [ML Service Architecture](ML%20Architecture.md) is not yet
  implemented.

Therefore the current code must not declare a service ready for this model until
all six production features are available at service scope.

## 2. Notebook decision

The reference notebook is
`experiments/previous/anomalydetection-multivariate-time-series.ipynb`. Its
Isolation Forest experiment:

- selects eleven experimental features, including host-oriented signals that are
  deliberately excluded from the production container schema;
- fits `sklearn.ensemble.IsolationForest` on the training rows;
- maps scikit-learn prediction `1` to normal and `-1` to anomaly;
- tests contamination values from `0.01` through `0.15` with
  `random_state=42`; and
- selects contamination using labelled test-set F1 score.

The notebook establishes a useful algorithm candidate, not a production model
artifact. Its source data was already normalized, its labels were used to tune
contamination, and one saved output shows execution before
`best_contamination` existed. Production training must version preprocessing,
feature semantics, temporal validation, and contamination selection instead of
loading the notebook model directly.

## 3. Feature contract

Feature schema `container_iforest_v1` uses only six metrics that can be collected
for the monitored container/service. Values are finite floating-point numbers
computed from one container-scoped service and aligned to the same bucket.
Counter features use rates over a fixed five-minute lookback; emitted model rows
default to a 60-second cadence after the lookback is complete.

| Code | Intended container meaning | Source/derivation | Current Django service query | Required action |
| --- | --- | --- | --- | --- |
| `cpu_r` | CPU usage as percent of one CPU core | `sum(rate(container_cpu_usage_seconds_total[5m])) * 100` | Container-scoped | Keep, and document that multi-core workloads may exceed 100%; do not cap silently. |
| `mem_u` | Working set as percent of configured container memory limit | `container_memory_working_set_bytes / container_spec_memory_limit_bytes * 100` | Container-scoped | Reject absent/unbounded limits or introduce a separately versioned denominator policy. |
| `disk_r` | Container filesystem bytes read per second | `rate(container_fs_reads_bytes_total[5m])` | No service expression; server expression is host-only | Add a cAdvisor service expression. |
| `disk_w` | Container filesystem bytes written per second | `rate(container_fs_writes_bytes_total[5m])` | No service expression; server expression is host-only | Add a cAdvisor service expression. |
| `eth1_fi` | Container receive bytes per second over non-loopback interfaces | `rate(container_network_receive_bytes_total{interface!="lo"}[5m])` | No service expression; server expression is host-only | Add a cAdvisor service expression; the legacy `eth1` name is only a stable feature code. |
| `eth1_fo` | Container transmit bytes per second over non-loopback interfaces | `rate(container_network_transmit_bytes_total{interface!="lo"}[5m])` | No service expression; server expression is host-only | Add a cAdvisor service expression. |

cAdvisor documents container CPU, memory, filesystem I/O, and network counters,
including the `container_fs_*` and `container_network_*` series used above. Metric
availability still depends on the host kernel, cgroup version, runtime, cAdvisor
build/options, filesystem, and storage driver. Readiness must inspect actual
series rather than assume that enabling cAdvisor makes every feature available.

The initial model deliberately excludes `load_1`, `load_5`, `disk_q`, `disk_u`,
and `tcp_timeouts`. They are host-only in the current adapter, are not uniformly
available with honest service-level semantics, or require additional privileged
collection. They may be introduced only in a new feature-schema version after
service-level collection and deployment compatibility are proven. Notebook
scores do not apply to the six-feature production schema.

## 4. Crash/offline detection

Crash detection does not wait for the 72-hour ML warm-up and does not depend on
an active model. Django's service lifecycle evaluates deterministic evidence:

- an application scrape target reports `up == 0`;
- the container disappears or its last-seen timestamp becomes stale;
- a Docker health check reports unhealthy;
- container start time changes, indicating restart;
- an OOM/exit event is observed; or
- the service heartbeat/telemetry deadline expires.

Rules move the service through the defined `STALE`/`OFFLINE` lifecycle and emit
an idempotent alert/correlation event. Missing telemetry must distinguish a
single service failure from collector, host, ingestion, or VictoriaMetrics
failure before declaring a crash. Isolation Forest detections can enrich or
raise the severity of this evidence but cannot override lifecycle truth.

## 5. Container identity and aggregation

All training and inference queries must include the trusted VictoriaMetrics
tenant plus `server_id` and `service_id`. The ingestion gateway derives those
labels from the server credential and the validated
`monitoring.service_name` Docker label. User-provided IDs never select a tenant.

The current Django service identity is stable across container restarts and is
better for learning a continuing workload than a transient Docker container ID.
When several replicas on the same server deliberately share one service name,
their cAdvisor series are aggregated and the model describes that logical
service group. Per-replica modelling would require a new stable replica identity
and must not use ephemeral container IDs as model ownership.

Root cAdvisor series (`id="/"`), empty images/names, unlabeled containers, host
`node_*` series, and series without the trusted `service_id` must be excluded
from ML datasets.

## 6. Collection changes required

1. Keep Alloy's host collector for server dashboards, but make the ML feature
   queries a separate allowlist containing only container expressions.
2. Ensure cAdvisor propagates `monitoring.service_name` on every selected
   container resource series so ingestion can attach `service_id`.
3. Relabel collector output to the same validated `service_name`; let the
   ingestion gateway derive the trusted `service_id` as it does for cAdvisor.
4. Add scrape-time and ingestion tests containing representative cAdvisor disk
   and network series, not only application `up` samples.
5. Add deployment probes that report which of the six features are available
   for each service and why a feature is missing.

The Docker socket and any eBPF/namespace access are privileged capabilities.
Installation must disclose them, use read-only/minimal mounts where supported,
and keep the telemetry gateway's credential-derived identity enforcement.

## 7. Dataset construction

FastAPI builds an immutable dataset by querying VictoriaMetrics directly. A
dataset definition includes:

- organization, server, and service UUID;
- feature schema `container_iforest_v1` and ordered feature list;
- source metric expressions or expression-version hash;
- UTC start/end, five-minute rate window, row cadence, and alignment boundary;
- expected units and per-feature completeness counts;
- missing-value, unbounded-memory, restart, and counter-reset policies;
- chronological train/validation/test boundaries; and
- preprocessing artifact/version and definition hash.

Rows are joined by timestamp only after all six features have been evaluated
on the same grid. Do not forward-fill across restarts or telemetry gaps, replace
missing values with zero, mix units, or fall back to host metrics. A bucket is
usable only when every required feature is finite and passes quality checks.

The existing Django public range adapter caps queries at 30 days and 5,000
points. The ML worker must use its own authenticated, tenant-safe VictoriaMetrics
query adapter with bounded pagination/chunking; it should not scrape Django's
Flutter-facing metric endpoints.

## 8. Isolation Forest training and inference

Train one model per stable service initially. Cohort/global models require an
explicit compatibility key covering workload type, feature schema, units,
collector versions, resource-limit policy, and platform.

The training artifact must contain:

- fitted Isolation Forest;
- exact ordered feature names;
- scikit-learn/runtime versions;
- preprocessing parameters fitted on training data only;
- `n_estimators`, `max_samples`, `contamination`, and `random_state`;
- dataset UUID and definition hash;
- validation metrics and score/threshold distribution; and
- compatibility metadata for collector and feature schema versions.

Use chronological validation. Labels from resolved incidents may evaluate and
calibrate candidates, but production training must not tune against the final
held-out test period as the notebook does. Start with `random_state=42`; select
contamination from an operator-approved bounded policy and available historical
labels, then store the chosen value rather than recalculating it during inference.

Inference uses the same query definitions, ordering, cadence, and preprocessing
artifact. Persist `decision_function`/anomaly score, model decision, threshold,
feature values, window, completeness, model version, and dataset lineage. Require
multiple anomalous buckets or correlation evidence before creating an incident
to avoid treating a single noisy sample as an outage.

## 9. Integration boundary

```text
Alloy cAdvisor + application health/lifecycle signals
                         |
                         v
              trusted Django ingestion
                         |
                         v
             tenant VictoriaMetrics data
                    /            \
                   v              v
      Django lifecycle rules   FastAPI ML workers
                   |              |
                   v              v
          crash/offline event  Isolation Forest
                   |           degradation detection
                   +------v-------+
                     correlation
                         |
                         v
              Django incident service
```

Django continues to own services and incidents. FastAPI owns dataset, job, model,
and detection metadata. ML workers never insert incidents directly and never use
Django's host-level metric expressions as fallback values.

## 10. Acceptance gates

The container Isolation Forest pipeline is ready only when all gates pass:

1. Every selected series contains trusted tenant, server, and service identity.
2. All six model features are present for a representative container for at least
   the configured readiness window, with stable units and acceptable gaps.
3. Killing/restarting the container preserves service identity, handles counter
   resets, and does not join samples across the restart gap.
4. Host CPU, memory, disk, or network activity from an unrelated container does
   not change the selected service's feature rows.
5. Dataset creation is reproducible from its immutable definition and hash.
6. Training and inference use identical ordered features and preprocessing.
7. An unavailable feature blocks readiness with a specific reason; it never
   becomes zero or a host-derived substitute.
8. Model activation is atomic, and a failed or incompatible candidate leaves the
   previous model active.
9. Replayed inference windows and correlation candidates do not duplicate
   detections or incidents.
10. A service crash is detected without an ML model, and an ML-only anomaly does
    not by itself mark the service offline.

## 11. Implementation order

1. Add container disk/network expressions and adapter tests.
2. Prove all cAdvisor-derived series retain trusted `service_id` through remote
   write and VictoriaMetrics.
3. Implement deterministic service lifecycle/crash rules and idempotent events.
4. Implement per-service feature readiness and the immutable dataset builder.
5. Implement versioned six-feature Isolation Forest training, validation, registry, and
   activation.
6. Implement idempotent window inference, detection persistence, correlation,
   and Django incident submission.

## 12. References

- [cAdvisor Prometheus container metrics](https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md)
- [ML Service Architecture](ML%20Architecture.md)
- [User Implementation Integration Contract](API%20Documentation/User%20Implementation%20Integration%20Contract.md)
