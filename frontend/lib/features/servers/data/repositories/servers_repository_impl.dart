import '../../domain/entities/server.dart';
import '../../domain/repositories/servers_repository.dart';
import '../data_sources/servers_data_source.dart';

class ServersRepositoryImpl implements ServersRepository {
  const ServersRepositoryImpl(this._dataSource);

  final ServersDataSource _dataSource;

  @override
  Future<List<Server>> getServers() => _dataSource.getServers();
}
