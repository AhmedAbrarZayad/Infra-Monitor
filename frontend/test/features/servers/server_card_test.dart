import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/servers/domain/entities/server.dart';
import 'package:frontend/features/servers/presentation/widgets/server_card.dart';

ServerSummary server({MetricReading? cpu}) => ServerSummary(
  id: 'server-1',
  name: 'api-server',
  hostName: 'api-01',
  environment: 'production',
  status: ServerStatus.healthy,
  alertCount: 0,
  cpu: cpu,
  memory: null,
  disk: null,
  lastSeenAt: null,
  serviceCount: 2,
  cpuHistory: const [],
);

void main() {
  testWidgets(
    'renders unavailable metrics as No data and supports navigation tap',
    (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              height: 220,
              child: ServerCard(server: server(), onTap: () => tapped = true),
            ),
          ),
        ),
      );
      expect(find.text('No data'), findsNWidgets(3));
      expect(find.textContaining('2 services'), findsOneWidget);
      await tester.tap(find.text('api-server'));
      expect(tapped, isTrue);
    },
  );

  testWidgets('renders real percentage telemetry', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 220,
            child: ServerCard(
              server: server(
                cpu: const MetricReading(
                  value: 48.6,
                  unit: 'percent',
                  recordedAt: null,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    expect(find.text('49%'), findsOneWidget);
  });
}
