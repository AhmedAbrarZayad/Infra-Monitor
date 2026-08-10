import '../entities/incident.dart';

abstract interface class IncidentsRepository {
  Future<List<Incident>> getIncidents();
}
