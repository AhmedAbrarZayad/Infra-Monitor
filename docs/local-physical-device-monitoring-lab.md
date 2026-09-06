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
$infraAdb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $infraAdb)) {
  throw "ADB is missing. Install Android SDK Platform-Tools from Android Studio > SDK Manager > SDK Tools."
}
& $infraAdb version
wsl --list --verbose
```

`Ubuntu` must show WSL version `2`.

### One-time preparation before presentation day

Complete this once before following the live-demo sequence. Enable systemd if
`wsl -d Ubuntu -- systemctl is-system-running` returns neither `running` nor
`degraded`, then restart WSL before continuing. Disable Docker Desktop's
integration for the `Ubuntu` distribution and install a native Docker engine so
cAdvisor can inspect its container runtime:

```bash
sudo apt-get update
sudo apt-get --fix-broken install
sudo dpkg --configure -a
sudo apt-get install -y docker.io stress-ng fio sysstat curl
sudo systemctl enable --now containerd docker
getent group docker || sudo groupadd docker
sudo usermod -aG docker "$USER"
```

Run `wsl --terminate Ubuntu` once to apply group membership, reopen Ubuntu, and
verify `groups`, `docker version`, and `systemctl is-active docker containerd`.
Do not restart WSL again during the live demonstration.

## 2. Find the device addresses

```powershell
ipconfig
```

Use the IPv4 address of the active Wi-Fi/Ethernet adapter, not WSL, Docker, VPN,
or loopback. The phone address is needed only for optional Wi-Fi testing. Find
it in Android Wi-Fi details and confirm both devices share a trusted, non-guest
subnet such as `192.168.0.x`.

```text
Windows LAN IP: 192.168.0.107
Phone IP:       192.168.0.108
```

ADB reverse needs neither address for Flutter. The generated enrollment command
detects the current Windows gateway inside WSL every time it runs.

## 3. Configure narrow firewall rules

USB/ADB phone testing does not require a phone firewall rule. The WSL rule is
still used by Alloy and the installer. Create the exact phone rule only when
testing the Flutter application over Wi-Fi.

Open Administrator PowerShell:

```powershell
Start-Process powershell.exe -Verb RunAs
```

On a trusted home network, use its actual interface alias:

```powershell
Get-NetConnectionProfile
Set-NetConnectionProfile -InterfaceAlias "WiFi" -NetworkCategory Private
```

Remove stale duplicate lab rules, then create the WSL NAT range rule. It avoids
replacing the rule whenever WSL changes address:

```powershell
Get-NetFirewallRule -DisplayName "Infra Monitor Phone 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Infra Monitor WSL 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress 172.16.0.0/12 -Action Allow -Profile Any
```

For optional Wi-Fi phone testing, add one rule using the phone's current IP:

```powershell
New-NetFirewallRule -DisplayName "Infra Monitor Phone 7000" -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress 192.168.0.108 -InterfaceAlias "WiFi" -Action Allow -Profile Any
```

The WSL rule permits only TCP port 7000 from the private address block WSL2 uses
for NAT; it does not expose the port publicly. Creating the rules before
starting Compose is fine. Never disable Windows Firewall for the lab.

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
GEMINI_API_KEY=replace-with-your-google-ai-studio-api-key
GEMINI_MODEL=gemini-3.7-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=60
ASSISTANT_WS_TICKET_TTL_SECONDS=60

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
`http://<WINDOWS_LAN_IP>:7000` from remote Linux hosts or optional Wi-Fi tests.

### Refresh addresses at the start of every lab session

The Windows LAN address can change after reconnecting to Wi-Fi; the phone
address can also change when using optional Wi-Fi testing. The WSL
virtual-adapter address can change and must **not** be saved as the public
monitoring address. Before starting Compose, display the current Windows Wi-Fi
address:

```powershell
$infraLanIp = (Get-NetIPAddress -InterfaceAlias "WiFi" -AddressFamily IPv4 |
  Where-Object AddressState -eq "Preferred" |
  Select-Object -First 1 -ExpandProperty IPAddress)
$infraLanIp
```

Use that value—not a `172.x` WSL/Docker address—in `backend/.env`:

```dotenv
MONITORING_INSTALL_URL=http://<WINDOWS_LAN_IP>:7000/api/monitoring/install.sh
MONITORING_PUBLIC_BASE_URL=http://<WINDOWS_LAN_IP>:7000
MONITORING_SERVER_URL=http://<WINDOWS_LAN_IP>:7000
```

For the recommended USB/ADB workflow, `frontend/.env` does not use either LAN
address:

```dotenv
API_BASE_URL=http://127.0.0.1:7000/api
```

Use the Windows LAN address only for optional Wi-Fi phone testing:

```dotenv
API_BASE_URL=http://<WINDOWS_LAN_IP>:7000/api
```

If any backend monitoring URL changes while Compose is already running,
restart Django so it reloads `backend/.env`:

```powershell
docker compose restart backend
Invoke-RestMethod "http://${infraLanIp}:7000/api/health/live/"
```

Re-run the Flutter application after changing `frontend/.env`, because that
file is bundled into the app. For Wi-Fi testing, also update the narrow firewall
rule whenever the phone's address changes. USB/ADB testing needs neither update.

These values are intentionally reachable fallbacks for generated commands.
When that command runs inside WSL2, it detects the live Windows gateway using
`ip route show default` and replaces the fallback host before downloading the
installer or consuming the enrollment token. Ordinary remote Linux machines
cannot use WSL gateway detection and therefore require a stable DNS name or a
reachable configured address.

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
Create the Gemini key in Google AI Studio and put it only in `backend/.env`.
It is not the ML shared token and must not be copied into `model/.env` or
`frontend/.env`. The backend container needs outbound internet access to call
the Gemini API.

Use this local configuration, replacing addresses and passwords:

```dotenv
SECRET_KEY=replace-with-a-long-random-local-secret
DEBUG=True
# LAN-only demo setting. Use explicit hostnames in a deployed environment.
ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=http://192.168.0.107:7000
USE_X_FORWARDED_HOST=False

POSTGRES_USER=monitor
POSTGRES_PASSWORD=replace-with-a-local-database-password
POSTGRES_DB=ai-infra-monitor
DB_HOST=localhost
DB_PORT=5433
DB_CONN_MAX_AGE=60

SEED_OWNER_USERNAME=owner
SEED_OWNER_EMAIL=owner@example.com
SEED_OWNER_PASSWORD=replace-with-a-local-owner-password
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=replace-with-a-local-admin-password
SEED_ENGINEER_USERNAME=engineer
SEED_ENGINEER_EMAIL=engineer@example.com
SEED_ENGINEER_PASSWORD=replace-with-a-local-engineer-password

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=30
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
FRONTEND_WEB_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000

OTP_EXPIRY_MINUTES=10
MONITORING_ENROLLMENT_EXPIRY_MINUTES=15
# Non-WSL fallback. The generated command detects and uses the live WSL gateway.
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

Gmail is unnecessary for the seeded verified accounts. Compose overrides the
host database address with `postgres:5432` inside Django.

The physical phone uses `http://127.0.0.1:7000/api` with ADB reverse, or the
Windows LAN address for optional Wi-Fi testing. The monitoring URLs remain safe
fallbacks for ordinary Linux hosts. On WSL, the generated command automatically
replaces their host with the current Windows gateway, and the backend returns
an Alloy configuration using that same verified address.

## 5. Start the platform

```powershell
Set-Location "C:\Users\ahmed\OneDrive\Documents\Projects\AI Incident Report and Infrastructure monitoring\Infra-Monitor"
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:7000/api/health/live/
Invoke-RestMethod http://127.0.0.1:7001/health
Invoke-RestMethod http://192.168.0.107:7000/api/health/live/
docker compose exec backend python manage.py seed_test_users
```

The backend container runs `python manage.py migrate` before starting Django.
Do not run a second manual migration while it is starting; concurrent migrations
can briefly expose a partially migrated schema. Wait for the local health check
to succeed before running `seed_test_users`. If startup takes longer, inspect
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
systemctl is-active docker containerd
```

If all three services report `running`, `degraded`, or `active`, do not change
`backend/.env`; continue directly to Flutter and enrollment.

```bash
groups
docker version
test -S /run/containerd/containerd.sock && echo "containerd socket ready"
```

`groups` must include `docker`, both services must be `active`, and the socket
check must succeed. Do not use `chmod 666` on Docker sockets; membership in the
`docker` group is already effectively root-equivalent and should be limited to
the trusted lab user.

Do not use `chmod 666` on runtime sockets. The hardened installer grants the
dedicated Alloy user the required Docker and containerd access automatically.

## 7. Run Flutter on the phone

### Recommended: USB with ADB reverse

This route is private to the authorized USB-debugging connection. It avoids
DHCP address changes, Windows phone firewall rules, guest-network isolation,
and router client-isolation settings.

Connect the unlocked phone by USB, accept its debugging prompt, and run:

```powershell
$infraAdb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $infraAdb)) {
  throw "ADB is missing. Install Android SDK Platform-Tools from Android Studio > SDK Manager > SDK Tools."
}
& $infraAdb version
& $infraAdb devices
```

The Python virtual environment does not install or expose ADB. The commands
above call the Android SDK executable directly, so no permanent `PATH` change is
required. In Android, enable **Developer options > USB debugging** and use a USB
cable that supports data. `adb devices` must show the device with state
`device`; if it says `unauthorized`, unlock the phone and accept the debugging
prompt. If it says `offline`, unlock and reconnect the phone, then restart ADB:

```powershell
& $infraAdb kill-server
& $infraAdb start-server
& $infraAdb devices
```

Do not continue until the state is `device`. Then create and verify the reverse
port-forwarding rule:

```powershell
& $infraAdb reverse tcp:7000 tcp:7000
& $infraAdb reverse --list
```

Set `frontend/.env`:

```dotenv
API_BASE_URL=http://127.0.0.1:7000/api
GOOGLE_WEB_CLIENT_ID=
GOOGLE_ANDROID_CLIENT_ID=
```

Here `127.0.0.1:7000` normally refers to the phone, but ADB forwards that port
over USB to port `7000` on Windows. HTTP and WebSocket traffic on port `7000`
both use the same forwarding rule. This file is bundled into the app; put no
secrets in it.

```powershell
Set-Location frontend
flutter clean
flutter pub get
flutter devices
flutter run -d YOUR_DEVICE_ID
```

ADB reverse rules may disappear after disconnecting or restarting the phone.
If the app later reports that it cannot reach the backend, reconnect USB and
run the following again:

```powershell
& $infraAdb reverse tcp:7000 tcp:7000
& $infraAdb reverse --list
```

Remove the rule when finished with:

```powershell
& $infraAdb reverse --remove tcp:7000
```

### Alternative: Android emulator

The Android emulator can reach the Windows loopback interface through
`10.0.2.2`. It does not test a physical phone, but it also avoids LAN firewall
and router configuration:

```dotenv
API_BASE_URL=http://10.0.2.2:7000/api
```

Stop and rerun Flutter after selecting this value.

### Optional: test over Wi-Fi

Use Wi-Fi only when the test specifically needs wireless connectivity. Confirm
the phone browser can open this endpoint before starting Flutter:

```text
http://<WINDOWS_LAN_IP>:7000/api/health/live/
```

If the browser cannot open it, do not debug Django or Flutter yet. Confirm the
phone IP, disable its VPN temporarily, leave guest Wi-Fi, and disable router
AP/client isolation. Then configure the exact phone firewall rule from section
3 and continue below.

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

If the browser endpoint works but the installed app does not, check the build
variant. `flutter run` uses the debug manifest, which permits local HTTP. A
release APK also needs the following in
`android/app/src/main/AndroidManifest.xml` while the lab uses plain HTTP:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<application android:usesCleartextTraffic="true" ...>
```

Prefer HTTPS instead of cleartext HTTP for any deployment outside this isolated
local lab.

Sign in as `owner@example.com` first. The default local password is
`Owner123!` unless overridden by `SEED_OWNER_PASSWORD`. Create an organization
through
onboarding or **More → Create organization**.

Then sign in with the Admin and Engineer accounts, request membership in that
organization, and use the Owner account to approve them and promote the Admin.

## 8. Enroll Ubuntu from Flutter

Organization Owners can enroll servers:

1. Open **Servers** and tap **Add server**.
2. Enter `WSL Ubuntu Lab` and choose **Development**.
3. Tap **Generate install command** and copy it.
4. Run the command inside Ubuntu WSL2.

The command contains a secret, single-use token that expires after 15 minutes.
Do not share or commit it. Run the generated command exactly as shown; do not
replace its URLs manually. On WSL it automatically:

1. detects the current Windows gateway from the default route;
2. downloads the installer with connection limits and retries;
3. proves Django is reachable before consuming the token;
4. uses the same working URL for enrollment, callbacks, and remote write;
5. grants Alloy Docker and containerd socket access; and
6. safely replaces an older Alloy configuration when the same host is
   re-enrolled.

The command should contain `ip route show default`, `--connect-timeout`, and
`--server "$_im_server"`. These confirm the dynamic installer is active.

```bash
systemctl status alloy --no-pager
journalctl -u alloy -n 100 --no-pager
grep 'url =' /etc/alloy/config.alloy
```

The URL should contain the current WSL gateway rather than the Windows LAN IP.
There must be no new `Failed to send batch`, `context deadline exceeded`, or
`containerd.sock: permission denied` messages. Wait 30–60 seconds and refresh
Flutter.

Confirm ingestion from Windows before continuing:

```powershell
docker compose logs backend --tail 200 | Select-String "POST /api/metrics/write"
```

At least one `204` response means Django accepted and forwarded telemetry.

## 9. Add discoverable services

Inside Ubuntu using its native Docker engine:

```bash
docker network inspect monitor-ml-net >/dev/null 2>&1 || docker network create monitor-ml-net

docker run -d \
  --name demo-metrics \
  --network monitor-ml-net \
  --memory 512m \
  --restart unless-stopped \
  --label monitoring.enabled=true \
  --label monitoring.service_name=demo-metrics \
  --label monitoring.metrics_port=9100 \
  --label monitoring.metrics_path=/metrics \
  prom/node-exporter:latest

docker run -d \
  --name demo-load \
  --network monitor-ml-net \
  --memory 512m \
  --restart unless-stopped \
  --label monitoring.enabled=true \
  --label monitoring.service_name=demo-load \
  alpine sleep infinity
```

Keep the explicit memory limits on both containers. The service-level ML
feature set calculates memory utilization from
`container_memory_working_set_bytes / container_spec_memory_limit_bytes`; an
unlimited container may not expose a usable denominator. Both containers also
join `monitor-ml-net` so cAdvisor consistently exposes their non-loopback
network counters. The feature builder requires CPU, memory, disk read/write,
and network receive/transmit at the same timestamp and intentionally rejects an
incomplete row instead of filling missing measurements with zero.

## 10. Optional metric showcases

If the goal is to test ML and Gemini, do not run these loads yet. Complete the
quiet-baseline and first-training steps in section 11 first, then return here if
you also want to demonstrate the host charts. Training on the showcase load
would make that activity part of the model's baseline.

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

Show the total first, then allocate a conservative 256 MiB with OOM avoidance:

```bash
free -h
stress-ng --vm 1 --vm-bytes 256M --vm-keep --oom-avoid --timeout 90s
```

In another terminal:

```bash
watch -n 1 free -h
```

Expected percentage-point increase is approximately `256 MiB / total WSL memory
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

## 11. Test ML anomaly detection, Gemini, and crash classification

### Establish a quiet baseline and confirm training

Keep `demo-load` running long enough for Alloy to report all six container
features: CPU, memory, disk read/write, and network in/out. The ML dispatcher
runs every five minutes and uses only completed five-minute UTC buckets. On the
first usable run it attempts inference, receives `model_not_found`, trains from
the available data within the preceding 24 hours, saves a per-service artifact,
and retries inference. Leave `demo-load` idle during this stage.

Find the `demo-load` service UUID:

```powershell
docker compose exec backend python manage.py shell -c "from servers.models import Service; [print(s.service_id, s.display_name) for s in Service.objects.filter(service_name='demo-load')]"
```

After creating the containers, leave them running quietly for at least ten
minutes, then continue watching until the next five-minute dispatcher run. The
metric queries use five-minute rates and ML evaluates only completed
five-minute UTC buckets, so the first one or two dispatcher runs may correctly
report `insufficient_inference_data` while the initial complete row is being
built.

Watch the first-time flow:

```powershell
docker compose logs -f ml_service celery_worker
```

The successful first-time sequence is:

```text
POST /infer 404
POST /train 200
POST /infer 200
```

Press `Ctrl+C` to stop following logs. If enough telemetry is already present,
the task can be enqueued immediately:

```powershell
docker compose exec backend python manage.py shell -c "from ml_model.tasks import orchestrate_service_ml; print(orchestrate_service_ml.delay('SERVICE_UUID').id)"
docker compose exec ml_service ls -la /code/artifacts/SERVICE_UUID
```

The artifact directory must contain `model.joblib` and `metadata.json`. If it
already existed from an earlier lab run, `/infer` returns `200` immediately and
`/train` is correctly skipped. Missing or incomplete feature rows are skipped;
they are never zero-filled or replaced with host metrics.

### Produce one controlled anomalous service window

Run all pressure inside the monitored `demo-load` container so the model sees
service-level rather than host-only evidence. First prepare a 64 MiB file and a
small HTTP server inside that container. Alpine places the `httpd` applet in
`busybox-extras`, so install it before starting the server:

```bash
docker exec demo-load apk add --no-cache busybox-extras
docker exec demo-load sh -c 'killall httpd 2>/dev/null || true; dd if=/dev/zero of=/tmp/ml-net.bin bs=1M count=64; httpd -p 8080 -h /tmp'
```

Synchronize the start to the next five-minute UTC boundary. This avoids a load
that straddles two partial inference buckets:

```bash
wait_seconds=$((300 - $(date -u +%s) % 300))
if [ "$wait_seconds" -eq 300 ]; then wait_seconds=0; fi
echo "Waiting ${wait_seconds}s for the next five-minute UTC boundary"
sleep "$wait_seconds"
date -u
```

Immediately start seven minutes of CPU, memory, disk, and network pressure. The
aligned start ensures at least one complete five-minute bucket is loaded:

```bash
docker exec -d demo-load sh -c 'timeout 420 sh -c "yes >/dev/null & yes >/dev/null & wait"'
docker exec -d demo-load sh -c 'dd if=/dev/zero of=/dev/shm/ml-memory.bin bs=1M count=256; sleep 420; rm -f /dev/shm/ml-memory.bin'
docker exec -d demo-load sh -c 'timeout 420 sh -c "while true; do dd if=/dev/zero of=/tmp/ml-disk.bin bs=1M count=128; sync; dd if=/tmp/ml-disk.bin of=/dev/null bs=1M; done"'
docker run -d --rm --name demo-traffic-client --network monitor-ml-net alpine sh -c 'timeout 420 sh -c "while true; do wget -q -O /dev/null http://demo-load:8080/ml-net.bin; done"'
docker stats demo-load
```

Use `128` instead of `256` for the memory file if WSL has limited memory. Exit
`docker stats` with `Ctrl+C`; the detached load continues. After seven minutes,
enqueue the service once so the just-completed bucket is evaluated without
waiting for the next periodic dispatch:

```powershell
docker compose exec backend python manage.py shell -c "from ml_model.tasks import orchestrate_service_ml; print(orchestrate_service_ml.delay('SERVICE_UUID').id)"
docker compose logs --since 15m ml_service celery_worker
```

The ML log should show `POST /infer ... 200`. Verify the actual stored decision,
not merely that the endpoint ran:

```powershell
docker compose exec backend python manage.py shell -c "from ml_model.models import AnomalyDetection as A; [print(x.service_id_id, x.is_anomaly, round(x.anomaly_score, 4), x.window_started_at, x.window_ended_at) for x in A.objects.order_by('-detected_at')[:10]]"
```

For `demo-load`, `True` is the successful anomaly-detection result. Isolation
Forest is statistical, so `False` is a valid normal decision rather than a
pipeline failure. If the first loaded window is normal, let the same combined
load cover another complete window and repeat the enqueue/check. Do not retrain:
the point is to compare loaded windows against the quiet model.

Refresh the phone. An anomalous window appears as a warning under **Overview →
Needs Attention** and **Server Detail → Anomaly History**, with the message
“Unusual service behaviour; crash not confirmed.” **Needs Attention remains
empty until a stored detection has `is_anomaly=true`; ordinary server metrics
and normal inference results are not shown there.**

### Ask Gemini about the anomaly

1. Expand the warning under **Overview → Needs Attention** or **Server Detail →
   Anomaly History**.
2. Tap **Ask AI**. The app opens the AI tab with that anomaly selected.
3. Confirm the banner says **AI advice — crash not confirmed** and the six
   stored metrics match the anomaly card.
4. Tap **What should I check first?** and send it. The response should appear
   incrementally rather than all at once.
5. Move to another tab, return to AI, select the same anomaly, and confirm the
   saved conversation reloads.

Flutter derives its `ws://...:7000/ws/...` URL from the same `API_BASE_URL` used
for HTTP. Do not add a second phone port or hard-code a WSL address. ADB reverse
carries both protocols over USB; the optional Wi-Fi firewall rule carries both
protocols over the LAN.

### Verify that a crash remains a separate lifecycle incident

Only after testing Gemini, stop the monitored container:

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
docker rm -f demo-traffic-client demo-metrics demo-load 2>/dev/null || true
docker network rm monitor-ml-net 2>/dev/null || true
sudo systemctl stop alloy
```

On Windows:

```powershell
Set-Location "C:\Users\ahmed\OneDrive\Documents\Projects\AI Incident Report and Infrastructure monitoring\Infra-Monitor"
$infraAdb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (Test-Path -LiteralPath $infraAdb) { & $infraAdb reverse --remove tcp:7000 }
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

- USB phone failure: resolve `$infraAdb` as shown in section 7, run
  `& $infraAdb devices`, and confirm the device is `device`, not
  `unauthorized`; accept the phone prompt, then recreate and list the forwarding
  rule with `& $infraAdb reverse tcp:7000 tcp:7000` and
  `& $infraAdb reverse --list`.
- Wi-Fi phone failure: first open the liveness URL in the phone browser. If it
  fails there, confirm the exact phone IP/rule, same non-guest subnet, no VPN,
  and no router AP/client isolation. If it works in the browser but not Flutter,
  fully rebuild the app and check Android Internet/cleartext permissions.
- WSL failure: confirm the generated command contains `ip route show default`;
  create a fresh enrollment and run it unchanged. The WSL NAT firewall rule does
  not need an exact address update.
- Flutter failure: confirm `frontend/.env` includes `/api` and matches the
  selected transport: `127.0.0.1` for ADB reverse or the Windows LAN IP for
  Wi-Fi. Stop and rerun Flutter after changing the bundled file.
- Enrollment failure: use a fresh token. The installer checks the dynamically
  detected gateway before consuming it and prints a bounded error instead of
  hanging.
- Missing metrics: run `grep 'url =' /etc/alloy/config.alloy` and inspect Alloy
  logs. If the URL or permissions are from an older installation, create and
  run a new enrollment for the same hostname; re-enrollment rotates the
  credential and replaces the configuration automatically. Then wait two
  scrape cycles.
- Missing ML features: confirm the target is a discovered container service and
  all six service-level series exist. Host metrics and partial rows are rejected.
- Missing artifact: inspect `celery_worker` and `ml_service` logs, verify at
  least two complete one-minute feature rows exist, then enqueue the service
  task again.
- Unauthorized ML calls: ensure `ML_SERVICE_TOKEN` is identical in
  `backend/.env` and `model/.env`, then recreate `backend`, `celery_worker`, and
  `ml_service` so they reload it.
- Celery inactivity: verify Redis is healthy and both `celery_worker` and
  `celery_beat` are running; inspect their logs for broker or task errors.
- Normal-only inference: confirm the artifact was trained during the quiet
  baseline, then repeat the combined controlled load through another complete
  five-minute bucket. A statistical test is not guaranteed to be anomalous.
- Phone does not update: pull to refresh and check the polling preference. For
  USB, confirm the ADB reverse rule still exists with
  `& $infraAdb reverse --list`. For Wi-Fi, confirm the phone
  can still reach the Windows LAN address on port 7000.
- Gemini not configured: set `GEMINI_API_KEY` in `backend/.env`, then run
  `docker compose up -d --build backend`; never put the key in Flutter.
- Gemini model/key error: inspect `docker compose logs --tail 200 backend`,
  confirm `GEMINI_MODEL=gemini-3.7-flash`, API-key validity/quota, and Docker
  outbound internet access.
- Assistant disconnected: tap **Reconnect**. A new one-time ticket is issued
  and HTTP history is reloaded; an expired ticket is never reused.
- Phone HTTP works but chat does not: confirm the backend is running Daphne,
  the URL starts with `/ws/`, and no proxy/firewall is stripping WebSocket
  upgrades on port 7000.
- No AI context: the assistant intentionally lists only `is_anomaly=true`
  detections. Normal inference windows and lifecycle-only incidents are not
  chatbot contexts.
