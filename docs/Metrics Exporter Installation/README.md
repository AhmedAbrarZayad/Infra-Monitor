# Comprehensive Project Plan: Multi-Tenant SaaS Infrastructure Monitoring Platform

## 1. Executive Summary
This document details the complete architecture, implementation strategy, and local simulation plan for a multi-tenant SaaS infrastructure monitoring platform. The system is built on a **Docker-first, edge-push telemetry model**. Instead of the central server trying to reach into customer networks (which fails due to firewalls), customer servers run a lightweight collector that automatically discovers their applications and pushes metrics to our central platform. This provides a "zero-touch" onboarding experience via a single shell command, ensuring strict data isolation and high scalability.

---

## 2. System Architecture Overview

The architecture is strictly divided into two zones: the **Central SaaS Platform** (controlled by us) and the **Customer Edge Environment** (controlled by the customer).

### 2.1 Central SaaS Platform
1. **Flutter UI**: The customer-facing frontend. It generates single-use enrollment tokens, displays the installation command, and polls the backend to show real-time onboarding progress.
2. **Django REST Framework Backend**: The control-plane orchestration service. It handles user and organization authorization, enrollment-token creation, token validation, server registration, dynamic configuration generation, enrollment progress, and organization-scoped query APIs. It does not proxy the high-volume metrics data plane.
3. **PostgreSQL**: The relational database storing organizations, server metadata, ephemeral enrollment tokens, and hashed permanent server credentials.
4. **VictoriaMetrics Cluster (Proposed Later)**: A Prometheus-compatible time-series database that will be added after the enrollment control plane is established. Its native tenant routes will isolate metrics by an internal numeric account/project identifier. The current repository still uses Prometheus and does not yet contain VictoriaMetrics.
5. **vmauth or a Dedicated Ingestion Gateway (Proposed Later)**: The metrics data-plane entry point. It authenticates a server-scoped credential, resolves it to a trusted VictoriaMetrics tenant, removes or overwrites identity labels supplied by the edge, and routes the request to the correct VictoriaMetrics tenant path.

### 2.2 Customer Edge Environment
1. **Docker Compose**: The customer runs their backend applications in Docker. These containers are tagged with a specific metadata label (e.g., `monitoring.enabled=true`) to signal they should be monitored.
2. **Grafana Alloy**: A single-binary telemetry collector installed on the host via our automated script. It always collects supported host metrics. When Docker is available and permission is granted, it also collects container-resource metrics and discovers explicitly tagged application-metrics endpoints. It applies useful identity labels and pushes data outward over HTTPS. Those edge labels are not trusted as the tenant security boundary.

---

## 3. The "Zero-Touch" Onboarding Flow

This is the end-to-end lifecycle of a customer adding a server to the platform:

1. **Token Generation**: The user logs into the Flutter UI and clicks "Add Server". The UI requests a single-use, short-lived enrollment token from the backend.
2. **Command Execution**: The UI displays a one-line `curl` command containing the token. The user copies and pastes this into their target Linux server's terminal.
3. **Automated Installation**: The shell script downloads, validates the Linux environment, detects whether Docker is available, and exchanges the temporary token for permanent credentials and a custom configuration file. Missing Docker disables container monitoring but does not prevent host monitoring.
4. **Service Initialization**: The script installs the Grafana Alloy binary, writes the secure configuration, sets up a `systemd` service, and starts the collector.
5. **Telemetry Flow**: Alloy collects host metrics and, when Docker is available, container resource metrics. Tagged containers may additionally expose application-specific `/metrics` endpoints for Alloy to discover and scrape. Alloy sends Prometheus `remote_write` data to the ingestion gateway, which authenticates the server credential and routes the payload to the trusted VictoriaMetrics tenant.
6. **UI Confirmation**: The Flutter UI polls the backend, detects the incoming metrics, and updates the screen to "Server Connected".

---

## 4. Component Implementation Details

### 4.1 The Automated Installation Script
Hosted on our backend, this shell script is the bridge between the user's terminal and our SaaS. Its logic follows these steps:
* **Pre-flight Checks**: Verifies Linux distribution, architecture, required command-line tools, network access, available service manager, and installation permissions. Docker is optional: if it is unavailable, the installer enables host monitoring and reports that container monitoring was skipped.
* **Argument Parsing**: Reads the `--token` and `--server` (backend URL) arguments.
* **Secure Handshake**: Makes an HTTP POST request to the backend's enrollment endpoint, passing the token and local system metadata (hostname, OS, architecture).
* **Asset Deployment**: Receives the permanent server credential and the dynamically generated HCL configuration. It writes the credential to a strictly restricted file and writes the configuration to the Alloy directory. Downloaded Alloy releases and the installer itself must have their signature or checksum verified before execution.
* **Permission Setup**: Runs Alloy as a dedicated service user. For Docker monitoring, the installer can add that user to the Docker group or apply explicitly supported access controls. Because Docker-socket access is effectively privileged, the installer must display and record that security implication. Running Alloy as root or as a privileged container is an explicit fallback, not the silent default.
* **Systemd Integration**: Creates a systemd service file to ensure the collector runs in the background, survives reboots, and automatically restarts on failure.
* **Progress Reporting**: Reports coarse installation stages to the backend using the permanent server credential. Metric arrival remains the authoritative proof that monitoring works.

### 4.2 Backend API Design
The Django REST Framework control plane and the metrics gateway expose the following endpoints:

1. **Create Enrollment (`POST /api/organizations/{organization_id}/monitoring/enrollments/`)**:
   * **Authentication**: User JWT. Only an approved `OWNER` or `ADMIN` membership may create an enrollment.
   * **Input**: Server display name, environment, and any safe installation options.
   * **Logic**: Creates a single-use, short-lived token tied to the authenticated organization and actor. The organization is taken from the scoped URL and verified membership, never from an arbitrary request-body field.
   * **Output**: Returns `enrollment_id`, the one-time token, expiry, and the installation command displayed by Flutter.

2. **Enrollment Endpoint (`POST /api/internal/monitoring/enroll/`)**:
   * **Input**: Receives the single-use enrollment token and host metadata.
   * **Logic**: Validates and consumes the token transactionally, derives the organization from the stored token, creates a new organization-owned Server record, and generates a permanent write-only credential scoped to that server. It generates the Grafana Alloy configuration tailored to that server identity.
   * **Output**: Returns the enrollment ID, permanent credential, server ID, ingestion URL, and configuration. The permanent credential is returned only during this exchange and is stored hashed by the platform.

3. **Installation Progress Callback (`POST /api/internal/monitoring/enrollments/{enrollment_id}/status/`)**:
   * **Authentication**: Permanent server credential after enrollment; the enrollment token may report only the initial accepted stage during its exchange.
   * **Input**: A bounded stage such as `INSTALLER_STARTED`, `COLLECTOR_INSTALLED`, `COLLECTOR_STARTED`, or `FAILED`, plus a sanitized diagnostic message.
   * **Logic**: Confirms that the credential belongs to the enrollment's server and stores the latest stage. It does not accept organization or server identity from the body.
   * **Output**: Returns the accepted stage and timestamp.

4. **Organization-Scoped Status Polling (`GET /api/organizations/{organization_id}/monitoring/enrollments/{enrollment_id}/`)**:
   * **Authentication**: User JWT with an approved membership in the scoped organization.
   * **Logic**: Retrieves the enrollment only inside that organization and combines installer progress with the timestamp of the first accepted metric batch.
   * **Output**: Returns expiry, coarse installation stage, connection state, sanitized failure information, server ID when registered, and whether first metrics have arrived. A cross-organization enrollment ID returns `404`.

5. **Metrics Ingestion Gateway (`POST /api/metrics/write`)**:
   * **Input**: Receives the raw Prometheus `remote_write` payload from the customer's Alloy collector, authenticated via the permanent server credential.
   * **Ownership Logic**: Resolves the server credential to the platform's trusted server, organization, and internal numeric VictoriaMetrics account/project ID. Edge-provided organization/server labels are removed, validated, or overwritten; they never choose the storage tenant.
   * **Routing Logic**: Streams the compressed payload through vmauth or a dedicated data-plane gateway to the cluster tenant route, for example `/insert/{account_id}:{project_id}/prometheus/api/v1/write`. Django is not placed in the high-volume payload-forwarding path.
   * **Output**: Returns the appropriate remote-write status and updates coarse ingestion health asynchronously. Authentication failures reveal no organization information.

6. **Organization-Scoped Metrics Query APIs**:
   * **Input**: User JWT, scoped organization URL, authorized server/service identifiers, time range, and metric selection.
   * **Logic**: Django resolves the organization to its trusted VictoriaMetrics tenant and queries the corresponding `/select/{account_id}:{project_id}/prometheus/...` route. Flutter never supplies or accesses the underlying tenant ID directly.
   * **Output**: Returns bounded, normalized data for the Overview, Servers, Incidents, and Analytics APIs.

### 4.3 Dynamic Configuration Generation
Instead of giving every customer the same static config, the backend generates a custom Grafana Alloy configuration on the fly. This configuration instructs Alloy to:
1. Collect host CPU, memory, disk, and network metrics using its Unix/node-exporter-compatible component.
2. If Docker is available, connect to the local Docker runtime and collect cAdvisor container-resource metrics. cAdvisor observes accessible containers regardless of whether their applications expose a `/metrics` endpoint.
3. Separately use Docker discovery to find containers labeled `monitoring.enabled=true` and scrape their application-specific Prometheus endpoints.
4. Add `organization_id`, `server_id`, environment, and service labels for querying and diagnostics. These labels are hints until the ingestion gateway validates or overwrites them using the server credential.
5. Push the data over HTTPS to the metrics ingestion gateway using the permanent credential.

Application containers that expose custom metrics use labels such as:

```yaml
services:
  payments-api:
    labels:
      monitoring.enabled: "true"
      monitoring.metrics_port: "8000"
      monitoring.metrics_path: "/metrics"
      monitoring.service_name: "payments-api"
```

Stopping a container does not delete its service or historical metrics. The platform changes the service to `OFFLINE` or `STALE` after the configured last-seen threshold and retains its history.

### 4.4 Flutter UI & State Management
The Flutter application manages the onboarding state machine. It creates the enrollment through the active organization's scoped endpoint and polls that same organization's enrollment resource every few seconds. It presents coarse, trustworthy stages such as "Waiting for installation", "Collector started", "Waiting for first metrics", "Connected", "Expired", or "Failed". Detailed installer stages appear only when the authenticated installer callback has actually reported them.

---

## 5. Security & Multi-Tenancy Strategy

Data isolation and security are baked into the architecture at every layer:

1. **Single-Use Tokens**: Enrollment tokens expire quickly and can only be used once, preventing replay attacks.
2. **Server-Side Trust**: The backend derives the organization from the validated token in PostgreSQL. It completely ignores any organization ID the installer might pass in the JSON payload, preventing cross-tenant spoofing.
3. **Untrusted Edge Labels**: Tenant and server labels stamped at the edge are useful metadata, but a customer with root access can edit them. The ingestion gateway removes, validates, or overwrites them using identity resolved from the permanent server credential.
4. **Scoped Credentials**: The permanent credential given to the collector is strictly scoped. It can only write metrics; it cannot read data or alter configurations.
5. **TSDB Isolation**: The gateway routes writes to a trusted VictoriaMetrics cluster tenant path such as `/insert/{account_id}:{project_id}/prometheus/api/v1/write`. Django routes reads through the corresponding trusted select tenant. The public organization UUID is mapped internally and is not trusted as a raw TSDB tenant selector.
6. **Control/Data Plane Separation**: Django owns authorization, enrollment, metadata, and query orchestration. vmauth or a dedicated gateway handles compressed high-volume remote-write traffic, preventing the application API from becoming a telemetry bottleneck.
7. **Collector Privilege Disclosure**: Docker-socket access can grant root-equivalent control. The installer uses a dedicated service user, grants only the selected supported access, and clearly discloses the risk before enabling Docker collection.

---

## 6. Local Simulation & Testing Blueprint

To validate this distributed system for the academic project, we will simulate the entire environment on a single physical laptop.

### 6.1 Simulation Topology
* **Host Machine (Central SaaS)**: Runs the Django REST Framework backend, Flutter UI, and PostgreSQL. The current repository also runs Prometheus; the proposed later phase adds VictoriaMetrics cluster plus vmauth or a dedicated ingestion gateway through Docker Compose. Public enrollment and ingestion endpoints must listen on an address reachable from the VMs (for example, the host's LAN address), not only `localhost`.
* **Virtual Machine 1 (Customer A)**: Simulates a server running **two** backend applications (e.g., API and Worker) via Docker Compose.
* **Virtual Machine 2 (Customer B)**: Simulates a server running **one** backend application.
* **Virtual Machine 3 (Customer C)**: Simulates a server running **one** backend application.

*Tooling*: We will use Multipass to rapidly provision lightweight Ubuntu VMs and install Docker on each.

### 6.2 Execution & Verification Plan
1. **Deploy Dummy Apps**: On each VM, deploy simple Python applications that expose a Prometheus `/metrics` endpoint. Tag them with `monitoring.enabled`, metrics port/path, and stable service-name labels. Customer A deploys two; B and C deploy one. Alloy's cAdvisor component collects resource metrics for accessible containers independently of these application-scrape labels.
2. **Run Onboarding**: Generate tokens in the Flutter UI for Org A, B, and C. SSH into each VM and execute the one-line installation script, pointing to the Host's IP.
3. **Test Multi-Tenancy**: Log into the UI as Org A. Verify the dashboard shows its host and exactly two application-metric sources. Log out, log in as Org B, and verify only its single application-metric source is visible. This proves credential-based gateway routing, tenant-scoped TSDB storage, and Django's organization-scoped queries are consistently isolating data.
4. **Test Auto-Discovery and Lifecycle**: SSH into Customer A's VM and stop one dummy container. Verify current samples become stale and the service changes to `OFFLINE` after the last-seen threshold, while its historical metrics and incidents remain available. Restart it and verify the same service returns to `HEALTHY` instead of creating a duplicate.

---

## 7. Key Academic & Architectural Defense Points

When presenting this project, emphasize these decisions to demonstrate senior-level engineering maturity:

1. **Push vs. Pull Telemetry**: Traditional Prometheus uses a "Pull" model, which fails in SaaS because customer servers are behind NATs/firewalls. Our "Push" model (`remote_write`) requires zero inbound firewall rules on the customer side, mirroring industry leaders like Datadog and Grafana Cloud.
2. **Docker-First Auto-Discovery**: By leveraging Docker Service Discovery, we eliminate the need for users to manually configure IP addresses and ports. The system automatically adapts to container restarts and IP changes.
3. **Dynamic Configuration**: Generating the collector configuration through Django makes the system adaptable while keeping tenant and server assignment under control-plane authorization.
4. **Credential-Based Multi-Tenancy**: The ingestion gateway derives the VictoriaMetrics tenant route from a server-scoped credential. Edge labels cannot redirect samples into another organization's tenant.
5. **Control/Data Plane Separation**: Django manages users, organizations, enrollments, metadata, and authorized queries; the ingestion gateway and VictoriaMetrics handle telemetry throughput.
6. **Supply Chain Security**: The installer uses single-use tokens, restricts credential file permissions (`chmod 600`), verifies installer/collector signatures or checksums, and avoids executing unverified remote scripts directly in memory.
7. **Safe Service Lifecycle**: Container disappearance changes current health but never destroys service identity, historical telemetry, alerts, or incident evidence.
