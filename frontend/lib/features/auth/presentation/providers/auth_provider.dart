import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../data/auth_repository.dart';
import '../../domain/auth_state.dart';

/// Global auth repository provider.
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository();
});

/// Global secure storage provider.
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});

/// Auth state notifier provider — single source of truth for auth state.
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    repository: ref.watch(authRepositoryProvider),
    storage: ref.watch(secureStorageProvider),
  );
});

/// Manages authentication state and token persistence.
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository repository;
  final FlutterSecureStorage storage;

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';

  AuthNotifier({
    required this.repository,
    required this.storage,
    AuthState initialState = const AuthInitial(),
    bool autoLogin = true,
  }) : super(initialState) {
    if (autoLogin) _tryAutoLogin();
  }

  /// Check for stored tokens on app start.
  Future<void> _tryAutoLogin() async {
    try {
      final accessToken = await storage.read(key: _accessTokenKey);
      final refreshToken = await storage.read(key: _refreshTokenKey);

      if (accessToken == null || refreshToken == null) {
        state = const AuthUnauthenticated();
        return;
      }

      // Try to refresh the token to validate it
      final tokens = await repository.refreshToken(refreshToken: refreshToken);
      await _persistTokens(tokens['access']!, tokens['refresh']!);
      final user = await repository.getMe(accessToken: tokens['access']!);
      state = AuthAuthenticated(
        user: user,
        accessToken: tokens['access']!,
        refreshToken: tokens['refresh']!,
      );
    } on ApiException catch (error) {
      if (error.statusCode == 401) {
        await _clearTokens();
        state = const AuthUnauthenticated();
      } else {
        state = AuthSessionRestoreError(error.message);
      }
    } catch (_) {
      state = const AuthSessionRestoreError(
        'Unable to restore your session. Check your connection and try again.',
      );
    }
  }

  Future<void> retrySessionRestore() async {
    state = const AuthInitial();
    await _tryAutoLogin();
  }

  Future<void> clearSession() async {
      await _clearTokens();
      state = const AuthUnauthenticated();
  }

  /// Register a new user.
  Future<void> register({
    required String username,
    required String email,
    required String password,
    required String passwordConfirm,
    String firstName = '',
    String lastName = '',
  }) async {
    state = const AuthLoading();
    try {
      await repository.register(
        username: username,
        email: email,
        password: password,
        passwordConfirm: passwordConfirm,
        firstName: firstName,
        lastName: lastName,
      );
      state = AuthEmailVerificationRequired(email: email);
    } on ApiException catch (e) {
      state = AuthError(e.message);
    } catch (e) {
      state = AuthError('Registration failed. Please try again.');
    }
  }

  /// Verify email with OTP.
  Future<void> verifyEmail({
    required String email,
    required String otp,
  }) async {
    state = const AuthLoading();
    try {
      final response = await repository.verifyEmail(email: email, otp: otp);
      await _persistTokens(response.accessToken, response.refreshToken);
      state = AuthAuthenticated(
        user: response.user,
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
      );
    } on ApiException catch (e) {
      state = AuthError(e.message);
    } catch (e) {
      state = AuthError('Email verification failed. Please try again.');
    }
  }

  /// Resend email verification OTP.
  Future<void> resendOtp({required String email}) async {
    try {
      await repository.resendOtp(email: email);
    } catch (_) {
      // Silently fail — the UI should show a generic message
    }
  }

  /// Login with email and password.
  Future<void> login({
    required String email,
    required String password,
  }) async {
    state = const AuthLoading();
    try {
      final response = await repository.login(email: email, password: password);
      await _persistTokens(response.accessToken, response.refreshToken);
      state = AuthAuthenticated(
        user: response.user,
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
      );
    } on ApiException catch (e) {
      if (e.body.containsKey('email_not_verified') ||
          (e.body.values.any((v) =>
              v is List &&
              v.any((item) =>
                  item is Map && item['email_not_verified'] == true)))) {
        state = AuthEmailVerificationRequired(email: email);
      } else {
        state = AuthError(e.message);
      }
    } catch (e) {
      state = AuthError('Login failed. Please try again.');
    }
  }

  /// Logout and blacklist refresh token.
  Future<void> logout() async {
    final currentState = state;
    if (currentState is AuthAuthenticated) {
      try {
        await repository.logout(
          accessToken: currentState.accessToken,
          refreshToken: currentState.refreshToken,
        );
      } catch (_) {
        // Even if server-side logout fails, clear local tokens
      }
    }
    await _clearTokens();
    state = const AuthUnauthenticated();
  }

  /// Request a password reset OTP.
  Future<void> forgotPassword({required String email}) async {
    state = const AuthLoading();
    try {
      await repository.forgotPassword(email: email);
      state = AuthPasswordResetOtpSent(email: email);
    } on ApiException catch (e) {
      state = AuthError(e.message);
    } catch (e) {
      state = AuthError('Failed to send reset code. Please try again.');
    }
  }

  /// Reset password with OTP.
  Future<void> resetPassword({
    required String email,
    required String otp,
    required String newPassword,
    required String newPasswordConfirm,
  }) async {
    state = const AuthLoading();
    try {
      await repository.resetPassword(
        email: email,
        otp: otp,
        newPassword: newPassword,
        newPasswordConfirm: newPasswordConfirm,
      );
      state = const AuthUnauthenticated();
    } on ApiException catch (e) {
      state = AuthError(e.message);
    } catch (e) {
      state = AuthError('Password reset failed. Please try again.');
    }
  }

  /// Persist tokens to secure storage.
  Future<void> _persistTokens(String access, String refresh) async {
    await storage.write(key: _accessTokenKey, value: access);
    await storage.write(key: _refreshTokenKey, value: refresh);
  }

  /// Clear stored tokens.
  Future<void> _clearTokens() async {
    await storage.delete(key: _accessTokenKey);
    await storage.delete(key: _refreshTokenKey);
    await storage.delete(key: 'active_organization_id');
  }
}
