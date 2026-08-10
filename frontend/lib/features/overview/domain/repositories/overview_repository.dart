import '../entities/overview_dashboard.dart';

abstract interface class OverviewRepository {
  Future<OverviewDashboard> getDashboard();
}
