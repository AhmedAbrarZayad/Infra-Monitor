import '../../domain/entities/overview_dashboard.dart';
import '../../domain/repositories/overview_repository.dart';
import '../data_sources/overview_data_source.dart';

class OverviewRepositoryImpl implements OverviewRepository {
  const OverviewRepositoryImpl(this._dataSource);

  final OverviewDataSource _dataSource;

  @override
  Future<OverviewDashboard> getDashboard() => _dataSource.getDashboard();
}
