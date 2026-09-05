import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/anomalies/domain/entities/anomaly_detection.dart';

void main() {
  test('parses a complete anomaly response', () {
    final anomaly = AnomalyDetection.fromJson({
      'id': 'detection-1',
      'server_id': 'server-1',
      'server_name': 'WSL lab',
      'service_id': 'service-1',
      'service_name': 'demo-load',
      'is_anomaly': true,
      'anomaly_score': -0.12,
      'confidence_score': 0.12,
      'model_version': 'model-v1',
      'feature_values': {'cpu_r': 82, 'mem_u': 43.5},
      'window_started_at': '2026-09-05T10:00:00Z',
      'window_ended_at': '2026-09-05T10:05:00Z',
      'detected_at': '2026-09-05T10:06:00Z',
    });

    expect(anomaly.displayService, 'demo-load');
    expect(anomaly.displayServer, 'WSL lab');
    expect(anomaly.isAnomaly, isTrue);
    expect(anomaly.anomalyScore, -0.12);
    expect(anomaly.featureValues, {'cpu_r': 82.0, 'mem_u': 43.5});
    expect(anomaly.modelVersion, 'model-v1');
    expect(anomaly.windowStartedAt, isNotNull);
  });

  test('tolerates older responses without names or model metadata', () {
    final anomaly = AnomalyDetection.fromJson({
      'service_id': 'service-1',
      'server_id': 'server-1',
      'feature_values': {'cpu_r': 'invalid'},
    });

    expect(anomaly.displayService, 'service-1');
    expect(anomaly.displayServer, 'server-1');
    expect(anomaly.modelVersion, 'Unknown');
    expect(anomaly.featureValues, isEmpty);
    expect(anomaly.detectedAt, isNull);
  });
}
