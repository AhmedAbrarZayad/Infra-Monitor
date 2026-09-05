# Infra Monitor

Infra Monitor is a Django and Flutter application for enrolling Linux servers,
collecting telemetry through Grafana Alloy and VictoriaMetrics, and presenting
operational dashboards, alerts, incidents, logs, and anomaly detections.

## Backend architecture

The Django backend is organized by business domain:

| Package | Responsibility |
| --- | --- |
| `accounts` | Authentication, organizations, memberships, preferences, and enrollment lifecycle |
| `servers` | Servers, services, metric queries, and monitoring credentials |
| `installer` | Installer delivery, host enrollment callbacks, and remote-write ingestion |
| `alert` | Alert queries and lifecycle actions |
| `incident` | Incident workflow, assignment, evidence, updates, and feedback |
| `log` | Operational log queries and internal batch ingestion |
| `ml_model` | Anomaly detection records and APIs |
| `dashboard` | Cross-domain overview and analytics read models |
| `infra_monitor` | Django settings, root routing, and platform health endpoints |
| `common` | Small framework-level API helpers shared between domains |

Domain URL modules are composed under
`/api/organizations/<organization_id>/`. Business views do not live in the
`infra_monitor` project package.

## Backend setup

From PowerShell:

```powershell
cd backend
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set the database and application values in `backend/.env`, then run:

```powershell
python manage.py migrate
python manage.py runserver 0.0.0.0:7000
```

The environment file is ignored by Git and must never be committed.

For the root Compose stack, also create `model/.env` from
`model/.env.example`. Set the same `ML_SERVICE_TOKEN` in `backend/.env` and
`model/.env`; no root `.env` is used.

## Backend quality checks

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
ruff check .
ruff format --check .
```

To format backend Python code:

```powershell
ruff check . --fix
ruff format .
```

## Documentation

- [Local physical-device monitoring lab](docs/local-physical-device-monitoring-lab.md)
- [Monitoring architecture and API flow](docs/monitoring-end-to-end.md)
- [ML service architecture](docs/ML%20Architecture.md)
- [Container Isolation Forest integration](docs/Container%20Isolation%20Forest%20Integration.md)

## UI design reference

[Lovable prototype](https://lovable.dev/projects/bda4cb03-1b60-4c56-9687-8f600e8f0536)
