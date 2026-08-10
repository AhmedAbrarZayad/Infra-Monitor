import '../../domain/entities/user_preferences.dart';
import '../../domain/repositories/preferences_repository.dart';
import '../data_sources/preferences_data_source.dart';

class PreferencesRepositoryImpl implements PreferencesRepository {
  const PreferencesRepositoryImpl(this.source);
  final PreferencesDataSource source;
  @override
  Future<UserPreferences> getPreferences() => source.getPreferences();
}
