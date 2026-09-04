# Infra Monitor Flutter client

The client reads organization-scoped operational telemetry from the Django API. Set `API_BASE_URL` in `frontend/.env`; include `/api` and use a host reachable from the selected device.

```dotenv
# Android emulator
API_BASE_URL=http://10.0.2.2:8000/api

# Flutter web or desktop on the development machine
API_BASE_URL=http://localhost:8000/api

# Production behind the external HTTPS reverse proxy
API_BASE_URL=https://monitor.example.com/api
```

For a physical phone, use the development machine's LAN address and allow that host/origin in Django. Production must use HTTPS.

```sh
dart format --set-exit-if-changed lib test
flutter analyze
flutter test
```
