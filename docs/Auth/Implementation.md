# Authentication Implementation Guide

## Backend Structure

```
accounts/
├── models/
│   ├── users.py                    # Custom user model (USERNAME_FIELD = email)
│   ├── password_reset_otp.py       # OTP with expiry + usage tracking
│   └── email_verification_otp.py   # OTP with expiry + usage tracking
├── serializers/
│   ├── register_serializer.py      # Validates uniqueness, password strength + match
│   ├── login_serializer.py         # Authenticates, blocks unverified users
│   ├── verify_email_serializer.py  # Validates email + 6-digit OTP
│   ├── resend_otp_serializer.py    # Validates email format
│   ├── forgot_password_serializer.py  # Email-only input
│   ├── reset_password_serializer.py   # OTP + new password + confirm
│   └── user_serializer.py         # Read-only user output
├── services/
│   ├── email_service.py           # Gmail OAuth 2.0 SMTP (XOAUTH2)
│   └── otp_service.py            # OTP generation + verification facade
├── views/
│   ├── register_view.py
│   ├── verify_email_view.py
│   ├── resend_otp_view.py
│   ├── login_view.py
│   ├── logout_view.py
│   ├── forgot_password_view.py
│   └── reset_password_view.py
├── templates/emails/
│   ├── welcome.html
│   ├── email_verification_otp.html
│   └── password_reset_otp.html
├── tests/
│   ├── test_models.py             # 9 tests
│   ├── test_serializers.py        # 14 tests
│   ├── test_services.py           # 11 tests (mocked SMTP)
│   └── test_views.py             # 18 integration tests
├── urls.py
└── admin.py
```

## Frontend Structure

```
lib/features/auth/
├── data/
│   ├── models/
│   │   ├── user_model.dart         # User JSON serialization
│   │   └── auth_response.dart      # AuthResponse, RegisterResponse, MessageResponse
│   └── auth_repository.dart        # HTTP client for all endpoints
├── domain/
│   └── auth_state.dart            # Sealed class hierarchy (7 states)
├── presentation/
│   ├── providers/
│   │   └── auth_provider.dart     # Riverpod StateNotifier + secure storage
│   ├── pages/
│   │   ├── login_page.dart
│   │   ├── register_page.dart
│   │   ├── verify_email_page.dart
│   │   ├── forgot_password_page.dart
│   │   └── reset_password_page.dart
│   └── widgets/
│       ├── auth_text_field.dart
│       └── auth_button.dart
└── auth.dart                      # Barrel export
```

---

## Key Design Decisions

### 1. Model — `USERNAME_FIELD = "email"`

Login uses email (not username). The `Users` model sets `USERNAME_FIELD = "email"` so Django's auth backend authenticates by email.

### 2. OTP Exclusivity

When a new OTP is generated, all previous active OTPs for that user are marked `is_used = True`. This prevents OTP reuse and ensures only the latest code is valid.

```python
# otp_service.py
EmailVerificationOTP.objects.filter(user=user, is_used=False).update(is_used=True)
```

### 3. Email Service — XOAUTH2 (not App Passwords)

Uses Google's OAuth 2.0 refresh token flow to obtain short-lived access tokens, then authenticates to SMTP via the `XOAUTH2` mechanism. More secure than static app passwords and compatible with Google's security policies.

### 4. Anti-Enumeration on Forgot Password

The forgot-password endpoint always returns `200` regardless of whether the email exists. This prevents attackers from discovering valid email addresses.

### 5. Sealed Auth States (Flutter)

Uses Dart 3 sealed classes for exhaustive state matching in the UI:

```dart
sealed class AuthState {}
class AuthInitial extends AuthState {}
class AuthLoading extends AuthState {}
class AuthAuthenticated extends AuthState { ... }
class AuthUnauthenticated extends AuthState {}
class AuthError extends AuthState { ... }
class AuthEmailVerificationRequired extends AuthState { ... }
class AuthPasswordResetOtpSent extends AuthState { ... }
```

### 6. Router Guard

`app_router.dart` uses a `redirect` callback that checks `authProvider` state:
- Unauthenticated + protected route → `/login`
- Authenticated + auth route → `/`

---

## Environment Configuration

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Yes | PostgreSQL connection |
| `GMAIL_SENDER_EMAIL` | Yes | Gmail address for sending |
| `GMAIL_CLIENT_ID` | Yes | Google OAuth 2.0 client ID |
| `GMAIL_CLIENT_SECRET` | Yes | Google OAuth 2.0 client secret |
| `GMAIL_REFRESH_TOKEN` | Yes | OAuth 2.0 refresh token |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | No | Default: 30 |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | No | Default: 7 |
| `OTP_EXPIRY_MINUTES` | No | Default: 10 |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated URLs |

### Frontend (`--dart-define`)

| Variable | Default | Usage |
|----------|---------|-------|
| `API_BASE_URL` | `http://10.0.2.2:8000/api` | Android emulator |
| `API_BASE_URL` | `http://localhost:8000/api` | Web/desktop |

```bash
# Android
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api

# Web
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api
```

---

## Test Coverage

| Layer | File | Tests | Coverage |
|-------|------|-------|----------|
| Models | `test_models.py` | 9 | Users CRUD, OTP expiry/usage, uniqueness |
| Serializers | `test_serializers.py` | 14 | Validation rules, duplicate rejection, password strength |
| Services | `test_services.py` | 11 | OTP lifecycle, SMTP mocking, token refresh |
| Views | `test_views.py` | 18 | Full HTTP integration tests for all endpoints |
| Flutter Models | `auth_models_test.dart` | 6 | JSON serialization, missing fields |
| Flutter Repo | `auth_repository_test.dart` | 10 | MockClient, success + error paths |
| **Total** | | **68** | |

```bash
# Run backend tests
py manage.py test accounts -v 2

# Run frontend tests
flutter test test/features/auth/ -v
```
