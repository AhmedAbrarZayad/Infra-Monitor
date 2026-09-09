#!/bin/sh

# Infra Monitor host installer
# ============================
# Enrolls a Debian/Ubuntu server, installs Grafana Alloy, writes the Alloy
# configuration supplied by the backend, and starts Alloy with systemd.
#
# Example:
#   sudo sh install.sh --token enroll_example \
#     --server https://monitoring.example.com
#
# This uses portable POSIX `sh` syntax; Bash is not required.

# Stop on the first failed command (-e) or use of an unset variable (-u). This
# helps prevent a failed installation from continuing in a partially valid state.
set -eu

# Installer settings and the standard locations used by Grafana Alloy.
PROGRAM="infra-monitor installer"
TOKEN=""
SERVER_URL=""
ALLOY_USER="alloy"
ALLOY_CONFIG_DIR="/etc/alloy"
ALLOY_DATA_DIR="/var/lib/alloy"
ALLOY_CONFIG_FILE="$ALLOY_CONFIG_DIR/config.alloy"
ALLOY_CREDENTIAL_FILE="$ALLOY_CONFIG_DIR/credential"
REQUEST_LOG_USER="infra-monitor"
REQUEST_LOG_CONFIG_DIR="/etc/infra-monitor"
REQUEST_LOG_STATE_DIR="/var/lib/infra-monitor"
REQUEST_LOG_SCRIPT="/usr/local/libexec/infra-monitor-request-forwarder.py"

# Show command usage. Exit 0 for --help and 2 for malformed arguments.
usage() {
    echo "Usage: $0 --token TOKEN --server BACKEND_URL" >&2
    exit "${1:-2}"
}

log() { printf '%s\n' "$PROGRAM: $*" >&2; }
die() { log "error: $*"; exit 1; }

# Parse each command-line option, removing it with `shift` after processing.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --token) [ "$#" -ge 2 ] || usage; TOKEN=$2; shift 2 ;;
        --server) [ "$#" -ge 2 ] || usage; SERVER_URL=${2%/}; shift 2 ;;
        -h|--help) usage 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done

# Validate everything before installing packages or writing system files.
[ -n "$TOKEN" ] || die "--token is required"
[ -n "$SERVER_URL" ] || die "--server is required"

# Fail before consuming the one-time token when the selected callback address
# is unreachable. This catches stale WSL gateways immediately.
curl --connect-timeout 5 --max-time 10 --fail --silent --show-error \
    "$SERVER_URL/api/health/live/" >/dev/null \
    || die "cannot reach backend at $SERVER_URL"
[ "$(id -u)" -eq 0 ] || die "run this installer as root (for example, with sudo)"
[ "$(uname -s)" = "Linux" ] || die "only Linux is supported"
command -v systemctl >/dev/null 2>&1 || die "systemd is required"

# Install the tools used by this script. `jq` safely creates/parses JSON, `curl`
# performs HTTPS requests, and APT/GPG verify signed package repository content.
if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends ca-certificates curl jq gpg python3
else
    die "this version supports Debian/Ubuntu hosts (apt-get is required)"
fi

# Convert Linux kernel architecture names into values understood by the API.
ARCH=$(uname -m)
case "$ARCH" in
    x86_64) API_ARCH="amd64" ;;
    aarch64|arm64) API_ARCH="arm64" ;;
    *) die "unsupported architecture: $ARCH" ;;
esac

# Report the distribution name (such as "ubuntu") during enrollment. `linux`
# is retained as a safe fallback when /etc/os-release does not exist.
OS_NAME="linux"
if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_NAME=${ID:-linux}
fi

# The backend includes Docker collection components only when Docker is present.
DOCKER_AVAILABLE=false
if command -v docker >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
fi

# Use an isolated directory for the enrollment response and generated config.
# The trap removes these sensitive temporary files on exit or interruption.
TMP_DIR=$(mktemp -d)
RESPONSE_FILE="$TMP_DIR/enrollment.json"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT HUP INT TERM

# Construct JSON with jq so hostnames or tokens containing special characters
# cannot produce invalid JSON. Tenant identity must come from the token on the
# backend; this request intentionally sends no organization identifier.
PAYLOAD=$(jq -n \
    --arg token "$TOKEN" \
    --arg hostname "$(hostname)" \
    --arg os "$OS_NAME" \
    --arg architecture "$API_ARCH" \
    --arg server_url "$SERVER_URL" \
    --argjson docker_available "$DOCKER_AVAILABLE" \
    '{token:$token, hostname:$hostname, os:$os, architecture:$architecture, docker_available:$docker_available, server_url:$server_url}')

# Exchange the short-lived, one-time token for an enrollment ID, permanent
# write-only server credential, and server-specific Alloy configuration.
# The JSON body is saved in a file while the variable captures only the HTTP
# status. Following redirects supports a canonical HTTPS API URL.
log "enrolling host"
HTTP_CODE=$(curl --connect-timeout 5 --max-time 30 --silent --show-error --location \
    --output "$RESPONSE_FILE" --write-out '%{http_code}' \
    --header 'Content-Type: application/json' \
    --data "$PAYLOAD" \
    "$SERVER_URL/api/internal/monitoring/enroll/") || die "enrollment request failed"

# Accept any successful 2xx response. Otherwise extract a safe public error
# message from the backend response and stop.
case "$HTTP_CODE" in
    2??) ;;
    *)
        MESSAGE=$(jq -r '.detail // .message // "enrollment was rejected"' "$RESPONSE_FILE" 2>/dev/null || true)
        die "backend returned HTTP $HTTP_CODE: $MESSAGE"
        ;;
esac

# `jq -e` makes a missing/null required field an error. The alternatives support
# both response field names currently mentioned in the project documentation.
ENROLLMENT_ID=$(jq -er '.enrollment_id' "$RESPONSE_FILE") || die "response has no enrollment_id"
SERVER_ID=$(jq -er '.server_id' "$RESPONSE_FILE") || die "response has no server_id"
CREDENTIAL=$(jq -er '.credential // .server_credential' "$RESPONSE_FILE") || die "response has no server credential"
jq -er '.config // .alloy_config' "$RESPONSE_FILE" > "$TMP_DIR/config.alloy" || die "response has no Alloy configuration"

# Report authenticated installer progress without making callback availability
# a prerequisite for installing a healthy collector.
report_status() {
    STATUS_PAYLOAD=$(jq -n --arg stage "$1" '{stage:$stage}')
    curl --connect-timeout 5 --max-time 10 --silent --show-error --fail \
        --header "Authorization: Bearer $CREDENTIAL" \
        --header 'Content-Type: application/json' \
        --data "$STATUS_PAYLOAD" \
        "$SERVER_URL/api/internal/monitoring/enrollments/$ENROLLMENT_ID/status/" >/dev/null \
        || log "warning: could not report installer stage $1"
}

report_status INSTALLER_STARTED

# Add Grafana's official repository. The dedicated keyring and `signed-by`
# restriction ensure this signing key is used only for Grafana packages.
log "installing Grafana Alloy from Grafana's signed APT repository"
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/grafana.gpg
printf '%s\n' 'deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main' \
    > /etc/apt/sources.list.d/grafana.list
apt-get update
apt-get install -y alloy acl
report_status COLLECTOR_INSTALLED

# Run Alloy as a dedicated, non-login account instead of root. The package will
# usually create this account already, so user creation is conditional.
id "$ALLOY_USER" >/dev/null 2>&1 || useradd --system --home "$ALLOY_DATA_DIR" --shell /usr/sbin/nologin "$ALLOY_USER"
install -d -o root -g "$ALLOY_USER" -m 0750 "$ALLOY_CONFIG_DIR"
install -d -o "$ALLOY_USER" -g "$ALLOY_USER" -m 0750 "$ALLOY_DATA_DIR"

# Root owns the configuration and credential. Group-read permission lets only
# the Alloy service consume them; the permanent credential is never displayed.
install -o root -g "$ALLOY_USER" -m 0640 "$TMP_DIR/config.alloy" "$ALLOY_CONFIG_FILE"
printf '%s' "$CREDENTIAL" > "$ALLOY_CREDENTIAL_FILE"
chown root:"$ALLOY_USER" "$ALLOY_CREDENTIAL_FILE"
chmod 0640 "$ALLOY_CREDENTIAL_FILE"

# Install the access-log forwarder separately from Alloy. Alloy's Loki writer
# cannot send the JSON request-log contract used by the backend.
id "$REQUEST_LOG_USER" >/dev/null 2>&1 || useradd --system --home "$REQUEST_LOG_STATE_DIR" --shell /usr/sbin/nologin "$REQUEST_LOG_USER"
usermod -aG "$ALLOY_USER" "$REQUEST_LOG_USER"
if getent group adm >/dev/null 2>&1; then
    usermod -aG adm "$REQUEST_LOG_USER"
fi
install -d -o root -g "$REQUEST_LOG_USER" -m 0750 "$REQUEST_LOG_CONFIG_DIR" "$REQUEST_LOG_STATE_DIR"
install -d -o root -g root -m 0755 "$(dirname "$REQUEST_LOG_SCRIPT")"
cat > "$REQUEST_LOG_SCRIPT" <<'PYTHON'
#!/usr/bin/env python3
import json
import os
import re
import time
import urllib.request
from datetime import datetime

LOG_PATH = os.environ.get("ACCESS_LOG_PATH", "/var/log/nginx/access.log")
ENDPOINT = os.environ["REQUEST_LOG_ENDPOINT"]
CREDENTIAL_FILE = os.environ["REQUEST_LOG_CREDENTIAL_FILE"]
SERVER_ID = os.environ["REQUEST_LOG_SERVER_ID"]
STATE_FILE = os.environ.get("REQUEST_LOG_STATE_FILE", "/var/lib/infra-monitor/access-log.offset")
BATCH_SIZE = 100
LINE = re.compile(r'^(?P<ip>\S+) \S+ \S+ \[(?P<date>[^]]+)\] "(?P<method>\S+) (?P<target>\S+) (?P<protocol>\S+)" (?P<status>\d{3}) (?P<size>\d+|-) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"(?: (?P<seconds>[\d.]+))?')


def offset():
    try:
        return int(open(STATE_FILE, encoding="ascii").read())
    except (FileNotFoundError, ValueError):
        return 0


def save_offset(value):
    temporary = STATE_FILE + ".tmp"
    with open(temporary, "w", encoding="ascii") as handle:
        handle.write(str(value))
    os.replace(temporary, STATE_FILE)


def parse(line):
    match = LINE.match(line)
    if not match:
        return None
    values = match.groupdict()
    target = values["target"].split("?", 1)
    timestamp = datetime.strptime(values["date"], "%d/%b/%Y:%H:%M:%S %z").isoformat()
    return {
        "timestamp": timestamp,
        "source_ip": values["ip"],
        "method": values["method"],
        "path": target[0],
        "query_string": target[1] if len(target) == 2 else "",
        "protocol": values["protocol"],
        "status_code": int(values["status"]),
        "content_length": None if values["size"] == "-" else int(values["size"]),
        "response_time_ms": float(values["seconds"]) * 1000 if values["seconds"] else None,
        "referer": values["referer"],
        "user_agent": values["agent"],
    }


def send(entries):
    with open(CREDENTIAL_FILE, encoding="ascii") as handle:
        credential = handle.read().strip()
    body = json.dumps({"server_id": SERVER_ID, "entries": entries}).encode()
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Authorization": "Bearer " + credential, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status >= 300:
            raise RuntimeError("ingestion returned HTTP " + str(response.status))


def run_once():
    if not os.path.exists(LOG_PATH):
        return
    current = os.path.getsize(LOG_PATH)
    position = offset()
    if position > current:
        position = 0
    entries = []
    with open(LOG_PATH, "rb") as handle:
        handle.seek(position)
        for raw_line in handle:
            position = handle.tell()
            entry = parse(raw_line.decode("utf-8", "replace").rstrip("\n"))
            if entry:
                entries.append(entry)
            if len(entries) == BATCH_SIZE:
                send(entries)
                entries = []
    if entries:
        send(entries)
    save_offset(position)


while True:
    try:
        run_once()
    except Exception as error:
        print("request-log-forwarder: " + str(error), flush=True)
    time.sleep(5)
PYTHON
chmod 0755 "$REQUEST_LOG_SCRIPT"
cat > "$REQUEST_LOG_CONFIG_DIR/forwarder.env" <<EOF
REQUEST_LOG_ENDPOINT=$SERVER_URL/api/internal/request-logs/
REQUEST_LOG_CREDENTIAL_FILE=$ALLOY_CREDENTIAL_FILE
REQUEST_LOG_SERVER_ID=$SERVER_ID
REQUEST_LOG_STATE_FILE=$REQUEST_LOG_STATE_DIR/access-log.offset
ACCESS_LOG_PATH=/var/log/nginx/access.log
EOF
chown root:"$REQUEST_LOG_USER" "$REQUEST_LOG_CONFIG_DIR/forwarder.env"
chmod 0640 "$REQUEST_LOG_CONFIG_DIR/forwarder.env"

cat > /etc/systemd/system/infra-monitor-request-forwarder.service <<EOF
[Unit]
Description=Infra Monitor Request Shield access-log forwarder
Wants=network-online.target
After=network-online.target

[Service]
User=$REQUEST_LOG_USER
Group=$REQUEST_LOG_USER
SupplementaryGroups=$ALLOY_USER
EnvironmentFile=$REQUEST_LOG_CONFIG_DIR/forwarder.env
ExecStart=/usr/bin/python3 $REQUEST_LOG_SCRIPT
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=$REQUEST_LOG_STATE_DIR

[Install]
WantedBy=multi-user.target
EOF

# Docker is optional. Docker-group membership enables container discovery, but
# access to the Docker socket is effectively root-equivalent, so this is logged
# explicitly. Without Docker, Alloy can still collect host metrics.
if command -v docker >/dev/null 2>&1 && getent group docker >/dev/null 2>&1; then
    log "Docker detected; granting Alloy Docker-socket access (effectively root-equivalent)"
    usermod -aG docker "$ALLOY_USER"

    # cAdvisor also opens containerd when Docker uses the overlayfs storage
    # driver. Grant only the Alloy account socket access now and after future
    # containerd restarts instead of running the whole collector as root.
    if [ -S /run/containerd/containerd.sock ]; then
        setfacl -m "u:$ALLOY_USER:rw" /run/containerd/containerd.sock
        install -d -m 0755 /etc/systemd/system/containerd.service.d
        cat > /etc/systemd/system/containerd.service.d/infra-monitor-alloy-access.conf <<'EOF'
[Service]
ExecStartPost=/usr/bin/setfacl -m u:alloy:rw /run/containerd/containerd.sock
EOF
    fi
else
    log "Docker unavailable; host monitoring will still be enabled"
fi

# Create the systemd service. Important directives below run Alloy as its own
# user, restart it after failures, make the system filesystem read-only, and
# permit writes only in /var/lib/alloy. Quoting 'EOF' prevents shell expansion
# while this unit file is being written.
cat > /etc/systemd/system/alloy.service <<'EOF'
[Unit]
Description=Grafana Alloy telemetry collector
# Do not start collection until the host has usable networking.
Wants=network-online.target
After=network-online.target

[Service]
# Apply least privilege: Alloy does not run as the root user.
User=alloy
Group=alloy
# Added only when the Docker group exists; it enables Docker socket access.
SupplementaryGroups=docker
# Run the backend-generated config and persist Alloy state under /var/lib.
ExecStart=/usr/bin/alloy run --storage.path=/var/lib/alloy /etc/alloy/config.alloy
# Recover automatically if Alloy crashes or exits unexpectedly.
Restart=always
RestartSec=5
# Basic systemd sandboxing. Alloy can read the host but can write only its state.
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/alloy

[Install]
# `systemctl enable` attaches this service to the normal server boot target.
WantedBy=multi-user.target
EOF

# Remove the optional Docker group when it does not exist; systemd treats an
# unknown SupplementaryGroups entry as a startup error.
if ! getent group docker >/dev/null 2>&1; then
    sed -i '/^SupplementaryGroups=docker$/d' /etc/systemd/system/alloy.service
fi

# Reload systemd, start Alloy now, enable it after reboot, and verify it stayed
# active long enough to catch immediate configuration/permission errors.
systemctl daemon-reload
systemctl enable --now alloy
systemctl is-active --quiet alloy || die "Alloy failed to start; inspect: journalctl -u alloy"
systemctl enable --now infra-monitor-request-forwarder
systemctl is-active --quiet infra-monitor-request-forwarder || die "Request-log forwarder failed to start; inspect: journalctl -u infra-monitor-request-forwarder"

# Report progress using the permanent server credential. This callback helps the
# UI, but actual metric arrival is the authoritative health signal. Therefore a
# callback failure produces a warning instead of stopping an operational Alloy.
# The credential determines server and organization identity; the callback body
# deliberately contains neither value.
report_status COLLECTOR_STARTED

log "installation complete; Alloy and Request Shield access-log forwarder are running"
