import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config/env_config.dart';
import 'models/auth_response.dart';

/// Exception thrown when an API call returns a non-success status.
class ApiException implements Exception {
  final int statusCode;
  final Map<String, dynamic> body;

  ApiException(this.statusCode, this.body);

  String get message {
    if (body.containsKey('detail')) return body['detail'].toString();
    // Collect all field-level errors
    final errors = <String>[];
    body.forEach((key, value) {
      if (value is List) {
        errors.addAll(value.map((e) => e.toString()));
      } else if (value is Map && value.containsKey('detail')) {
        errors.add(value['detail'].toString());
      } else {
        errors.add(value.toString());
      }
    });
    return errors.isNotEmpty ? errors.join('\n') : 'An error occurred.';
  }

  /// Check if this is an email-not-verified error.
  bool get isEmailNotVerified =>
      body['email_not_verified'] == true ||
      (body is List && (body as dynamic).any((e) => e is Map && e['email_not_verified'] == true));

  @override
  String toString() => 'ApiException($statusCode): $message';
}

/// Repository for all auth-related API calls.
class AuthRepository {
  final http.Client _client;
  final String _baseUrl;

  AuthRepository({
    http.Client? client,
    String? baseUrl,
  })  : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? '${EnvConfig.apiBaseUrl}/auth';

  Map<String, String> _headers({String? accessToken}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (accessToken != null) {
      headers['Authorization'] = 'Bearer $accessToken';
    }
    return headers;
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  void _checkResponse(http.Response response) {
    if (response.statusCode >= 400) {
      throw ApiException(response.statusCode, _decodeResponse(response));
    }
  }

  /// POST /api/auth/register/
  Future<RegisterResponse> register({
    required String username,
    required String email,
    required String password,
    required String passwordConfirm,
    String firstName = '',
    String lastName = '',
  }) async {
    print("the base url is ${_baseUrl}");
    final response = await _client.post(
      Uri.parse('$_baseUrl/register/'),
      headers: _headers(),
      body: jsonEncode({
        'username': username,
        'email': email,
        'password': password,
        'password_confirm': passwordConfirm,
        'first_name': firstName,
        'last_name': lastName,
      }),
    );
    _checkResponse(response);
    return RegisterResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/verify-email/
  Future<AuthResponse> verifyEmail({
    required String email,
    required String otp,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/verify-email/'),
      headers: _headers(),
      body: jsonEncode({'email': email, 'otp': otp}),
    );
    _checkResponse(response);
    return AuthResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/resend-otp/
  Future<MessageResponse> resendOtp({required String email}) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/resend-otp/'),
      headers: _headers(),
      body: jsonEncode({'email': email}),
    );
    _checkResponse(response);
    return MessageResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/login/
  Future<AuthResponse> login({
    required String email,
    required String password,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/login/'),
      headers: _headers(),
      body: jsonEncode({'email': email, 'password': password}),
    );
    _checkResponse(response);
    return AuthResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/logout/
  Future<MessageResponse> logout({
    required String accessToken,
    required String refreshToken,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/logout/'),
      headers: _headers(accessToken: accessToken),
      body: jsonEncode({'refresh': refreshToken}),
    );
    _checkResponse(response);
    return MessageResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/forgot-password/
  Future<MessageResponse> forgotPassword({required String email}) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/forgot-password/'),
      headers: _headers(),
      body: jsonEncode({'email': email}),
    );
    _checkResponse(response);
    return MessageResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/reset-password/
  Future<MessageResponse> resetPassword({
    required String email,
    required String otp,
    required String newPassword,
    required String newPasswordConfirm,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/reset-password/'),
      headers: _headers(),
      body: jsonEncode({
        'email': email,
        'otp': otp,
        'new_password': newPassword,
        'new_password_confirm': newPasswordConfirm,
      }),
    );
    _checkResponse(response);
    return MessageResponse.fromJson(_decodeResponse(response));
  }

  /// POST /api/auth/token/refresh/
  Future<Map<String, String>> refreshToken({
    required String refreshToken,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/token/refresh/'),
      headers: _headers(),
      body: jsonEncode({'refresh': refreshToken}),
    );
    _checkResponse(response);
    final data = _decodeResponse(response);
    return {
      'access': data['access'] as String,
      'refresh': (data['refresh'] as String?) ?? refreshToken,
    };
  }
}
