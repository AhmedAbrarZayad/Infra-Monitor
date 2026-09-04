import '../../domain/entities/server.dart';

abstract interface class ServersDataSource {
  Future<List<Server>> getServers();
}

class DummyServersDataSource implements ServersDataSource {
  @override
  Future<List<Server>> getServers() async => const [];
}
