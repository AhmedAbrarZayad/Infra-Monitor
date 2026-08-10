import '../entities/server.dart';

abstract interface class ServersRepository {
  Future<List<Server>> getServers();
}
