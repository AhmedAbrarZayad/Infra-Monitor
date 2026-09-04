# Monitoring deployment configuration

The backend and VictoriaMetrics services use plain HTTP inside the private
Docker network. Production TLS should terminate at a trusted reverse proxy or
load balancer. Only the Django backend needs to be publicly reachable;
`vminsert` and `vmstorage` must remain private.

## Development on the same machine

Use the published Django port from `backend/docker-compose.yml`:

```env
MONITORING_INSTALL_URL=http://localhost:7000/api/monitoring/install.sh
MONITORING_PUBLIC_BASE_URL=http://localhost:7000
ALLOWED_HOSTS=localhost,127.0.0.1
USE_X_FORWARDED_HOST=False
CSRF_TRUSTED_ORIGINS=
```

When Alloy runs in another VM or physical host, replace `localhost` with the
development machine's reachable LAN address and add that address to
`ALLOWED_HOSTS`, for example `http://192.168.1.20:7000`.

## Production behind HTTPS

```env
MONITORING_INSTALL_URL=https://api.example.com/api/monitoring/install.sh
MONITORING_PUBLIC_BASE_URL=https://api.example.com
ALLOWED_HOSTS=api.example.com
USE_X_FORWARDED_HOST=True
CSRF_TRUSTED_ORIGINS=https://api.example.com
VICTORIAMETRICS_INSERT_URL=http://vminsert:8480
VICTORIAMETRICS_SELECT_URL=http://vmselect:8481
```

The proxy must replace, rather than append untrusted client values for, these
headers:

```text
Host: original public host
X-Forwarded-Host: original public host
X-Forwarded-Proto: https
```

Forward `/api/` to Django on port `8000`. Allow sufficiently large request
bodies for Prometheus Remote Write (the application default is 10 MiB
compressed), disable response buffering for `/api/metrics/write`, and use
timeouts longer than `VICTORIAMETRICS_WRITE_TIMEOUT_SECONDS`. Do not expose
ports `8480`, `8482`, `8400`, or `8401` publicly. Port `8481` is published by
the development Compose file for debugging and should be firewalled or removed
in production.

## End-to-end VictoriaMetrics smoke test

With the Compose stack and Docker engine running, execute the opt-in test inside
the backend container so the internal `vminsert` and `vmselect` hostnames are
reachable:

```sh
docker compose exec -e RUN_MONITORING_INTEGRATION=1 backend \
  python manage.py test installer.tests_integration --verbosity 2
```

Normal test runs discover this test but skip it unless the environment flag is
set.

Tenant-specific `vmselect` read URLs encode the `account:project` separator as
`%3A`; tenant identifiers remain internal and are never accepted from Flutter.
