import '../entities/analytics_dashboard.dart';

abstract interface class AnalyticsRepository {
  Future<AnalyticsDashboard> getAnalytics();
}
