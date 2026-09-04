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
[ "$(id -u)" -eq 0 ] || die "run this installer as root (for example, with sudo)"
[ "$(uname -s)" = "Linux" ] || die "only Linux is supported"
command -v systemctl >/dev/null 2>&1 || die "systemd is required"

# Install the tools used by this script. `jq` safely creates/parses JSON, `curl`
# performs HTTPS requests, and APT/GPG verify signed package repository content.
if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends ca-certificates curl jq gpg
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
    --argjson docker_available "$DOCKER_AVAILABLE" \
    '{token:$token, hostname:$hostname, os:$os, architecture:$architecture, docker_available:$docker_available}')

# Exchange the short-lived, one-time token for an enrollment ID, permanent
# write-only server credential, and server-specific Alloy configuration.
# The JSON body is saved in a file while the variable captures only the HTTP
# status. Following redirects supports a canonical HTTPS API URL.
log "enrolling host"
HTTP_CODE=$(curl --silent --show-error --location \
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
CREDENTIAL=$(jq -er '.credential // .server_credential' "$RESPONSE_FILE") || die "response has no server credential"
jq -er '.config // .alloy_config' "$RESPONSE_FILE" > "$TMP_DIR/config.alloy" || die "response has no Alloy configuration"

# Report authenticated installer progress without making callback availability
# a prerequisite for installing a healthy collector.
report_status() {
    STATUS_PAYLOAD=$(jq -n --arg stage "$1" '{stage:$stage}')
    curl --silent --show-error --fail \
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
apt-get install -y alloy
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

# Docker is optional. Docker-group membership enables container discovery, but
# access to the Docker socket is effectively root-equivalent, so this is logged
# explicitly. Without Docker, Alloy can still collect host metrics.
if command -v docker >/dev/null 2>&1 && getent group docker >/dev/null 2>&1; then
    log "Docker detected; granting Alloy Docker-socket access (effectively root-equivalent)"
    usermod -aG docker "$ALLOY_USER"
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

# Report progress using the permanent server credential. This callback helps the
# UI, but actual metric arrival is the authoritative health signal. Therefore a
# callback failure produces a warning instead of stopping an operational Alloy.
# The credential determines server and organization identity; the callback body
# deliberately contains neither value.
report_status COLLECTOR_STARTED

log "installation complete; Alloy is running"
