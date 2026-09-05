# Monitoring: server installation to dashboard metrics

This document describes the current monitoring implementation end to end:

- how an owner/admin enrolls a Linux server from Flutter;
- every monitoring API involved;
- what the installer changes on the server;
- how Alloy sends host, container, and application metrics;
- what Django validates and changes in PostgreSQL;
- where time-series samples are stored and queried;
- how to verify, rotate, disconnect, and remove a server safely.

For Windows Home, WSL2, physical-phone networking, firewall rules, and load-test
commands, see [local-physical-device-monitoring-lab.md](local-physical-device-monitoring-lab.md).

## 1. Architecture

```mermaid
flowchart LR
    UI[Flutter Add server] -->|JWT| ENROLL[Django enrollment API]
    ENROLL --> PG[(PostgreSQL control plane)]
    ENROLL -->|single-use command| HOST[Linux / WSL server]
    HOST -->|one-time enrollment token| INTERNAL[Django internal enrollment]
    INTERNAL --> PG
    INTERNAL -->|Alloy config + server credential| HOST
    HOST -->|Prometheus remote write| GATEWAY[Django metrics gateway]
    GATEWAY -->|trusted tenant/server labels| VM[(VictoriaMetrics)]
    GATEWAY --> PG
    UI -->|JWT metric queries| QUERY[Django operational API]
    QUERY --> VM
    QUERY -->|JSON| UI
```

There are two data stores with different responsibilities:

| Store | Contains |
| --- | --- |
| PostgreSQL | Organizations, memberships, enrollment lifecycle, servers, monitoring connections, hashed write credentials, VictoriaMetrics tenant mapping, and discovered services |
| VictoriaMetrics | Raw Prometheus time-series samples and labels |

The existing `servers_metrics` PostgreSQL table/model is not written by the
current Prometheus remote-write pipeline. Dashboard metric reads query
VictoriaMetrics through `VictoriaMetricsQueryAdapter`.

## 2. Required platform configuration

The important backend settings are:

```dotenv
MONITORING_ENROLLMENT_EXPIRY_MINUTES=15
MONITORING_INSTALL_URL=http://192.168.0.107:7000/api/monitoring/install.sh
MONITORING_PUBLIC_BASE_URL=http://192.168.0.107:7000
MONITORING_SERVER_URL=http://192.168.0.107:7000
MONITORING_CREDENTIAL_OVERLAP_MINUTES=15
MONITORING_REMOTE_WRITE_MAX_COMPRESSED_BYTES=10485760
MONITORING_REMOTE_WRITE_MAX_DECOMPRESSED_BYTES=104857600
VICTORIAMETRICS_INSERT_URL=http://vminsert:8480
VICTORIAMETRICS_SELECT_URL=http://vmselect:8481
VICTORIAMETRICS_WRITE_TIMEOUT_SECONDS=10
VICTORIAMETRICS_QUERY_TIMEOUT_SECONDS=10
```

`MONITORING_PUBLIC_BASE_URL` must be reachable from the monitored server. Do not
use `localhost` when Django runs on another machine.

Start and migrate the platform:

```powershell
Set-Location backend
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose ps
Invoke-RestMethod http://127.0.0.1:7000/api/health/live/
```

Compose publishes Django as host port `7000` to container port `8000`.

## 3. Authorization model

All user-facing organization APIs require a JWT access token:

```http
Authorization: Bearer USER_ACCESS_TOKEN
```

Rules:

- An approved organization member can read servers, services, health, and
  metrics belonging to that organization.
- Only an approved `OWNER` or `ADMIN` can create/cancel enrollments, change
  server monitoring state, or rotate credentials.
- Flutter hides **Add server** from engineers, and the backend independently
  enforces the same rule.
- Internal installer and metric-write APIs do not act as a user. They derive
  organization and server identity from short-lived enrollment tokens or
  permanent server credentials.

## 4. Enrollment lifecycle

```mermaid
stateDiagram-v2
    [*] --> CREATED: Owner/admin generates command
    CREATED --> EXPIRED: Expiry time passes
    CREATED --> CANCELLED: Owner/admin cancels
    CREATED --> INSTALLING: Installer exchanges token
    INSTALLING --> FAILED: Installer reports failure
    INSTALLING --> CONNECTED: First metric batch accepted
    CONNECTED --> [*]
```

Installer progress is tracked separately as:

```text
INSTALLER_STARTED → COLLECTOR_INSTALLED → COLLECTOR_STARTED
```

The authoritative transition to `CONNECTED` is the first successfully forwarded
metric batch, not merely the collector-started callback.

## 5. Step 1: generate the command in Flutter

The current UI flow is:

1. Sign in and select/create an organization.
2. Open **Servers**.
3. Tap **Add server** (owner/admin only).
4. Enter the server name and environment.
5. Tap **Generate install command**.
6. Copy the command and run it on the target Linux host.

Flutter calls:

```http
POST /api/organizations/{organization_id}/monitoring/enrollments/
Authorization: Bearer USER_ACCESS_TOKEN
Content-Type: application/json

{
  "server_name": "WSL Ubuntu Lab",
  "environment": "development"
}
```

Response (`201 Created`, abbreviated):

```json
{
  "enrollment_id": "UUID",
  "server_name": "WSL Ubuntu Lab",
  "environment": "development",
  "stage": "CREATED",
  "expires_at": "2026-09-04T12:15:00Z",
  "is_used": false,
  "server_id": null,
  "token": "enroll_REDACTED",
  "install_command": "curl -fsSL http://HOST:7000/api/monitoring/install.sh | sudo sh -s -- --token enroll_REDACTED --server http://HOST:7000"
}
```

At this point PostgreSQL receives one `accounts_enrollmenttoken` row:

- `token_hash`: SHA-256 hash of the secret token;
- `token_prefix`: non-secret prefix for identification;
- `organization_id`, `created_by_id`, name, and environment;
- `stage=CREATED`;
- `expires_at=now+MONITORING_ENROLLMENT_EXPIRY_MINUTES`;
- `server_id`, `consumed_at`, and `first_metric_at` remain null.

The raw enrollment token is returned only in this creation response. It is
single-use and must not be logged, committed, or shared.

## 6. Step 2: installer download and token exchange

The generated command downloads a public script:

```http
GET /api/monitoring/install.sh
```

Optional integrity endpoint:

```http
GET /api/monitoring/install.sh.sha256
```

Before running the command, the target must provide Linux, systemd, `apt-get`,
and connectivity to the backend. Install native Docker before enrollment if
container metrics are required; the generated Alloy config is decided using
`docker_available` at enrollment time.

The script detects hostname, OS, architecture, and Docker, then exchanges the
token:

```http
POST /api/internal/monitoring/enroll/
Content-Type: application/json

{
  "token": "enroll_REDACTED",
  "hostname": "Zayad",
  "os": "ubuntu",
  "architecture": "amd64",
  "docker_available": true
}
```

Valid architectures are `amd64` and `arm64`. Unknown, expired, cancelled,
consumed, and replayed tokens all return the same `401` response to avoid token
state disclosure. A duplicate hostname in one organization returns `409` with
code `hostname_already_registered`.

On success, one atomic PostgreSQL transaction:

1. locks and validates the enrollment;
2. creates `servers_servers` with status `UNKNOWN`;
3. creates `servers_monitoringconnection` with `PENDING/UNKNOWN` health;
4. creates the organization's `accounts_victoriametricstenant` if absent;
5. creates an `ACTIVE` `servers_serverwritecredential` containing only a hash;
6. links the enrollment to the server, sets `consumed_at`, and moves it to
   `INSTALLING`.

Response (`201 Created`, delivered only to the installer):

```json
{
  "enrollment_id": "UUID",
  "server_id": "UUID",
  "credential": "srv_UUID.REDACTED_SECRET",
  "ingestion_url": "http://HOST:7000/api/metrics/write",
  "config": "GENERATED_ALLOY_CONFIGURATION"
}
```

The backend stores only the SHA-256 hash of the secret portion of the server
credential. The raw credential is delivered once.

## 7. Step 3: changes made on the Linux server

The installer:

- installs `ca-certificates`, `curl`, `jq`, and `gpg`;
- adds Grafana's signed APT repository using a dedicated keyring;
- installs Grafana Alloy;
- writes generated configuration to `/etc/alloy/config.alloy`;
- writes the permanent credential to `/etc/alloy/credential`;
- sets both files to `root:alloy` with mode `0640`;
- creates `/var/lib/alloy` for state/WAL data;
- adds the `alloy` user to `docker` only when Docker exists;
- installs `/etc/systemd/system/alloy.service`;
- enables and starts Alloy.

The service runs as the non-login `alloy` user with `NoNewPrivileges`, protected
home/system paths, automatic restart, and write access limited to Alloy state.
Docker-group access is effectively root-equivalent and is granted explicitly.

Installer callbacks use the permanent server credential:

```http
POST /api/internal/monitoring/enrollments/{enrollment_id}/status/
Authorization: Bearer SERVER_WRITE_CREDENTIAL
Content-Type: application/json

{"stage":"COLLECTOR_STARTED"}
```

Allowed stages are `INSTALLER_STARTED`, `COLLECTOR_INSTALLED`,
`COLLECTOR_STARTED`, and `FAILED`. Failure callbacks can also contain an
uppercase `failure_code` (maximum 64 characters) and printable message (maximum
500 characters).

## 8. Step 4: collection and remote write

Generated Alloy components include:

- `prometheus.exporter.unix`: host CPU, memory, disk, load, filesystem, and
  network metrics;
- `prometheus.exporter.cadvisor`: container metrics when Docker was present;
- `discovery.docker`: application endpoint discovery;
- `prometheus.remote_write`: authenticated write to Django.

Application containers must opt in:

```bash
docker run -d \
  --name demo-metrics \
  --label monitoring.enabled=true \
  --label monitoring.service_name=demo-metrics \
  --label monitoring.metrics_port=9100 \
  --label monitoring.metrics_path=/metrics \
  prom/node-exporter:latest
```

Required discovery labels:

| Label | Purpose |
| --- | --- |
| `monitoring.enabled=true` | Explicit opt-in |
| `monitoring.service_name` | Stable service identity within the server |
| `monitoring.metrics_port` | Container metrics port, 1–65535 |
| `monitoring.metrics_path` | Optional path; defaults to `/metrics` |

Alloy sends Prometheus Remote Write v1 batches to:

```http
POST /api/metrics/write
Authorization: Bearer SERVER_WRITE_CREDENTIAL
Content-Type: application/x-protobuf
Content-Encoding: snappy
X-Prometheus-Remote-Write-Version: 0.1.0
```

Django rejects wrong encodings/version, invalid protobuf/Snappy, empty series,
oversized payloads, and revoked/expired credentials.

The gateway performs these security and persistence steps:

1. authenticates the write credential using constant-time hash comparison;
2. derives organization and server from that credential;
3. validates discovered service names/ports;
4. creates or updates `servers_service` rows;
5. removes edge-supplied identity labels;
6. overwrites `organization_id`, `server_id`, and recognized `service_id` with
   trusted database-derived values;
7. forwards the re-encoded batch to the organization's numeric VictoriaMetrics
   tenant;
8. only after VictoriaMetrics accepts it, updates PostgreSQL health state.

VictoriaMetrics write URL:

```text
{VICTORIAMETRICS_INSERT_URL}/insert/{account_id}:{project_id}/prometheus/api/v1/write
```

After an accepted first batch, PostgreSQL changes to:

- credential `last_used_at=now`;
- monitoring connection `status=CONNECTED`, `ingestion_health=HEALTHY`, and
  `last_metric_at=now`;
- server `status=HEALTHY` and `last_seen_at=now`;
- discovered services `status=HEALTHY` and `last_reported_at=now`;
- enrollment `stage=CONNECTED` and `first_metric_at=now`.

## 9. Database schema and migrations

Monitoring-specific schema arrives through:

| Migration | Change |
| --- | --- |
| `servers/0001_initial.py` | Creates server, service, and SQL metrics models |
| `servers/0002_...py` | Adds `unique_org_hostname` and `unique_server_service_name` constraints |
| `servers/0004_monitoringconnection_serverwritecredential.py` | Creates monitoring connection and write credential tables |
| `servers/0005_serverwritecredential_unique_active_server_credential.py` | Allows only one active credential per connection |
| `accounts/0013_enrollmenttoken.py` | Creates enrollment lifecycle table |
| `accounts/0014_monitoring_tenant_and_installer_stage.py` | Adds installer stage and VictoriaMetrics tenant mapping |

Important relationships:

```text
Organization 1 ── * EnrollmentToken
Organization 1 ── * Servers
Organization 1 ── 1 VictoriaMetricsTenant
Servers      1 ── 1 MonitoringConnection
Servers      1 ── * Service
Connection   1 ── * ServerWriteCredential
Enrollment   0..1 ── 1 Servers
```

Important constraints:

- one hostname per organization;
- one service name per server;
- one monitoring connection per server;
- one active write credential per connection;
- unique non-null rotation idempotency key per connection;
- one numeric VictoriaMetrics tenant mapping per organization;
- VictoriaMetrics account/project identifiers fit unsigned 32-bit limits.

Apply and inspect migrations:

```powershell
docker compose exec backend python manage.py showmigrations accounts servers
docker compose exec backend python manage.py migrate
```

Inspect control-plane rows without printing token/credential hashes:

```powershell
docker compose exec backend python manage.py shell -c "from accounts.models import EnrollmentToken,VictoriaMetricsTenant; from servers.models import Servers,MonitoringConnection,ServerWriteCredential,Service; print('enrollments',list(EnrollmentToken.objects.values('id','server_name','stage','installer_stage','expires_at','consumed_at','first_metric_at'))); print('servers',list(Servers.objects.values('server_id','name','host_name','status','last_seen_at'))); print('connections',list(MonitoringConnection.objects.values('id','server_id','status','ingestion_health','last_callback_at','last_metric_at'))); print('credentials',list(ServerWriteCredential.objects.values('id','connection_id','state','valid_until','last_used_at'))); print('tenants',list(VictoriaMetricsTenant.objects.values('organization_id','account_id','project_id'))); print('services',list(Service.objects.values('service_id','server_id','service_name','status','port','last_reported_at')))"
```

## 10. User-facing monitoring APIs

All paths below require a user JWT and enforce organization membership.

| Method and path | Role | Purpose |
| --- | --- | --- |
| `POST /api/organizations/{org}/monitoring/enrollments/` | Owner/admin | Create command/token |
| `GET /api/organizations/{org}/monitoring/enrollments/` | Owner/admin | List; optional `?stage=` |
| `GET /api/organizations/{org}/monitoring/enrollments/{id}/` | Owner/admin | Enrollment/connection status |
| `DELETE /api/organizations/{org}/monitoring/enrollments/{id}/` | Owner/admin | Cancel non-terminal enrollment |
| `GET /api/organizations/{org}/servers/` | Member | Paginated server list |
| `GET /api/organizations/{org}/servers/{server}/` | Member | Server summary |
| `PATCH /api/organizations/{org}/servers/{server}/` | Owner/admin | Change name/environment |
| `GET /api/organizations/{org}/servers/{server}/health/` | Member | Latest health metrics |
| `GET /api/organizations/{org}/servers/{server}/metrics/` | Member | Metric range |
| `GET /api/organizations/{org}/servers/{server}/services/` | Member | Discovered services |
| `GET /api/organizations/{org}/services/{service}/health/` | Member | Service health/latest metrics |
| `GET /api/organizations/{org}/services/{service}/metrics/` | Member | Service metric range |
| `GET /api/organizations/{org}/servers/{server}/monitoring/` | Member | Monitoring metadata |
| `DELETE /api/organizations/{org}/servers/{server}/monitoring/` | Owner/admin | Revoke writes/disconnect |
| `POST /api/organizations/{org}/servers/{server}/monitoring/credentials/rotate/` | Owner/admin | Rotate write credential |

Server list filters include `q`, `status`, and `environment`, plus standard
`limit`/`offset` pagination.

Metric range example:

```http
GET /api/organizations/{org}/servers/{server}/metrics/?metric=cpu_r&from=2026-09-04T11:00:00Z&to=2026-09-04T12:00:00Z&step=15
Authorization: Bearer USER_ACCESS_TOKEN
```

Response:

```json
{
  "metric": "cpu_r",
  "unit": "percent",
  "available": true,
  "availability": "available",
  "points": [
    {
      "timestamp": "2026-09-04T11:59:45Z",
      "value": 8.27,
      "unit": "percent",
      "labels": {}
    }
  ]
}
```

Ranges default to one hour, cannot exceed 30 days, return at most 5,000 points,
and require a step that keeps the response bounded.

## 11. Dashboard metric definitions

| Code | Unit | Server calculation |
| --- | --- | --- |
| `cpu_r` | percent | `100 - avg(rate(idle CPU[5m])) * 100` |
| `load_1` | load | Maximum `node_load1` |
| `load_5` | load | Maximum `node_load5` |
| `mem_u` | percent | `1 - available / total` |
| `disk_q` | seconds/second | Five-minute weighted disk I/O rate |
| `disk_r` | bytes/second | Five-minute disk-read rate |
| `disk_w` | bytes/second | Five-minute disk-write rate |
| `disk_u` | percent | Five-minute disk busy rate, capped at 100 |
| `eth1_fi` | bytes/second | Five-minute non-loopback receive rate |
| `eth1_fo` | bytes/second | Five-minute non-loopback transmit rate |
| `tcp_timeouts` | timeouts/second | Five-minute TCP timeout rate |

Currently, service queries use cAdvisor container series for `cpu_r` and `mem_u`;
unsupported service expressions return an empty result rather than falling back
to the server calculation. The planned `container_iforest_v1` model additionally
uses container-scoped `disk_r`, `disk_w`, `eth1_fi`, and `eth1_fo` after their
cAdvisor expressions and identity tests are implemented. Host metrics are never
inputs to that model. CPU is expressed per saturated core, so one busy container
core trends toward 100%, while host CPU is normalized across all logical CPUs.

Service crash/offline state comes from deterministic application `up`, container
last-seen/health/restart/OOM/exit, and heartbeat rules. Isolation Forest detects
degradation and does not independently mark a service offline. See
[Container Isolation Forest Integration](Container%20Isolation%20Forest%20Integration.md).

## 12. VictoriaMetrics read path

Django maps the authenticated organization to `account_id:project_id` and reads:

```text
{VICTORIAMETRICS_SELECT_URL}/select/{account_id}:{project_id}/prometheus/api/v1/query_range
```

Every query includes trusted `server_id`, and service queries also include
trusted `service_id`. Internal identity labels are removed from public JSON.
Reads use `nocache=1` and a one-millisecond latency offset so newly ingested rows
appear quickly.

## 13. Credential rotation and disconnect

Rotate with an idempotency key:

```http
POST /api/organizations/{org}/servers/{server}/monitoring/credentials/rotate/
Authorization: Bearer USER_ACCESS_TOKEN
Idempotency-Key: UNIQUE_OPERATION_ID
```

The current active credential becomes `GRACE` until the configured overlap time;
a new `ACTIVE` credential is returned once. Replaying the key returns `409`.
The caller must securely replace `/etc/alloy/credential` and restart Alloy.

Disconnect monitoring:

```http
DELETE /api/organizations/{org}/servers/{server}/monitoring/
Authorization: Bearer USER_ACCESS_TOKEN
```

This revokes active/grace credentials, marks the connection
`DISCONNECTED/STOPPED`, and marks the server `OFFLINE`. It does not uninstall
Alloy from the host or delete historical VictoriaMetrics samples.

## 14. Verification checklist

On the monitored server:

```bash
systemctl status alloy --no-pager
journalctl -u alloy --since "10 minutes ago" --no-pager
test -r /etc/alloy/config.alloy
test -r /etc/alloy/credential
```

If Docker metrics are enabled:

```bash
systemctl is-active docker containerd
test -S /var/run/docker.sock
test -S /run/containerd/containerd.sock
id alloy
docker ps
```

On Windows:

```powershell
Set-Location backend
docker compose ps
docker compose logs --tail 100 backend
Invoke-RestMethod http://127.0.0.1:7000/api/health/live/
Invoke-RestMethod http://127.0.0.1:7000/api/health/ready/
```

Success means:

- Alloy is active without recurring exporter/remote-write errors;
- the server appears in Flutter;
- PostgreSQL shows `CONNECTED/HEALTHY` and a recent `last_metric_at`;
- enrollment is `CONNECTED` with `first_metric_at` populated;
- VictoriaMetrics-backed API ranges return points;
- labeled containers create stable service rows and service metrics.

## 15. Uninstall from a monitored server

Disconnect through the API/UI first so the server credential is revoked. Then
on the Linux host:

```bash
sudo systemctl disable --now alloy
sudo apt-get remove --purge -y alloy
sudo rm -f /etc/apt/sources.list.d/grafana.list
sudo rm -f /etc/apt/keyrings/grafana.gpg
sudo rm -rf /etc/alloy /var/lib/alloy
sudo systemctl daemon-reload
```

The final `rm -rf` permanently removes local Alloy configuration, credentials,
and WAL/state. It does not remove PostgreSQL server metadata or historical
VictoriaMetrics data. Retention or an explicit backend deletion workflow must
handle historical data separately.
