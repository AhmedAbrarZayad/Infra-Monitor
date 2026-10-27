param(
    [string]$OrganizationId = "",
    [string]$ServerId = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required. Start Docker Desktop and run this script from the repository root."
}

$python = @'
from datetime import timedelta
import httpx
from django.utils import timezone
from accounts.models import Organization
from servers.models import Servers
from servers.services import MonitoringCredentialService
from sanitize.models import RequestLog, ShieldConfig
from sanitize.services import classify_pending_batch, generate_threat_suggestions

organization_id = "__ORGANIZATION_ID__"
server_id = "__SERVER_ID__"

organizations = Organization.objects.order_by("name", "id")
if organization_id:
    organization = Organization.objects.get(pk=organization_id)
elif organizations.count() == 1:
    organization = organizations.first()
else:
    print("Organizations:")
    for item in organizations:
        print(f"  {item.id}  {item.name}")
    raise SystemExit("Pass -OrganizationId when more than one organization exists.")

servers = Servers.objects.filter(organization=organization).order_by("name", "server_id")
if server_id:
    server = servers.get(pk=server_id)
elif servers.count() == 1:
    server = servers.first()
else:
    print(f"Servers in {organization.name}:")
    for item in servers:
        print(f"  {item.server_id}  {item.name}  {item.host_name}  {item.status}")
    raise SystemExit("Pass -ServerId when more than one server exists.")

try:
    connection = server.monitoring_connection
except Exception as exc:
    raise SystemExit("The selected server has no monitoring connection.") from exc

if connection.status == "DISCONNECTED":
    raise SystemExit("The selected server monitoring connection is disconnected.")

# Raw credentials are intentionally not recoverable from the database.
# Rotate a test credential so this script is self-contained and repeatable.
MonitoringCredentialService.revoke_all(connection)
_, raw_credential = MonitoringCredentialService.issue(
    connection,
    actor=server.registered_by,
)

ShieldConfig.objects.update_or_create(
    organization=organization,
    defaults={
        "enabled": True,
        "platform_self_monitor": True,
        "gemini_escalation": False,
        "red_suggestion_threshold": 1,
        "gray_suggestion_threshold": 1,
        "suggestion_window_minutes": 60,
    },
)

now = timezone.now()
payload = {
    "server_id": str(server.server_id),
    "entries": [
        {
            "timestamp": now.isoformat(),
            "source_ip": "203.0.113.50",
            "method": "GET",
            "path": "/search",
            "query_string": "q=normal",
            "status_code": 200,
            "user_agent": "Mozilla/5.0 RequestShieldExternalTest",
            "content_length": 512,
            "response_time_ms": 35.5,
            "referer": "https://example.test/",
            "protocol": "HTTP/1.1",
            "headers_digest": {},
        },
        {
            "timestamp": (now + timedelta(seconds=5)).isoformat(),
            "source_ip": "203.0.113.51",
            "method": "GET",
            "path": "/search",
            "query_string": "q=%27%20OR%201%3D1--",
            "status_code": 200,
            "user_agent": "sqlmap/1.7 RequestShieldExternalTest",
            "content_length": 512,
            "response_time_ms": 42.0,
            "referer": "https://example.test/",
            "protocol": "HTTP/1.1",
            "headers_digest": {},
        },
    ],
}

response = httpx.post(
    "http://127.0.0.1:8000/api/internal/request-logs/",
    json=payload,
    headers={"Authorization": f"Bearer {raw_credential}"},
    timeout=15,
)
print(f"Organization: {organization.name} ({organization.id})")
print(f"Server: {server.name} ({server.server_id})")
print(f"Ingestion status: {response.status_code}")
print(f"Ingestion response: {response.text}")
response.raise_for_status()

classified = classify_pending_batch(organization.id, batch_size=100)
logs = list(
    RequestLog.objects.filter(
        server=server,
        source=RequestLog.Source.EXTERNAL,
        created_at__gte=now - timedelta(minutes=1),
    ).order_by("created_at")
)

print(f"Classified in this run: {classified}")
for log in logs:
    print(
        "External log: "
        f"ip={log.source_ip} path={log.path} zone={log.zone} "
        f"confidence={log.confidence} classifier={log.classified_by} "
        f"signals={log.threat_signals}"
    )

suggestions = generate_threat_suggestions(organization.id)
print(f"Threat suggestions created: {suggestions}")

if len(logs) != 2 or any(log.zone == RequestLog.Zone.UNCLASSIFIED for log in logs):
    raise SystemExit("Request Shield external test failed: logs were not classified.")

print("Request Shield external test passed.")
print("Note: the previous server credential was revoked and a fresh test credential was issued.")
'@

$python = $python.Replace("__ORGANIZATION_ID__", $OrganizationId)
$python = $python.Replace("__SERVER_ID__", $ServerId)
$python | docker compose exec -T backend python manage.py shell
if ($LASTEXITCODE -ne 0) {
    throw "Request Shield external test failed."
}
