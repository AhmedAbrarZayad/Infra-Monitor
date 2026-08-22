# Auth API Documentation

**Base URL**: `http://localhost:8000/api/auth`

> All requests use `Content-Type: application/json`
> When `DEBUG=True`, OTP-generating endpoints return `debug_otp` and `email_sent` in the response.

---

## 1. Register

`POST /api/auth/register/`

**Request**:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPass123!",
  "password_confirm": "TestPass123!",
  "first_name": "Test",
  "last_name": "User"
}
```

**Response** `201 Created`:
```json
{
  "message": "Registration successful. Please check your email for the verification code.",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "role": "viewer",
    "is_email_verified": false,
    "created_at": "2026-08-22T10:00:00Z"
  },
  "debug_otp": "482901",
  "email_sent": false
}
```

**Error** `400 Bad Request`:
```json
{
  "email": ["A user with this email already exists."],
  "username": ["A user with this username already exists."],
  "password_confirm": ["Passwords do not match."],
  "password": ["This password is too short. It must contain at least 8 characters."]
}
```

---

## 2. Verify Email

`POST /api/auth/verify-email/`

**Request**:
```json
{
  "email": "test@example.com",
  "otp": "482901"
}
```

**Response** `200 OK`:
```json
{
  "message": "Email verified successfully. Welcome to Infra Monitor!",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "role": "viewer",
    "is_email_verified": true,
    "created_at": "2026-08-22T10:00:00Z"
  },
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Error** `400 Bad Request`:
```json
{
  "detail": "Invalid or expired OTP."
}
```

---

## 3. Resend OTP

`POST /api/auth/resend-otp/`

**Request**:
```json
{
  "email": "test@example.com"
}
```

**Response** `200 OK`:
```json
{
  "message": "If an account exists with this email, a new verification code has been sent.",
  "debug_otp": "739201",
  "email_sent": false
}
```

**Error** `400 Bad Request` (already verified):
```json
{
  "detail": "Email is already verified."
}
```

---

## 4. Login

`POST /api/auth/login/`

**Request**:
```json
{
  "email": "test@example.com",
  "password": "TestPass123!"
}
```

**Response** `200 OK`:
```json
{
  "message": "Login successful.",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "role": "viewer",
    "is_email_verified": true,
    "created_at": "2026-08-22T10:00:00Z"
  },
  "tokens": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Error** `400 Bad Request`:
```json
{
  "non_field_errors": ["Invalid email or password."]
}
```

```json
{
  "non_field_errors": ["Please verify your email before logging in."]
}
```

---

## 5. Logout

`POST /api/auth/logout/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** `200 OK`:
```json
{
  "message": "Logged out successfully."
}
```

**Error** `401 Unauthorized`:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error** `400 Bad Request`:
```json
{
  "detail": "Refresh token is required."
}
```

---

## 6. Forgot Password

`POST /api/auth/forgot-password/`

**Request**:
```json
{
  "email": "test@example.com"
}
```

**Response** `200 OK` (always returns 200 to prevent email enumeration):
```json
{
  "message": "If an account exists with this email, a password reset code has been sent.",
  "debug_otp": "561432",
  "email_sent": false
}
```

---

## 7. Reset Password

`POST /api/auth/reset-password/`

**Request**:
```json
{
  "email": "test@example.com",
  "otp": "561432",
  "new_password": "NewStrongPass456!",
  "new_password_confirm": "NewStrongPass456!"
}
```

**Response** `200 OK`:
```json
{
  "message": "Password reset successfully. You can now log in with your new password."
}
```

**Error** `400 Bad Request`:
```json
{
  "detail": "Invalid or expired OTP."
}
```

```json
{
  "new_password_confirm": ["Passwords do not match."]
}
```

---

## 8. Refresh Token

`POST /api/auth/token/refresh/`

**Request**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** `200 OK`:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error** `401 Unauthorized`:
```json
{
  "detail": "Token is blacklisted",
  "code": "token_not_valid"
}
```

---

## Testing Flow (Step-by-Step)

```
1. Register       → copy debug_otp from response
2. Verify Email   → paste otp → copy access & refresh tokens
3. Login          → (optional, verify-email already returns tokens)
4. Logout         → send refresh token with Bearer access header
5. Forgot Password → copy debug_otp from response
6. Reset Password  → paste otp + set new password
7. Login           → use new password
```

## Notes

- `debug_otp` and `email_sent` fields only appear when `DEBUG=True` in `.env`
- OTPs expire after 10 minutes (configurable via `OTP_EXPIRY_MINUTES`)
- Generating a new OTP invalidates all previous OTPs for that user
- Logout blacklists the refresh token — it cannot be reused
