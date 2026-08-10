import '../entities/user_preferences.dart';

abstract interface class PreferencesRepository {
  Future<UserPreferences> getPreferences();
}
