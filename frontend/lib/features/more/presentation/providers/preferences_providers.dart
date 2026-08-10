import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/data_sources/preferences_data_source.dart';
import '../../data/repositories/preferences_repository_impl.dart';
import '../../domain/entities/user_preferences.dart';
import '../../domain/repositories/preferences_repository.dart';

final preferencesDataSourceProvider = Provider<PreferencesDataSource>(
  (ref) => DummyPreferencesDataSource(),
);
final preferencesRepositoryProvider = Provider<PreferencesRepository>(
  (ref) => PreferencesRepositoryImpl(ref.watch(preferencesDataSourceProvider)),
);
final preferencesProvider = FutureProvider<UserPreferences>(
  (ref) => ref.watch(preferencesRepositoryProvider).getPreferences(),
);
