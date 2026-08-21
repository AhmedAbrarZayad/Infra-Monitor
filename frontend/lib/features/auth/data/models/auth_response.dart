import 'user_model.dart';

/// Response from login and verify-email endpoints.
class AuthResponse {
  final String message;
  final UserModel user;
  final String accessToken;
  final String refreshToken;

  const AuthResponse({
    required this.message,
    required this.user,
    required this.accessToken,
    required this.refreshToken,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    final tokens = json['tokens'] as Map<String, dynamic>;
    return AuthResponse(
      message: json['message'] as String,
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
      accessToken: tokens['access'] as String,
      refreshToken: tokens['refresh'] as String,
    );
  }
}

/// Response from register endpoint (no tokens, email verification needed).
class RegisterResponse {
  final String message;
  final UserModel user;

  const RegisterResponse({
    required this.message,
    required this.user,
  });

  factory RegisterResponse.fromJson(Map<String, dynamic> json) {
    return RegisterResponse(
      message: json['message'] as String,
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}

/// Generic message response from forgot-password, reset-password, etc.
class MessageResponse {
  final String message;

  const MessageResponse({required this.message});

  factory MessageResponse.fromJson(Map<String, dynamic> json) {
    return MessageResponse(message: json['message'] as String);
  }
}
