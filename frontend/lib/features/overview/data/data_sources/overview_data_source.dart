import '../../domain/entities/overview_dashboard.dart';

abstract interface class OverviewDataSource {
  Future<OverviewDashboard> getDashboard();
}

/// Temporary local implementation. Replace this provider with an API data
/// source when the backend is ready; presentation code does not change.
class DummyOverviewDataSource implements OverviewDataSource {
  @override
  Future<OverviewDashboard> getDashboard() async {
    await Future<void>.delayed(const Duration(milliseconds: 250));
    return const OverviewDashboard(
      serverCount: 6,
      openIncidentCount: 4,
      updatedAt: '12:18:09',
      fleetMetrics: [
        FleetMetric('HEALTHY', '1', 'servers', null),
        FleetMetric('WARNING', '3', 'servers', Severity.warning),
        FleetMetric('CRITICAL', '1', 'servers', Severity.critical),
        FleetMetric('OFFLINE', '1', 'no heartbeat', null),
        FleetMetric('UNKNOWN', '1', 'awaiting agent', null),
        FleetMetric('ALERTS 1H', '8', '+3 vs prev', Severity.info),
      ],
      criticalIncidents: [
        IncidentSummary(
          id: 'INC-2481',
          severity: Severity.critical,
          status: 'ACKNOWLEDGED',
          title: 'Database connection timeout on Payment Service',
          server: 'payment-service-prod',
          service: 'payment-api',
          environment: 'Production',
          age: '18m ago',
          owner: 'A. Perera',
          aiNote: 'AI conf: medium',
          footer: 'acknowledged 12:46:03 UTC',
        ),
        IncidentSummary(
          id: 'INC-2479',
          severity: Severity.critical,
          status: 'NEW',
          title: 'Server heartbeat lost for worker-queue-prod',
          server: 'worker-queue-prod',
          service: 'worker-queue',
          environment: 'Production',
          age: '6m ago',
          owner: 'unassigned',
          aiNote: 'Not enough evidence',
          footer: 'not acknowledged',
        ),
      ],
      highIncidents: [
        IncidentSummary(
          id: 'INC-2480',
          severity: Severity.high,
          status: 'INVESTIGATING',
          title: 'Memory usage exceeded 90% on auth-api-prod',
          server: 'auth-api-prod',
          service: 'auth-api',
          environment: 'Production',
          age: '37m ago',
          owner: 'M. Fernando',
        ),
      ],
      attentionItems: [
        AttentionItem(
          'HIGHEST CPU',
          'payment-service-prod',
          '96%',
          Severity.critical,
        ),
        AttentionItem(
          'HIGHEST MEMORY',
          'auth-api-prod',
          '91%',
          Severity.warning,
        ),
        AttentionItem(
          'LOW DISK SPACE',
          'db-primary-prod',
          '82% used',
          Severity.warning,
        ),
        AttentionItem('RECENT OUTAGE', 'worker-queue-prod', 'offline 6m', null),
        AttentionItem(
          'HIGH ERROR RATE',
          'web-frontend-prod',
          '4.1%',
          Severity.warning,
        ),
      ],
      recentAnomalies: [],
      alerts: [
        AlertItem(
          severity: Severity.critical,
          title: 'CPU 96% sustained 7m',
          time: '12:41',
          resource: 'payment-service-prod',
          description:
              'Threshold 95% breached; DB timeouts observed alongside.',
        ),
        AlertItem(
          severity: Severity.critical,
          title: 'Heartbeat lost',
          time: '12:53',
          resource: 'worker-queue-prod',
          description: 'No agent telemetry for 6m 12s.',
        ),
        AlertItem(
          severity: Severity.high,
          title: 'Memory 91%',
          time: '12:22',
          resource: 'auth-api-prod',
          description: 'Heap growth without traffic increase.',
        ),
        AlertItem(
          severity: Severity.warning,
          title: 'Disk 82%',
          time: '11:58',
          resource: 'db-primary-prod',
          description: 'Free space trending to 15% floor.',
        ),
        AlertItem(
          severity: Severity.info,
          title: 'Release 4.18.2',
          time: '12:38',
          resource: 'payment-service-prod',
          description: 'Deployment recorded for correlation.',
        ),
      ],
      healthItems: [
        HealthItem(
          'Agent ingestion',
          '6 of 6 agents reporting',
          '1 agent stale (worker-queue-prod)',
          false,
        ),
        HealthItem(
          'Backend API',
          'Operational · p95 118ms',
          'All ingestion workers healthy',
          true,
        ),
        HealthItem(
          'Last data received',
          '3s ago',
          'Streaming over websocket',
          true,
        ),
      ],
    );
  }
}
