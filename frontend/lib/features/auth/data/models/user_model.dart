/// User data model returned from auth API responses.
class UserModel {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final bool isEmailVerified;
  final String createdAt;

  const UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    required this.isEmailVerified,
    required this.createdAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      username: json['username'] as String,
      email: json['email'] as String,
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      role: json['role'] as String? ?? 'viewer',
      isEmailVerified: json['is_email_verified'] as bool? ?? false,
      createdAt: json['created_at'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'first_name': firstName,
      'last_name': lastName,
      'role': role,
      'is_email_verified': isEmailVerified,
      'created_at': createdAt,
    };
  }
}
