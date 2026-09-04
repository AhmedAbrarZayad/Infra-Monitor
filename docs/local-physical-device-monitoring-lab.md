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
```

Use the IPv4 address of the active Wi-Fi/Ethernet adapter, not WSL, Docker, VPN,
or loopback. Find the phone address in Android Wi-Fi details. Both should share
a trusted, non-guest subnet such as `192.168.0.x`.

## 3. Configure `backend/.env`

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Use this local configuration, replacing addresses and passwords:

```dotenv
SECRET_KEY=replace-with-a-long-random-local-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.0.107
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
MONITORING_INSTALL_URL=http://192.168.0.107:7000/api/monitoring/install.sh
MONITORING_PUBLIC_BASE_URL=http://192.168.0.107:7000
MONITORING_SERVER_URL=http://192.168.0.107:7000
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

## 4. Start the platform

```powershell
Set-Location backend
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_dummy_engineer
docker compose ps
Invoke-RestMethod http://127.0.0.1:7000/api/health/live/
Invoke-RestMethod http://192.168.0.107:7000/api/health/live/
```

For failures:

```powershell
docker compose logs --tail 200 backend
docker compose logs --tail 200 vmstorage vminsert vmselect
```

## 5. Configure narrow firewall rules

Open Administrator PowerShell:

```powershell
Start-Process powershell.exe -Verb RunAs
```

On a trusted home network, use its actual interface alias:

```powershell
Get-NetConnectionProfile
Set-NetConnectionProfile -InterfaceAlias "WiFi" -NetworkCategory Private
```

This does not disrupt internet access. Keep untrusted networks Public.

Allow only the phone's current IP:

```powershell
New-NetFirewallRule -DisplayName "Infra Monitor Phone 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress 192.168.0.108 -InterfaceAlias "WiFi" -Action Allow -Profile Any
```

Start Ubuntu and note its first IPv4 address:

```powershell
wsl -d Ubuntu -- hostname -I
```

Allow only that WSL address, replacing `WSL_IP`:

```powershell
New-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress WSL_IP -Action Allow -Profile Any
```

WSL's address can change after shutdown/reboot. If so, replace its rule:

```powershell
Get-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress NEW_WSL_IP -Action Allow -Profile Any
```

Verify the phone opens:

```text
http://192.168.0.107:7000/api/health/live/
```

Never leave Windows Firewall disabled. A temporary diagnostic disable must be
followed immediately by re-enabling it.

## 6. Prepare Ubuntu WSL2

```powershell
wsl -d Ubuntu
```

Inside Ubuntu:

```bash
systemctl is-system-running
curl -fsS http://192.168.0.107:7000/api/health/live/
```

`running` or `degraded` means systemd is available. Otherwise enable it:

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

## 11. End-of-session secure cleanup

Log out of Flutter. Inside Ubuntu:

```bash
docker rm -f demo-metrics demo-load
sudo systemctl stop alloy
```

On Windows:

```powershell
Set-Location backend
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
git status --short -- backend/.env frontend/.env
git check-ignore backend/.env frontend/.env
```

## 12. Permanently remove lab data

Retain database/metrics volumes:

```powershell
Set-Location backend
docker compose down
```

Permanently erase them only when intended:

```powershell
docker compose down --volumes
```

Do not run `wsl --unregister Ubuntu`; it permanently erases everything in that
distribution and is not a normal cleanup step.

## 13. Uninstall Multipass and reclaim its space

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

## 14. Troubleshooting

- Phone failure: confirm exact phone IP/rule, same non-guest subnet, no VPN, and
  no router client isolation.
- WSL failure: run `hostname -I` and recreate its exact-IP rule if it changed.
- Flutter failure: confirm `frontend/.env` includes `/api`, then rebuild.
- Enrollment failure: confirm WSL can curl Django and generate a fresh token.
- Missing metrics: check Alloy logs and `docker compose ps`, then wait two
  scrape cycles.
