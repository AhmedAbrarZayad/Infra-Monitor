# Local monitoring lab: Windows, WSL2, and Android

This Windows Home lab uses:

- Windows: Docker Desktop, Django, PostgreSQL, VictoriaMetrics, and Flutter
- Physical Android phone: Flutter debug application
- Existing Ubuntu WSL2 distribution: Alloy and Linux load tools
- Docker Desktop WSL integration: labeled test services

Examples use Windows `192.168.0.107` and phone `192.168.0.108`. Replace them
when DHCP assigns different addresses. This is a LAN-only development setup:
never expose port `7000` through router forwarding, UPnP, a public tunnel, or a
public IP. Keep Windows Firewall enabled.

Never publish `.env` files, enrollment commands, JWTs, OAuth secrets, or refresh
tokens. Revoke and replace any credential exposed in chat, logs, screenshots,
or version control.

## 1. Prerequisites

Install and start Docker Desktop, Flutter/Android tooling, Git, and Ubuntu WSL2.
Multipass and VirtualBox are not required.

```powershell
docker version
docker compose version
flutter doctor -v
wsl --list --verbose
```

`Ubuntu` must show WSL version `2`.

## 2. Find the device addresses

```powershell
ipconfig
wsl -d Ubuntu -- hostname -I
wsl -d Ubuntu -- bash -lc "ip route show default"
```

Use the IPv4 address of the active Wi-Fi/Ethernet adapter, not WSL, Docker, VPN,
or loopback. Find the phone address in Android Wi-Fi details. Both should share
a trusted, non-guest subnet such as `192.168.0.x`.

For `hostname -I`, the first address is the WSL source address used in the
firewall rule. Ignore Docker's usual `172.17.0.1` bridge address. For the route
output, record the address after `default via`; that is the Windows destination
WSL can reliably reach. Example:

```text
Windows LAN IP: 192.168.0.107
Phone IP:       192.168.0.108
WSL source IP:  172.28.148.9
WSL gateway:    172.28.144.1
```

Resolve all four values before continuing. WSL addresses may change after
`wsl --shutdown` or a Windows restart.

## 3. Configure narrow firewall rules

Open Administrator PowerShell:

```powershell
Start-Process powershell.exe -Verb RunAs
```

On a trusted home network, use its actual interface alias:

```powershell
Get-NetConnectionProfile
Set-NetConnectionProfile -InterfaceAlias "WiFi" -NetworkCategory Private
```

Remove stale duplicate lab rules, then create exact rules for the phone and the
first WSL address found in step 2:

```powershell
Get-NetFirewallRule -DisplayName "Infra Monitor Phone 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Infra Monitor Phone 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress 192.168.0.108 -InterfaceAlias "WiFi" -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress 172.28.148.9 -Action Allow -Profile Any
```

Do not use `172.17.0.1` for the WSL rule. Creating these rules before starting
Compose is fine; the listener appears when the backend starts. Never disable
Windows Firewall for the lab.

## 4. Configure the backend and model environments

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path model/.env)) { Copy-Item model/.env.example model/.env }
```

Set PostgreSQL and Django values in `backend/.env`. Set a non-empty
`ML_SERVICE_TOKEN` there, then copy that exact token into `model/.env`. Compose
loads each service's own file; there is no root `.env`, and the token must never
be put in Flutter.

```dotenv
# backend/.env
POSTGRES_USER=monitor
POSTGRES_PASSWORD=replace-with-a-local-database-password
POSTGRES_DB=ai-infra-monitor
ML_SERVICE_TOKEN=replace-with-a-long-random-shared-secret

# model/.env
ML_SERVICE_TOKEN=replace-with-the-same-long-random-shared-secret
DJANGO_INTERNAL_URL=http://backend:8000
DJANGO_CALLBACK_TIMEOUT_SECONDS=10
ML_ARTIFACT_DIR=/code/artifacts
```

Use plain URLs in `.env` files. Do not paste Markdown link syntax such as
`[http://backend:8000](http://backend:8000)`.

`backend` is the service name in `docker-compose.yml`. Docker Compose provides
internal DNS, so the `ml_service` container resolves `backend` to the Django
container and calls:

```text
http://backend:8000/api/internal/ml/detections/
```

Port `8000` is Django's container port. The published port `7000` is only for
requests coming from Windows or the physical phone. Therefore, use
`http://backend:8000` for the FastAPI-to-Django callback and
`http://<WINDOWS_LAN_IP>:7000` from physical devices.

On Windows PowerShell versions where the static `GetBytes` method is
unavailable, generate a token with:

```powershell
$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$token = ([BitConverter]::ToString($bytes)).Replace('-', '')
$rng.Dispose()
$token
```

Paste the printed value as `ML_SERVICE_TOKEN` in both environment files.

Use this local configuration, replacing addresses and passwords:

```dotenv
SECRET_KEY=replace-with-a-long-random-local-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.0.107,172.28.144.1
CSRF_TRUSTED_ORIGINS=http://192.168.0.107:7000
USE_X_FORWARDED_HOST=False

POSTGRES_USER=monitor
POSTGRES_PASSWORD=replace-with-a-local-database-password
POSTGRES_DB=ai-infra-monitor
DB_HOST=localhost
DB_PORT=5433
DB_CONN_MAX_AGE=60

SEED_ENGINEER_USERNAME=engineer
SEED_ENGINEER_EMAIL=engineer@example.com
SEED_ENGINEER_PASSWORD=replace-with-a-local-test-password

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=30
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
FRONTEND_WEB_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000

OTP_EXPIRY_MINUTES=10
MONITORING_ENROLLMENT_EXPIRY_MINUTES=15
MONITORING_INSTALL_URL=http://172.28.144.1:7000/api/monitoring/install.sh
MONITORING_PUBLIC_BASE_URL=http://172.28.144.1:7000
MONITORING_SERVER_URL=http://172.28.144.1:7000
MONITORING_CREDENTIAL_OVERLAP_MINUTES=15
MONITORING_REMOTE_WRITE_MAX_COMPRESSED_BYTES=10485760
MONITORING_REMOTE_WRITE_MAX_DECOMPRESSED_BYTES=104857600
VICTORIAMETRICS_INSERT_URL=http://vminsert:8480
VICTORIAMETRICS_WRITE_TIMEOUT_SECONDS=10
VICTORIAMETRICS_SELECT_URL=http://vmselect:8481
VICTORIAMETRICS_QUERY_TIMEOUT_SECONDS=10

GMAIL_SENDER_EMAIL=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
```

Gmail is unnecessary for the seeded verified account. Compose overrides the
host database address with `postgres:5432` inside Django.

The physical phone continues using `http://192.168.0.107:7000/api` in Flutter.
The three monitoring URLs use the WSL gateway because the installer and Alloy
run inside WSL. Setting these values now avoids changing `.env` after startup.

## 5. Start the platform

```powershell
Set-Location "C:\Users\ahmed\OneDrive\Documents\Projects\AI Incident Report and Infrastructure monitoring\Infra-Monitor"
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:7000/api/health/live/
Invoke-RestMethod http://127.0.0.1:7001/health
Invoke-RestMethod http://192.168.0.107:7000/api/health/live/
wsl -d Ubuntu -- curl --connect-timeout 5 --max-time 10 -fsS http://172.28.144.1:7000/api/health/live/
docker compose exec backend python manage.py seed_dummy_engineer
```

The backend container runs `python manage.py migrate` before starting Django.
Do not run a second manual migration while it is starting; concurrent migrations
can briefly expose a partially migrated schema. Wait for the local health check
to succeed before running `seed_dummy_engineer`. If startup takes longer, inspect
`docker compose logs --tail 200 backend` and retry the health check.

Confirm `backend`, `ml_service`, `celery_worker`, `celery_beat`, `redis`,
`vmstorage`, `vminsert`, and `vmselect` are running. Services with health checks
should report healthy.

For failures:

```powershell
docker compose logs --tail 200 backend
docker compose logs --tail 200 vmstorage vminsert vmselect
docker compose logs --tail 200 ml_service celery_worker celery_beat redis
```

## 6. Verify Ubuntu WSL2

```powershell
wsl -d Ubuntu
```

Inside Ubuntu:

```bash
systemctl is-system-running
curl --connect-timeout 5 --max-time 10 -fsS http://172.28.144.1:7000/api/health/live/
```

Use the WSL gateway recorded in step 2, not the Windows LAN address used by the
phone. If both commands succeed, do not change `backend/.env` or recreate the
backend; continue directly to the Flutter and enrollment steps.

`running` or `degraded` means systemd is available. Otherwise enable it:

This is one-time recovery, not part of a normal lab run. If it is required,
stop Compose first. After the WSL restart, return to step 2 and repeat address
discovery, firewall configuration, environment configuration, and startup
because the WSL source and gateway addresses may have changed.

```bash
sudo sh -c 'printf "[boot]\nsystemd=true\n" > /etc/wsl.conf'
exit
```

Then in PowerShell:

```powershell
wsl --shutdown
wsl -d Ubuntu
```

Reopen Docker Desktop afterward because `wsl --shutdown` stops its WSL backend.

Install load tools inside Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y stress-ng fio sysstat curl
```

Alloy's cAdvisor collector needs the Docker Engine's local containerd socket.
Docker Desktop WSL integration exposes the Docker API socket but not
`/run/containerd/containerd.sock`, so it cannot supply container CPU, memory,
and disk metrics. In Docker Desktop → Settings → Resources → WSL Integration,
**disable** integration for `Ubuntu` and apply/restart. Keep Docker Desktop
running for the Windows backend.

Install a separate native Docker daemon inside Ubuntu for monitored workloads:

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now containerd docker
getent group docker || sudo groupadd docker
sudo usermod -aG docker "$USER"
exit
```

Restart only Ubuntu from PowerShell:

This restart is also one-time setup. After it completes, return to step 2 and
repeat the address-dependent steps before enrolling the server.

```powershell
wsl --terminate Ubuntu
wsl -d Ubuntu
```

Verify the native daemon and required socket:

```bash
groups
docker version
docker info
systemctl is-active docker containerd
test -S /run/containerd/containerd.sock && echo "containerd socket ready"
```

`groups` must include `docker`, both services must be `active`, and the socket
check must succeed. Do not use `chmod 666` on Docker sockets; membership in the
`docker` group is already effectively root-equivalent and should be limited to
the trusted lab user.

If Alloy was enrolled before this change, its configuration remains valid.
Restart it after native Docker is ready:

```bash
sudo systemctl restart alloy
journalctl -u alloy --since "2 minutes ago" --no-pager
```

## 7. Run Flutter on the phone

Set `frontend/.env`:

```dotenv
API_BASE_URL=http://192.168.0.107:7000/api
GOOGLE_WEB_CLIENT_ID=
GOOGLE_ANDROID_CLIENT_ID=
```

This file is bundled into the app; put no secrets in it.

```powershell
Set-Location frontend
flutter clean
flutter pub get
flutter devices
flutter run -d YOUR_DEVICE_ID
```

Sign in using the seeded email/password. Create an organization through
onboarding or **More → Create organization**.

## 8. Enroll Ubuntu from Flutter

Organization owners/admins can enroll servers:

1. Open **Servers** and tap **Add server**.
2. Enter `WSL Ubuntu Lab` and choose **Development**.
3. Tap **Generate install command** and copy it.
4. Run the command inside Ubuntu WSL2.

The command contains a secret, single-use token that expires after 15 minutes.
Do not share or commit it.

```bash
systemctl status alloy --no-pager
journalctl -u alloy -n 100 --no-pager
```

Wait 15–30 seconds and refresh Flutter.

## 9. Add discoverable services

Inside Ubuntu using Docker Desktop integration:

```bash
docker run -d \
  --name demo-metrics \
  --restart unless-stopped \
  --label monitoring.enabled=true \
  --label monitoring.service_name=demo-metrics \
  --label monitoring.metrics_port=9100 \
  --label monitoring.metrics_path=/metrics \
  prom/node-exporter:latest

docker run -d \
  --name demo-load \
  --restart unless-stopped \
  --label monitoring.enabled=true \
  --label monitoring.service_name=demo-load \
  alpine sleep infinity
```

## 10. Generate and compare load

Run one test at a time with the Flutter server-detail page open. Before starting,
record the WSL CPU count and a quiet baseline:

```bash
nproc
mpstat 1 5
free -h
iostat -dx 1 5
ip -s link
```

Alloy normally scrapes every 15 seconds. CPU and disk rates use a five-minute
window, so a short load causes a gradual rise rather than an immediate jump.
For a presentation, allow 30–60 seconds after starting each command, refresh the
app, and explain the smoothing window.

| Test | Expected app behavior |
| --- | --- |
| One CPU worker | Approximately `100 / nproc` host CPU |
| Half the CPU workers | Trends toward approximately 50% while sustained |
| 1 GiB memory allocation | Memory rises by roughly `1 GiB / WSL total memory` |
| `fio` mixed I/O | Disk read/write throughput and utilization rise |
| One busy container core | Service CPU trends toward 100%; host rises by `100 / nproc` |
| Docker `iperf3` traffic | Container and host network counters rise |

### CPU showcase

One worker demonstrates CPU normalization. On 12 WSL CPUs it should read close
to `8.33%` (`100 / 12`):

```bash
stress-ng --cpu 1 --timeout 90s
```

For a clearer approximately 50% demonstration, use half the available CPUs:

```bash
workers=$(( $(nproc) / 2 ))
[ "$workers" -lt 1 ] && workers=1
echo "Using $workers of $(nproc) logical CPUs"
stress-ng --cpu "$workers" --timeout 6m
```

Six minutes lets the five-minute chart window fill and approach 50%. Stop early
with `Ctrl+C` after the graph clearly rises. Compare concurrently in another WSL
terminal:

```bash
mpstat 1
```

For nearly 100%, use all WSL CPUs only when temporary system sluggishness is
acceptable:

```bash
stress-ng --cpu "$(nproc)" --timeout 90s
```

### Memory showcase

Show the total first, then allocate 1 GiB:

```bash
free -h
stress-ng --vm 1 --vm-bytes 1G --vm-keep --timeout 90s
```

In another terminal:

```bash
watch -n 1 free -h
```

Expected percentage-point increase is approximately `1 GiB / total WSL memory
× 100`. Existing cache and application activity make it approximate. Do not
allocate most of WSL's memory; that can force swapping and make Windows sluggish.

### Disk showcase

```bash
fio --name=monitor-test --filename=/tmp/monitor-test.bin --size=1G \
  --rw=readwrite --bs=1M --direct=1 --time_based --runtime=90
```

Compare while it runs:

```bash
iostat -dx 1
```

The app should show increased disk read/write rates. Its five-minute rate will
usually be lower than fio's active-run summary because the chart includes idle
time before and after the test. Remove the test file:

```bash
rm -f /tmp/monitor-test.bin
```

### Container CPU showcase

Confirm `demo-load` is running, then saturate one container core:

```bash
docker start demo-load 2>/dev/null || true
docker exec -d demo-load sh -c 'timeout 90 yes >/dev/null'
docker stats demo-load
```

`docker stats` should approach 100% for the container. Service CPU should trend
toward 100%, while normalized host CPU rises by approximately `100 / nproc`
percentage points.

### Network showcase

Generate traffic entirely inside the native WSL Docker engine:

```bash
docker network create monitor-test-net
docker run -d --rm --name demo-iperf-server --network monitor-test-net \
  --label monitoring.enabled=true \
  --label monitoring.service_name=demo-network \
  networkstatic/iperf3 -s
docker run --rm --network monitor-test-net networkstatic/iperf3 -c demo-iperf-server -t 60 -P 4
```

Watch counters in another terminal:

```bash
watch -n 1 'ip -s link'
```

Throughput direction should match the iperf3 result, but exact app values may be
smoothed. Clean up afterward:

```bash
docker stop demo-iperf-server 2>/dev/null || true
docker network rm monitor-test-net
```

### Cooldown

Wait at least five minutes after sustained tests if you want the smoothed charts
to return close to baseline. Confirm no load generator remains:

```bash
pgrep -af 'stress-ng|fio|yes' || echo "No load generators running"
docker stats --no-stream
```

WSL reports its Linux environment's resource view, not total Windows usage.

## 11. Test anomaly detection and crash classification

Keep `demo-load` running long enough for Alloy to report all six container
features: CPU, memory, disk read/write, and network in/out. The ML dispatcher
runs every five minutes and uses only completed five-minute UTC buckets. On the
first usable run it trains from the preceding 24 hours, saves a per-service
artifact, and retries inference.

Find the discovered service UUID and optionally enqueue it immediately:

```powershell
docker compose exec backend python manage.py shell -c "from servers.models import Service; [print(s.service_id, s.display_name) for s in Service.objects.all()]"
docker compose exec backend python manage.py shell -c "from ml_model.tasks import orchestrate_service_ml; print(orchestrate_service_ml.delay('SERVICE_UUID').id)"
docker compose logs --tail 200 celery_worker ml_service
docker compose exec ml_service ls -la /code/artifacts/SERVICE_UUID
```

Missing or incomplete feature rows are deliberately skipped; they are never
zero-filled or replaced with host metrics. Let the baseline collect for several
windows, then generate sustained container CPU, disk, and network load using the
workloads above. Wait until the next five-minute bucket completes and either let
Celery beat dispatch normally or enqueue the service task again.

Refresh the phone. An anomalous window appears as a warning under **Overview →
Needs Attention** and **Server Detail → Anomaly History**, with the message
“Unusual service behaviour; crash not confirmed.” Isolation Forest can classify
the generated load as normal, especially with a short baseline, so several
completed baseline/load windows may be needed.

Finally stop the monitored container:

```bash
docker stop demo-load
```

After the configured lifecycle timeout and confirmation observations, Django
marks the service offline and creates the critical lifecycle incident shown in
**Incidents**. The earlier ML warning never creates an incident or changes the
service lifecycle.

## 12. End-of-session secure cleanup

Log out of Flutter. Inside Ubuntu:

```bash
docker rm -f demo-metrics demo-load
sudo systemctl stop alloy
```

On Windows:

```powershell
Set-Location "C:\Users\ahmed\OneDrive\Documents\Projects\AI Incident Report and Infrastructure monitoring\Infra-Monitor"
docker compose stop
wsl --shutdown
```

Firewall removal requires Administrator privileges. Open a new elevated window
and accept the UAC prompt:

```powershell
Start-Process powershell.exe -Verb RunAs
```

In the new window, verify elevation; the result must be `True`:

```powershell
([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

Then close lab access and confirm every firewall profile is enabled. These
commands remove every duplicate rule with the displayed name:

```powershell
Get-NetFirewallRule -DisplayName "Infra Monitor Phone 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallRule -DisplayName "Infra Monitor Django 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallProfile | Select-Object Name,Enabled
```

The third command removes the old broad rule if it exists. Trusted home Wi-Fi
may remain Private. Optionally restore it:

```powershell
Set-NetConnectionProfile -InterfaceAlias "WiFi" -NetworkCategory Public
```

Check that environment files were not staged:

```powershell
git status --short -- backend/.env model/.env frontend/.env
git check-ignore backend/.env model/.env frontend/.env
```

## 13. Permanently remove lab data

Retain database/metrics volumes:

```powershell
Set-Location "C:\Users\ahmed\OneDrive\Documents\Projects\AI Incident Report and Infrastructure monitoring\Infra-Monitor"
docker compose down
```

Permanently erase them only when intended:

```powershell
docker compose down --volumes
```

Do not run `wsl --unregister Ubuntu`; it permanently erases everything in that
distribution and is not a normal cleanup step.

## 14. Uninstall Multipass and reclaim its space

The repository includes a guarded Administrator script. Preview first:

```powershell
Set-Location "C:\Users\ahmed\OneDrive\Documents\Projects\AI Incident Report and Infrastructure monitoring\Infra-Monitor"
.\scripts\remove-multipass-lab.ps1 -RemoveData -WhatIf
```

Then delete the empty failed instance, uninstall Multipass, and remove only
verified Multipass directories:

```powershell
.\scripts\remove-multipass-lab.ps1 -RemoveData
```

If VirtualBox was installed solely for this lab and contains no other VMs:

```powershell
.\scripts\remove-multipass-lab.ps1 -RemoveData -RemoveVirtualBox
```

VirtualBox removal is explicit because it could affect unrelated VMs. The
script never deletes general VirtualBox VM folders.

## 15. Troubleshooting

- Phone failure: confirm exact phone IP/rule, same non-guest subnet, no VPN, and
  no router client isolation.
- WSL failure: run `hostname -I` and recreate its exact-IP rule if it changed.
- Flutter failure: confirm `frontend/.env` includes `/api`, then rebuild.
- Enrollment failure: confirm WSL can curl Django and generate a fresh token.
- Missing metrics: check Alloy logs and `docker compose ps`, then wait two
  scrape cycles.
- Missing ML features: confirm the target is a discovered container service and
  all six service-level series exist. Host metrics and partial rows are rejected.
- Missing artifact: inspect `celery_worker` and `ml_service` logs, verify at
  least one complete feature row exists, then enqueue the service task again.
- Unauthorized ML calls: ensure `ML_SERVICE_TOKEN` is identical in
  `backend/.env` and `model/.env`, then recreate `backend`, `celery_worker`, and
  `ml_service` so they reload it.
- Celery inactivity: verify Redis is healthy and both `celery_worker` and
  `celery_beat` are running; inspect their logs for broker or task errors.
- Normal-only inference: collect more baseline windows and sustain load through
  a full completed five-minute bucket. A test is not guaranteed to be anomalous.
- Phone does not update: pull to refresh, check the polling preference, and
  confirm the phone can still reach the Windows LAN address on port 7000.
