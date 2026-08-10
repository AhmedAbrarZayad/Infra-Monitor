import '../../domain/entities/incident.dart';

abstract interface class IncidentsDataSource {
  Future<List<Incident>> getIncidents();
}

class DummyIncidentsDataSource implements IncidentsDataSource {
  @override
  Future<List<Incident>> getIncidents() async {
    await Future<void>.delayed(const Duration(milliseconds: 180));
    return const [
      Incident(
        id: 'INC-2481',
        severity: 'CRITICAL',
        status: 'ACKNOWLEDGED',
        title: 'Database connection timeout on Payment Service',
        server: 'payment-service-prod',
        service: 'payment-api',
        environment: 'Production',
        age: '18m ago',
        owner: 'A. Perera',
        aiConfidence: 'AI conf: medium',
        acknowledgement: 'acknowledged 12:46:03 UTC',
      ),
      Incident(
        id: 'INC-2480',
        severity: 'HIGH',
        status: 'INVESTIGATING',
        title: 'Memory usage exceeded 90% on auth-api-prod',
        server: 'auth-api-prod',
        service: 'auth-api',
        environment: 'Production',
        age: '37m ago',
        owner: 'M. Fernando',
        aiConfidence: 'AI conf: high',
        acknowledgement: 'acknowledged 12:24:48 UTC',
      ),
      Incident(
        id: 'INC-2479',
        severity: 'CRITICAL',
        status: 'NEW',
        title: 'Server heartbeat lost for worker-queue-prod',
        server: 'worker-queue-prod',
        service: 'worker-queue',
        environment: 'Production',
        age: '6m ago',
        owner: 'unassigned',
        aiConfidence: 'Not enough evidence',
        acknowledgement: 'not acknowledged',
      ),
      Incident(
        id: 'INC-2478',
        severity: 'WARNING',
        status: 'OPEN',
        title: 'Disk capacity approaching threshold',
        server: 'db-primary-prod',
        service: 'postgres',
        environment: 'Production',
        age: '1h ago',
        owner: 'D. Silva',
        aiConfidence: 'AI conf: medium',
        acknowledgement: 'not acknowledged',
      ),
      Incident(
        id: 'INC-2477',
        severity: 'INFO',
        status: 'RESOLVED',
        title: 'Deployment completed successfully',
        server: 'web-frontend-prod',
        service: 'frontend',
        environment: 'Production',
        age: '2h ago',
        owner: 'system',
        aiConfidence: 'Correlated',
        acknowledgement: 'resolved 11:08:20 UTC',
      ),
      Incident(
        id: 'INC-2476',
        severity: 'HIGH',
        status: 'OPEN',
        title: 'Elevated API error rate detected',
        server: 'payment-service-prod',
        service: 'payment-api',
        environment: 'Production',
        age: '3h ago',
        owner: 'unassigned',
        aiConfidence: 'AI conf: high',
        acknowledgement: 'not acknowledged',
      ),
    ];
  }
}
