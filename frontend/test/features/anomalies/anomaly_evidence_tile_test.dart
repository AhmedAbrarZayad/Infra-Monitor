import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/anomalies/domain/entities/anomaly_detection.dart';
import 'package:frontend/features/anomalies/presentation/widgets/anomaly_evidence_tile.dart';

void main() {
  testWidgets('shows warning language and expanded model evidence', (
    tester,
  ) async {
    final anomaly = AnomalyDetection.fromJson({
      'id': 'detection-1',
      'server_name': 'WSL lab',
      'service_name': 'demo-load',
      'is_anomaly': true,
      'anomaly_score': -0.12,
      'confidence_score': 0.12,
      'model_version': 'model-v1',
      'feature_values': {
        'cpu_r': 82,
        'mem_u': 43008000,
        'disk_r': 1200,
        'disk_w': 700,
        'eth1_fi': 900,
        'eth1_fo': 500,
      },
      'window_started_at': '2026-09-05T10:00:00Z',
      'window_ended_at': '2026-09-05T10:05:00Z',
      'detected_at': '2026-09-05T10:06:00Z',
    });

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(body: AnomalyEvidenceTile(anomaly: anomaly)),
        ),
      ),
    );

    expect(find.textContaining('crash not confirmed'), findsOneWidget);
    expect(find.text('12%'), findsOneWidget);
    await tester.tap(find.text('demo-load'));
    await tester.pumpAndSettle();
    expect(find.text('model-v1'), findsOneWidget);
    expect(find.text('ANOMALY SCORE'), findsOneWidget);
    expect(find.text('CPU'), findsOneWidget);
    expect(find.text('Unavailable'), findsOneWidget);
    expect(find.textContaining('43008000'), findsNothing);
    expect(find.text('NETWORK OUT'), findsOneWidget);
    expect(find.text('View assignment'), findsOneWidget);
    expect(find.text('Ask AI'), findsOneWidget);

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: AnomalyEvidenceTile(
              key: const ValueKey('editable-anomaly'),
              anomaly: anomaly,
              canAssign: true,
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('demo-load'));
    await tester.pumpAndSettle();
    expect(find.text('Manage assignment'), findsOneWidget);
  });
}
