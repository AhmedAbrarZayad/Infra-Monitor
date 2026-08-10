import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/data_sources/servers_data_source.dart';
import '../../data/repositories/servers_repository_impl.dart';
import '../../domain/entities/server.dart';
import '../../domain/repositories/servers_repository.dart';

final serversDataSourceProvider = Provider<ServersDataSource>(
  (ref) => DummyServersDataSource(),
);
final serversRepositoryProvider = Provider<ServersRepository>(
  (ref) => ServersRepositoryImpl(ref.watch(serversDataSourceProvider)),
);
final serversProvider = FutureProvider<List<Server>>(
  (ref) => ref.watch(serversRepositoryProvider).getServers(),
);
