# Authentication Architecture

## Overview

Stateless JWT-based authentication with mandatory email verification (OTP) before first login. Transactional emails sent via Gmail OAuth 2.0 SMTP (XOAUTH2).

## Auth Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Flutter App
    participant B as Django API
    participant G as Gmail SMTP

    Note over U,G: Registration Flow
    U->>F: Fill registration form
    F->>B: POST /api/auth/register/
    B->>B: Create user (is_email_verified=false)
    B->>B: Generate 6-digit OTP (10 min expiry)
    B->>G: Send verification email (XOAUTH2)
    G-->>U: Email with OTP
    B-->>F: 201 {user} (no tokens)
    F->>F: Navigate to Verify Email page

    Note over U,G: Email Verification
    U->>F: Enter OTP
    F->>B: POST /api/auth/verify-email/
    B->>B: Validate OTP, mark email verified
    B->>G: Send welcome email
    B-->>F: 200 {user, tokens: {access, refresh}}
    F->>F: Store tokens → Navigate to Home

    Note over U,G: Login Flow
    U->>F: Enter email + password
    F->>B: POST /api/auth/login/
    B->>B: Authenticate, check is_email_verified
    B-->>F: 200 {user, tokens} or 400 (unverified → redirect)

    Note over U,G: Password Reset Flow
    U->>F: Enter email
    F->>B: POST /api/auth/forgot-password/
    B->>B: Generate reset OTP
    B->>G: Send reset email
    B-->>F: 200 (always, anti-enumeration)
    U->>F: Enter OTP + new password
    F->>B: POST /api/auth/reset-password/
    B->>B: Verify OTP, update password
    B-->>F: 200 → redirect to login
```

## Token Strategy

| Token | Lifetime | Storage (Flutter) | Purpose |
|-------|----------|-------------------|---------|
| Access | 30 min | `flutter_secure_storage` | API authorization (`Bearer` header) |
| Refresh | 7 days | `flutter_secure_storage` | Obtain new access tokens |

- **Blacklisting**: On logout, refresh token is blacklisted via `django-rest-framework-simplejwt` token blacklist.
- **Auto-login**: On app start, the stored refresh token is used to obtain a new access token. If expired, user is redirected to login.

## Security Measures

| Measure | Implementation |
|---------|----------------|
| Password hashing | Django's PBKDF2 (default) |
| OTP exclusivity | New OTP invalidates all previous OTPs for that user |
| OTP expiry | 10 minutes (configurable via `OTP_EXPIRY_MINUTES`) |
| Anti-enumeration | Forgot-password always returns 200 regardless of email existence |
| Email gate | Login blocked until `is_email_verified = true` |
| Token blacklist | Refresh tokens blacklisted on logout |
| CORS | Restricted to configured origins only |

## Email Service

```mermaid
flowchart LR
    A[Django View] --> B[GmailOAuth2EmailService]
    B --> C[Refresh Access Token]
    C --> D[google.oauth2.credentials]
    D --> E[SMTP XOAUTH2]
    E --> F[smtp.gmail.com:587]
```

- Uses `google-auth` to refresh OAuth 2.0 access tokens from a stored refresh token
- Authenticates to Gmail SMTP via `XOAUTH2` (not app passwords)
- Three branded HTML templates: welcome, verification OTP, password reset OTP
