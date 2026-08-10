import '../../domain/entities/incident.dart';
import '../../domain/repositories/incidents_repository.dart';
import '../data_sources/incidents_data_source.dart';

class IncidentsRepositoryImpl implements IncidentsRepository {
  const IncidentsRepositoryImpl(this.source);
  final IncidentsDataSource source;
  @override
  Future<List<Incident>> getIncidents() => source.getIncidents();
}
