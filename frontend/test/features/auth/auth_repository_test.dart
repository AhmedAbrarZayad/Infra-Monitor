import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/features/auth/data/auth_repository.dart';

void main() {
  group('AuthRepository', () {
    late AuthRepository repository;

    AuthRepository createRepoWithMock(
      Future<http.Response> Function(http.Request) handler,
    ) {
      return AuthRepository(
        client: MockClient(handler),
        baseUrl: 'http://test/api/auth',
      );
    }

    group('register', () {
      test('returns RegisterResponse on 201', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({
              'message': 'Registration successful.',
              'user': {
                'id': 1,
                'username': 'testuser',
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'viewer',
                'is_email_verified': false,
                'created_at': '2026-01-01T00:00:00Z',
              },
            }),
            201,
          );
        });

        final result = await repository.register(
          username: 'testuser',
          email: 'test@example.com',
          password: 'StrongPass123!',
          passwordConfirm: 'StrongPass123!',
        );

        expect(result.user.email, 'test@example.com');
        expect(result.user.isEmailVerified, false);
      });

      test('throws ApiException on 400', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({'email': ['A user with this email already exists.']}),
            400,
          );
        });

        expect(
          () => repository.register(
            username: 'testuser',
            email: 'existing@example.com',
            password: 'StrongPass123!',
            passwordConfirm: 'StrongPass123!',
          ),
          throwsA(isA<ApiException>()),
        );
      });
    });

    group('login', () {
      test('returns AuthResponse on 200', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({
              'message': 'Login successful.',
              'user': {
                'id': 1,
                'username': 'testuser',
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'viewer',
                'is_email_verified': true,
                'created_at': '2026-01-01T00:00:00Z',
              },
              'tokens': {
                'access': 'mock-access-token',
                'refresh': 'mock-refresh-token',
              },
            }),
            200,
          );
        });

        final result = await repository.login(
          email: 'test@example.com',
          password: 'TestPass123!',
        );

        expect(result.accessToken, 'mock-access-token');
        expect(result.refreshToken, 'mock-refresh-token');
        expect(result.user.isEmailVerified, true);
      });

      test('throws ApiException on invalid credentials', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({'detail': 'Invalid email or password.'}),
            400,
          );
        });

        expect(
          () => repository.login(email: 'test@example.com', password: 'wrong'),
          throwsA(isA<ApiException>()),
        );
      });
    });

    group('verifyEmail', () {
      test('returns AuthResponse with tokens on 200', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({
              'message': 'Email verified.',
              'user': {
                'id': 1,
                'username': 'testuser',
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'viewer',
                'is_email_verified': true,
                'created_at': '2026-01-01T00:00:00Z',
              },
              'tokens': {
                'access': 'access-token',
                'refresh': 'refresh-token',
              },
            }),
            200,
          );
        });

        final result = await repository.verifyEmail(
          email: 'test@example.com',
          otp: '123456',
        );

        expect(result.accessToken, 'access-token');
        expect(result.user.isEmailVerified, true);
      });
    });

    group('forgotPassword', () {
      test('returns MessageResponse on 200', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({'message': 'If an account exists...'}),
            200,
          );
        });

        final result = await repository.forgotPassword(
          email: 'test@example.com',
        );

        expect(result.message, contains('account'));
      });
    });

    group('resetPassword', () {
      test('returns MessageResponse on 200', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({'message': 'Password reset successfully.'}),
            200,
          );
        });

        final result = await repository.resetPassword(
          email: 'test@example.com',
          otp: '123456',
          newPassword: 'NewPass123!',
          newPasswordConfirm: 'NewPass123!',
        );

        expect(result.message, contains('reset'));
      });
    });

    group('logout', () {
      test('returns MessageResponse on 200', () async {
        repository = createRepoWithMock((request) async {
          expect(request.headers['Authorization'], 'Bearer mock-access');
          return http.Response(
            jsonEncode({'message': 'Logged out successfully.'}),
            200,
          );
        });

        final result = await repository.logout(
          accessToken: 'mock-access',
          refreshToken: 'mock-refresh',
        );

        expect(result.message, contains('Logged out'));
      });
    });

    group('refreshToken', () {
      test('returns new tokens on 200', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({
              'access': 'new-access-token',
              'refresh': 'new-refresh-token',
            }),
            200,
          );
        });

        final result = await repository.refreshToken(
          refreshToken: 'old-refresh-token',
        );

        expect(result['access'], 'new-access-token');
        expect(result['refresh'], 'new-refresh-token');
      });

      test('throws ApiException on 401', () async {
        repository = createRepoWithMock((request) async {
          return http.Response(
            jsonEncode({'detail': 'Token is invalid or expired'}),
            401,
          );
        });

        expect(
          () => repository.refreshToken(refreshToken: 'expired-token'),
          throwsA(isA<ApiException>()),
        );
      });
    });
  });
}
