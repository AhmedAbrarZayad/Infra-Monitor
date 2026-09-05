import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/servers/domain/entities/server.dart';
import 'package:frontend/features/servers/presentation/providers/servers_providers.dart';

void main() {
  test('server parser preserves missing telemetry as null', () {
    final server = ServerSummary.fromJson({
      'id': 'server-1',
      'name': 'api',
      'host_name': 'api-01',
      'environment': 'production',
      'status': 'HEALTHY',
      'metrics': {
        'cpu_r': null,
        'mem_u': {'value': 42.5, 'unit': 'percent'},
      },
      'cpu_history': [10, 25],
    });
    expect(server.id, 'server-1');
    expect(server.cpu, isNull);
    expect(server.memory?.value, 42.5);
    expect(server.cpuHistory, [.1, .25]);
  });

  test('metric range distinguishes empty from unavailable', () {
    final empty = MetricSeries.fromJson({
      'metric': 'cpu_r',
      'unit': 'percent',
      'available': true,
      'points': [],
    });
    final unavailable = MetricSeries.fromJson({
      'metric': 'cpu_r',
      'unit': 'percent',
      'available': false,
      'points': [],
    });
    expect(empty.available, isTrue);
    expect(empty.points, isEmpty);
    expect(unavailable.available, isFalse);
  });

  test('malformed metric points are ignored', () {
    final series = MetricSeries.fromJson({
      'available': true,
      'points': [
        {'timestamp': 'invalid', 'value': 1},
        {'timestamp': '2026-09-04T00:00:00Z', 'value': 3.5},
        {'timestamp': '2026-09-04T00:00:00Z', 'value': 'bad'},
      ],
    });
    expect(series.points, hasLength(1));
    expect(series.points.single.value, 3.5);
  });

  test('service parser includes health metrics', () {
    final service = MonitoredService.fromJson({
      'id': 'service-1',
      'server_id': 'server-1',
      'service_name': 'payments',
      'status': 'STALE',
      'port': 9090,
      'status_changed_at': '2026-09-04T01:00:00Z',
      'lifecycle_reason': 'service_telemetry_delayed',
      'consecutive_failure_observations': 1,
      'metrics': {
        'cpu_r': {'value': 2.2, 'unit': 'percent'},
      },
    });
    expect(service.name, 'payments');
    expect(service.port, 9090);
    expect(service.status, ServerStatus.stale);
    expect(service.statusChangedAt, isNotNull);
    expect(service.lifecycleReason, 'service_telemetry_delayed');
    expect(service.consecutiveFailureObservations, 1);
    expect(service.metrics['cpu_r']?.value, 2.2);
  });

  test('service parser tolerates older and unknown lifecycle responses', () {
    final service = MonitoredService.fromJson({
      'id': 'service-1',
      'status': 'FUTURE_STATUS',
    });

    expect(service.status, ServerStatus.unknown);
    expect(service.statusChangedAt, isNull);
    expect(service.lifecycleReason, 'awaiting_telemetry');
    expect(service.consecutiveFailureObservations, 0);
  });

  test('status parser supports every lifecycle status', () {
    expect(serverStatusFromJson('HEALTHY'), ServerStatus.healthy);
    expect(serverStatusFromJson('WARNING'), ServerStatus.warning);
    expect(serverStatusFromJson('CRITICAL'), ServerStatus.critical);
    expect(serverStatusFromJson('STALE'), ServerStatus.stale);
    expect(serverStatusFromJson('OFFLINE'), ServerStatus.offline);
    expect(serverStatusFromJson('UNKNOWN'), ServerStatus.unknown);
  });

  test('range step keeps every request below the backend point cap', () {
    expect(metricStep(const Duration(hours: 1)), 15);
    expect(metricStep(const Duration(days: 1)), 60);
    expect(metricStep(const Duration(days: 7)), 300);
    expect(metricStep(const Duration(days: 30)), 1800);
  });
}
