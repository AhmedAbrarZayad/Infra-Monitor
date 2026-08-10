import '../../domain/entities/user_preferences.dart';

abstract interface class PreferencesDataSource {
  Future<UserPreferences> getPreferences();
}

class DummyPreferencesDataSource implements PreferencesDataSource {
  @override
  Future<UserPreferences> getPreferences() async => const UserPreferences(
    name: 'A. Perera',
    email: 'a.perera@acme.io',
    role: 'Administrator',
    environment: 'Production',
    streamState: 'live',
    notifications: 'critical + high only',
    theme: 'dark (system)',
    refreshInterval: '5s',
    timezone: 'UTC',
  );
}
