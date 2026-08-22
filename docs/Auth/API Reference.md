# Authentication API Reference

## Base URL

```
/api/auth/
```

---

## Endpoints

### POST `/register/`

Creates a new user and sends email verification OTP.

**Auth**: None

**Request**:
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "StrongPass123!",
  "password_confirm": "StrongPass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response** `201`:
```json
{
  "message": "Registration successful. Please verify your email.",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "viewer",
    "is_email_verified": false,
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

**Errors**: `400` — duplicate email/username, weak password, password mismatch.

---

### POST `/verify-email/`

Verifies email with OTP. Returns JWT tokens on success.

**Auth**: None

**Request**:
```json
{
  "email": "john@example.com",
  "otp": "123456"
}
```

**Response** `200`:
```json
{
  "message": "Email verified successfully.",
  "user": { ... },
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

**Errors**: `400` — invalid/expired OTP.

---

### POST `/resend-otp/`

Resends email verification OTP. Invalidates previous OTPs.

**Auth**: None

**Request**:
```json
{
  "email": "john@example.com"
}
```

**Response** `200`:
```json
{
  "message": "Verification code sent."
}
```

---

### POST `/login/`

Authenticates user. Requires verified email.

**Auth**: None

**Request**:
```json
{
  "email": "john@example.com",
  "password": "StrongPass123!"
}
```

**Response** `200`:
```json
{
  "message": "Login successful.",
  "user": { ... },
  "tokens": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  }
}
```

**Errors**: `400` — invalid credentials, unverified email.

---

### POST `/logout/`

Blacklists the refresh token.

**Auth**: `Bearer <access_token>`

**Request**:
```json
{
  "refresh": "eyJ..."
}
```

**Response** `200`:
```json
{
  "message": "Logged out successfully."
}
```

**Errors**: `401` — unauthenticated. `400` — missing refresh token.

---

### POST `/forgot-password/`

Sends password reset OTP. Always returns 200 (anti-enumeration).

**Auth**: None

**Request**:
```json
{
  "email": "john@example.com"
}
```

**Response** `200`:
```json
{
  "message": "If an account exists with this email, a reset code has been sent."
}
```

---

### POST `/reset-password/`

Resets password using OTP.

**Auth**: None

**Request**:
```json
{
  "email": "john@example.com",
  "otp": "123456",
  "new_password": "NewStrongPass456!",
  "new_password_confirm": "NewStrongPass456!"
}
```

**Response** `200`:
```json
{
  "message": "Password reset successfully."
}
```

**Errors**: `400` — invalid OTP, password mismatch, weak password.

---

### POST `/token/refresh/`

Refreshes access token using a valid refresh token.

**Auth**: None

**Request**:
```json
{
  "refresh": "eyJ..."
}
```

**Response** `200`:
```json
{
  "access": "eyJ..."
}
```

**Errors**: `401` — token blacklisted or expired.
