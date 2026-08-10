import '../../domain/entities/analytics_dashboard.dart';
import '../../domain/repositories/analytics_repository.dart';
import '../data_sources/analytics_data_source.dart';

class AnalyticsRepositoryImpl implements AnalyticsRepository {
  const AnalyticsRepositoryImpl(this.source);
  final AnalyticsDataSource source;
  @override
  Future<AnalyticsDashboard> getAnalytics() => source.getAnalytics();
}
