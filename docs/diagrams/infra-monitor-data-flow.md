# Infra Monitor Data Flow Diagram

This document describes the current deployed architecture and the movement of
control-plane data, telemetry, logs, machine-learning data, and AI messages.

The diagram follows the implementation in `docker-compose.yml`, Django root
routing, the installer, the ML service, and the Flutter data sources. PostgreSQL
stores application and request-event state. VictoriaMetrics stores numeric
time-series samples and is queried through Django; the Flutter client does not
connect to VictoriaMetrics directly.

## Level 0: System Context

```mermaid
flowchart LR
    User["Owner / Admin / Engineer"]
    Host["Monitored Linux host\nHTTP services / Docker"]
    App["Infra Monitor platform"]
    Gemini["Google Gemini API"]
    Release["Offline ML release process"]

    User -->|"JWT REST requests\nAI WebSocket messages"| App
    Host -->|"Enrollment, metrics, access-log batches"| App
    App -->|"Gray-zone review prompts\nAnomaly assistant prompts"| Gemini
    Gemini -->|"Classifications and streamed answers"| App
    Release -->|"Approved model.joblib + metadata.json"| App
```

## Modeling Approach

The primary decomposition is by feature/data plane because each feature has a
different source, processing path, and persistence boundary. Human roles are
shown where they initiate or authorize a flow:

- **Owner** creates organizations, manages memberships, and controls privileged
  monitoring configuration.
- **Admin** manages approved organization operations and monitoring workflows.
- **Engineer** requests membership and uses approved operational data.
- **System actors** such as host collectors, Celery, the ML service, and Gemini
  carry data between services without being organization members.

Feature-based chunks are clearer than one role-only diagram because metrics,
access logs, asynchronous jobs, and model releases are primarily system-driven.

## Feature DFD 1: Identity and Organization Access

```mermaid
flowchart LR
    Owner["Owner"]
    Admin["Admin"]
    Engineer["Engineer"]
    Flutter["Flutter client"]
    Auth["Django accounts APIs\nJWT, organizations, memberships"]
    Roles["Membership authorization\nOWNER / ADMIN / ENGINEER"]
    PG[("PostgreSQL\nusers, organizations, memberships")]

    Owner -->|"Create organization\nmanage members"| Flutter
    Admin -->|"Approved organization operations"| Flutter
    Engineer -->|"Login, membership request\napproved operational access"| Flutter
    Flutter -->|"JWT-authenticated REST"| Auth
    Auth --> Roles
    Roles -->|"Role and organization checks"| Auth
    Auth -->|"Identity and membership state"| PG
    PG -->|"Authorized identity context"| Auth
    Auth -->|"JWT and scoped JSON"| Flutter
```

## Feature DFD 2: Enrollment and Collector Provisioning

```mermaid
flowchart LR
    Owner["Owner / Admin"]
    Flutter["Flutter client"]
    Installer["Linux installer\ninstall.sh"]
    API["Django installer APIs\nenrollment + status"]
    PG[("PostgreSQL\nenrollment, server, credential,\nVictoria tenant")]
    Alloy["Grafana Alloy"]
    Forwarder["Request-log forwarder"]

    Owner -->|"Generate enrollment token"| Flutter
    Admin -->|"Generate enrollment token"| Flutter
    Flutter -->|"Token request"| API
    API -->|"One-time token"| Installer
    Installer -->|"Host facts and token"| API
    API -->|"Persist server, connection, tenant"| PG
    PG -->|"Credential and generated config"| API
    API -->|"Install response"| Installer
    Installer -->|"Configure and start"| Alloy
    Installer -->|"Configure and start"| Forwarder
```

## Feature DFD 3: Metrics and Service Health

```mermaid
flowchart LR
    Host["Monitored host\nnode exporter / cAdvisor / app metrics"]
    Alloy["Grafana Alloy"]
    Gateway["Django remote-write gateway\nvalidate, tenant route, identity rewrite"]
    PG[("PostgreSQL\nservers, services, health metadata")]
    Insert["VictoriaMetrics vminsert"]
    Storage[("VictoriaMetrics vmstorage\nretained time-series")]
    Select["VictoriaMetrics vmselect"]
    Query["Django VictoriaMetricsQueryAdapter\ntenant-scoped PromQL"]
    Worker["Celery worker\nlifecycle evaluation"]
    Flutter["Flutter dashboards"]

    Host -->|"Prometheus samples"| Alloy
    Alloy -->|"Snappy protobuf remote_write"| Gateway
    Gateway -->|"Discover services and health"| PG
    Gateway -->|"Credential-derived tenant labels"| Insert
    Insert --> Storage
    Storage --> Select
    Flutter -->|"Metric and health requests"| Query
    Query -->|"Tenant-scoped queries"| Select
    Select -->|"Time-series samples"| Query
    Query -->|"Normalized authorized JSON"| Flutter
    Worker -->|"Read health observations"| Query
    Worker -->|"Service state, alerts, incidents"| PG
```

## Feature DFD 4: Access Logs and Request Shield

```mermaid
flowchart LR
    Service["HTTP service / reverse proxy"]
    Files["nginx / Apache access logs"]
    Forwarder["Request-log forwarder\nparse, batch, retry"]
    Ingest["Django Request Shield ingestion\nauthenticate, redact, feature extraction"]
    PG[("PostgreSQL\nRequestLog + ShieldConfig")]
    Redis["Redis\nCelery queue"]
    Worker["Celery worker\nclassification and suggestions"]
    ML["FastAPI ML service\n/classify-requests"]
    Artifact["Approved Request Shield artifact\nmodel.joblib + metadata.json"]
    Gemini["Google Gemini API"]
    Flutter["Flutter Request Shield UI"]
    Offset[("Forwarder offset state")]

    Service --> Files
    Files -->|"Access-log lines"| Forwarder
    Forwarder -->|"Bearer JSON batches"| Ingest
    Forwarder -->|"Persist byte offset"| Offset
    Ingest -->|"Validated events + 26 features"| PG
    Worker -->|"Scheduled task"| Redis
    Redis --> Worker
    Worker -->|"Pending feature vectors"| ML
    ML -->|"Load approved artifact only"| Artifact
    ML -->|"Zone, confidence, model version"| Worker
    Worker -->|"Update classifications and suggestions"| PG
    Worker -->|"Selected GRAY requests"| Gemini
    Gemini -->|"Second opinion"| Worker
    OrgAPI["Django organization APIs"]
    Flutter -->|"List, analytics, review, config"| OrgAPI
    OrgAPI -->|"Read and update Shield state"| PG
    PG -->|"Authorized Shield JSON"| OrgAPI
    OrgAPI --> Flutter
```

## Feature DFD 5: Service Anomaly Detection

```mermaid
flowchart LR
    VM["VictoriaMetrics vmselect"]
    Features["Django ServiceFeatureBuilder\naligned six-feature windows"]
    Worker["Celery worker\nservice ML dispatch"]
    ML["FastAPI ML service\n/train and /infer"]
    Models[("ML artifact volume\nservice model.joblib + metadata")]
    Callback["Django ML detection callback"]
    PG[("PostgreSQL\nAnomalyDetection")]
    OrgAPI["Django organization APIs"]
    Flutter["Flutter anomaly dashboard"]
    Assistant["Django AI assistant context"]

    Worker -->|"Request metric window"| Features
    Features -->|"Tenant-scoped PromQL"| VM
    VM -->|"CPU, memory, disk, network samples"| Features
    Features -->|"Six aligned features"| ML
    ML -->|"Load or update service artifact"| Models
    ML -->|"Detection + model version"| Callback
    Callback --> PG
    Flutter -->|"Anomaly list and details"| OrgAPI
    OrgAPI -->|"Read authorized detections"| PG
    PG -->|"Authorized detections"| OrgAPI
    OrgAPI --> Flutter
    Assistant -->|"Request anomaly evidence"| PG
```


## Feature DFD 6: AI Assistant

```mermaid
flowchart LR
    User["Owner / Admin / Engineer"]
    Flutter["Flutter AI assistant"]
    Ticket["Django WebSocket ticket API"]
    Consumer["Django Channels consumer"]
    PG[("PostgreSQL\nconversations, messages,\nanomaly evidence")]
    Gemini["Google Gemini API"]

    User -->|"Ask question"| Flutter
    Flutter -->|"Request one-time WebSocket ticket"| Ticket
    Ticket -->|"Ticket state"| PG
    Flutter -->|"Conversation WebSocket"| Consumer
    Consumer -->|"History and authorized evidence"| PG
    Consumer -->|"Prompt and stream request"| Gemini
    Gemini -->|"Streamed answer"| Consumer
    Consumer -->|"Stream tokens"| Flutter
    Consumer -->|"Persist completed response"| PG
  ```


## Data Store Responsibilities

| Store              | Data                                                                                                                                                                              | Main writers                                                                    | Main readers                                               |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| PostgreSQL         | Identity, organizations, enrollment, server/service metadata, credentials, alerts, incidents, logs, anomaly detections, AI state, Request Shield events/configuration/suggestions | Django APIs, remote-write gateway metadata path, Celery worker, ML callback     | Django domain APIs, Celery worker, Flutter through Django  |
| VictoriaMetrics    | Prometheus numeric samples and labels, including host, container, and application metrics                                                                                         | Django remote-write gateway through`vminsert`                                 | Django`VictoriaMetricsQueryAdapter` through `vmselect` |
| Redis              | Celery task messages and results                                                                                                                                                  | Celery Beat, Django task dispatch                                               | Celery Worker and result consumers                         |
| ML artifact volume | Versioned model files and metadata                                                                                                                                                | Offline release/deployment process; service anomaly training path where enabled | FastAPI ML service                                         |
| Forwarder state    | Access-log byte offset                                                                                                                                                            | Request-log forwarder                                                           | Request-log forwarder after restart/rotation               |

## Important Boundaries

- Flutter never calls FastAPI, PostgreSQL, Redis, or VictoriaMetrics directly.
  Django authorizes and normalizes all client-facing data.
- Monitoring credentials identify the organization and server. Collector-sent
  identity labels are overwritten before samples are sent to VictoriaMetrics.
- Metrics are time-series data and belong in VictoriaMetrics. Request Shield
  access events remain in PostgreSQL because they need paths, event metadata,
  classification updates, deduplication, review state, and relational tenancy.
- Request Shield production performs inference only. Its approved
  `model.joblib` and `metadata.json` are released offline; the production ML
  service does not expose a Request Shield training endpoint.
- Gemini is backend-only. API keys and prompts are not sent to Flutter.
- The current generic service-anomaly path still has `/train` and `/infer`
  semantics for service models; that is separate from the artifact-only Request
  Shield classifier.
