# Android push configuration

The Android client configuration lives at
`frontend/android/app/google-services.json`. That file is not a server
credential.

For server deployments, Base64-encode the Firebase service-account JSON and
store it in the server's secret environment configuration:

```env
FCM_ENABLED=true
FIREBASE_PROJECT_ID=inframonitor-7c5be
FIREBASE_SERVICE_ACCOUNT_BASE64=<base64-encoded-service-account-json>
FCM_HTTP_TIMEOUT_SECONDS=10
```

Do not commit the original JSON or the encoded value. Application Default
Credentials remain supported when the Base64 variable is omitted.

Run migrations and restart both backend processes after configuration:

```sh
python manage.py migrate
docker compose up --build backend celery_worker
```

Users must enable Notifications in the existing Preferences screen. Android
13 and newer also asks for OS notification permission after login.
