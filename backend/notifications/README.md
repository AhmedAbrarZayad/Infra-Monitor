# Android push configuration

The Android client configuration lives at
`frontend/android/app/google-services.json`. That file is not a server
credential.

For local Docker development, download a Firebase service-account key to
`backend/firebase-service-account.json` (this path is ignored by Git), then add
the following values to `backend/.env`:

```env
FCM_ENABLED=true
FIREBASE_PROJECT_ID=inframonitor-7c5be
GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-service-account.json
FCM_HTTP_TIMEOUT_SECONDS=10
```

The existing `./backend:/app` bind mount makes that credential available to
the backend and Celery worker. In production, mount the credential separately
as a read-only secret instead of placing it in the application directory.

Run migrations and restart both backend processes after configuration:

```sh
python manage.py migrate
docker compose up --build backend celery_worker
```

Users must enable Notifications in the existing Preferences screen. Android
13 and newer also asks for OS notification permission after login.
