import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/data_sources/analytics_data_source.dart';
import '../../data/repositories/analytics_repository_impl.dart';
import '../../domain/entities/analytics_dashboard.dart';
import '../../domain/repositories/analytics_repository.dart';

final analyticsDataSourceProvider = Provider<AnalyticsDataSource>(
  (ref) => DummyAnalyticsDataSource(),
);
final analyticsRepositoryProvider = Provider<AnalyticsRepository>(
  (ref) => AnalyticsRepositoryImpl(ref.watch(analyticsDataSourceProvider)),
);
final analyticsProvider = FutureProvider<AnalyticsDashboard>(
  (ref) => ref.watch(analyticsRepositoryProvider).getAnalytics(),
);
