import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/data_sources/incidents_data_source.dart';
import '../../data/repositories/incidents_repository_impl.dart';
import '../../domain/entities/incident.dart';
import '../../domain/repositories/incidents_repository.dart';

final incidentsDataSourceProvider = Provider<IncidentsDataSource>(
  (ref) => DummyIncidentsDataSource(),
);
final incidentsRepositoryProvider = Provider<IncidentsRepository>(
  (ref) => IncidentsRepositoryImpl(ref.watch(incidentsDataSourceProvider)),
);
final incidentsProvider = FutureProvider<List<Incident>>(
  (ref) => ref.watch(incidentsRepositoryProvider).getIncidents(),
);
