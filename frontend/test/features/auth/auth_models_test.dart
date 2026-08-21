import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/features/auth/data/models/user_model.dart';
import 'package:frontend/features/auth/data/models/auth_response.dart';

void main() {
  group('UserModel', () {
    test('fromJson creates valid model', () {
      final json = {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'role': 'viewer',
        'is_email_verified': true,
        'created_at': '2026-01-01T00:00:00Z',
      };

      final user = UserModel.fromJson(json);
      expect(user.id, 1);
      expect(user.username, 'testuser');
      expect(user.email, 'test@example.com');
      expect(user.isEmailVerified, true);
    });

    test('fromJson handles missing optional fields', () {
      final json = {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
      };

      final user = UserModel.fromJson(json);
      expect(user.firstName, '');
      expect(user.lastName, '');
      expect(user.role, 'viewer');
      expect(user.isEmailVerified, false);
    });

    test('toJson produces correct map', () {
      const user = UserModel(
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
        role: 'admin',
        isEmailVerified: true,
        createdAt: '2026-01-01T00:00:00Z',
      );

      final json = user.toJson();
      expect(json['id'], 1);
      expect(json['email'], 'test@example.com');
      expect(json['role'], 'admin');
    });
  });

  group('AuthResponse', () {
    test('fromJson creates valid response', () {
      final json = {
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
          'access': 'access-token',
          'refresh': 'refresh-token',
        },
      };

      final response = AuthResponse.fromJson(json);
      expect(response.message, 'Login successful.');
      expect(response.accessToken, 'access-token');
      expect(response.refreshToken, 'refresh-token');
      expect(response.user.email, 'test@example.com');
    });
  });

  group('RegisterResponse', () {
    test('fromJson creates valid response without tokens', () {
      final json = {
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
      };

      final response = RegisterResponse.fromJson(json);
      expect(response.message, 'Registration successful.');
      expect(response.user.isEmailVerified, false);
    });
  });

  group('MessageResponse', () {
    test('fromJson creates valid response', () {
      final json = {'message': 'Password reset successfully.'};
      final response = MessageResponse.fromJson(json);
      expect(response.message, 'Password reset successfully.');
    });
  });
}
