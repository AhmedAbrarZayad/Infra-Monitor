/// Environment configuration loaded via --dart-define.
///
/// Usage:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
///   flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api
class EnvConfig {
  EnvConfig._();

  /// Base URL for the backend API.
  /// Android emulator default: http://10.0.2.2:8000/api
  /// Web/desktop default:      http://localhost:8000/api
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api',
  );

  /// Google OAuth 2.0 Web Client ID (for future Google Sign-In).
  static const String googleWebClientId = String.fromEnvironment(
    'GOOGLE_WEB_CLIENT_ID',
    defaultValue: '',
  );

  /// Google OAuth 2.0 Android Client ID (for future Google Sign-In).
  static const String googleAndroidClientId = String.fromEnvironment(
    'GOOGLE_ANDROID_CLIENT_ID',
    defaultValue: '',
  );
}
