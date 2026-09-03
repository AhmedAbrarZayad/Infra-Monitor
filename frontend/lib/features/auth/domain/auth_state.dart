import '../data/models/user_model.dart';

/// Represents the authentication state of the application.
sealed class AuthState {
  const AuthState();
}

/// Initial/unknown state — checking for stored tokens.
class AuthInitial extends AuthState {
  const AuthInitial();
}

/// Actively loading (login, register, etc. in progress).
class AuthLoading extends AuthState {
  const AuthLoading();
}

/// User is authenticated.
class AuthAuthenticated extends AuthState {
  final UserModel user;
  final String accessToken;
  final String refreshToken;

  const AuthAuthenticated({
    required this.user,
    required this.accessToken,
    required this.refreshToken,
  });
}

/// User is not authenticated.
class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

/// An error occurred during an auth operation.
class AuthError extends AuthState {
  final String message;

  const AuthError(this.message);
}

/// A stored session could not be restored because of a retryable network error.
class AuthSessionRestoreError extends AuthState {
  final String message;
  const AuthSessionRestoreError(this.message);
}

/// Registration succeeded — user needs to verify email.
class AuthEmailVerificationRequired extends AuthState {
  final String email;

  const AuthEmailVerificationRequired({required this.email});
}

/// Password reset OTP has been sent — user needs to enter OTP + new password.
class AuthPasswordResetOtpSent extends AuthState {
  final String email;

  const AuthPasswordResetOtpSent({required this.email});
}
