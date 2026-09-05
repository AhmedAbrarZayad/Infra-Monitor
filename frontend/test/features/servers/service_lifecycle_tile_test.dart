import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/servers/domain/entities/server.dart';
import 'package:frontend/features/servers/presentation/widgets/service_lifecycle_tile.dart';

MonitoredService service({
  ServerStatus status = ServerStatus.healthy,
  String reason = 'telemetry_received',
  int failedChecks = 0,
}) => MonitoredService(
  id: 'service-1',
  serverId: 'server-1',
  name: 'payments',
  displayName: 'Payments API',
  status: status,
  port: 8080,
  lastReportedAt: DateTime.now().subtract(const Duration(seconds: 5)),
  statusChangedAt: DateTime.now().subtract(const Duration(minutes: 1)),
  lifecycleReason: reason,
  consecutiveFailureObservations: failedChecks,
  alertCount: 2,
  metrics: const {
    'cpu_r': MetricReading(value: 12.5, unit: 'percent', recordedAt: null),
    'mem_u': MetricReading(value: 256, unit: 'bytes', recordedAt: null),
  },
);

Future<void> pumpTile(WidgetTester tester, MonitoredService value) =>
    tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ServiceLifecycleTile(service: value),
          ),
        ),
      ),
    );

void main() {
  test('maps lifecycle reasons to safe user-facing messages', () {
    expect(
      serviceLifecycleMessage('service_telemetry_timeout'),
      'Service stopped reporting.',
    );
    expect(
      serviceLifecycleMessage('service_telemetry_delayed'),
      'Service telemetry is delayed.',
    );
    expect(
      serviceLifecycleMessage('application_unreachable'),
      'Application health checks failed.',
    );
    expect(
      serviceLifecycleMessage('collector_unavailable'),
      contains('crash is unconfirmed'),
    );
    expect(serviceLifecycleMessage('new_reason'), contains('unknown'));
  });

  testWidgets('renders collector outage without claiming a service crash', (
    tester,
  ) async {
    await pumpTile(
      tester,
      service(status: ServerStatus.stale, reason: 'collector_unavailable'),
    );

    expect(find.text('STALE'), findsOneWidget);
    expect(find.textContaining('crash is unconfirmed'), findsOneWidget);
    expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
  });

  testWidgets('expanded row shows evidence metrics and pending confirmation', (
    tester,
  ) async {
    await pumpTile(
      tester,
      service(
        status: ServerStatus.warning,
        reason: 'application_unreachable',
        failedChecks: 1,
      ),
    );
    await tester.tap(find.text('Payments API'));
    await tester.pumpAndSettle();

    expect(find.text('LAST REPORTED'), findsOneWidget);
    expect(find.text('STATUS CHANGED'), findsOneWidget);
    expect(find.text('8080'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('12.5 %'), findsOneWidget);
    expect(find.text('256.0 bytes'), findsOneWidget);
    expect(find.textContaining('1 of 2'), findsOneWidget);
  });
}
