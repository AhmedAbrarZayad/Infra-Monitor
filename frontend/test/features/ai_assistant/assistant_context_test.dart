import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/ai_assistant/domain/entities/assistant_context.dart';
import 'package:frontend/features/ai_assistant/data/data_sources/assistant_data_source.dart';

void main() {
  test('parses anomaly context and configuration state', () {
    final context = AssistantContext.fromJson({
      'anomalies': [
        {
          'id': 'a-1',
          'server_name': 'Ubuntu Lab',
          'service_name': 'demo-load',
          'is_anomaly': true,
          'anomaly_score': -0.2,
          'confidence_score': 0.2,
          'feature_values': {'cpu_r': 90},
        },
      ],
      'selected_anomaly': {
        'id': 'a-1',
        'service_name': 'demo-load',
        'is_anomaly': true,
      },
      'suggested_prompts': ['What should I check first?'],
      'gemini_configured': true,
    });

    expect(context.anomalies.single.displayServer, 'Ubuntu Lab');
    expect(context.selectedAnomaly?.displayService, 'demo-load');
    expect(context.prompts.single, 'What should I check first?');
    expect(context.geminiConfigured, isTrue);
  });

  test('tolerates empty and older context responses', () {
    final context = AssistantContext.fromJson(const {});
    expect(context.anomalies, isEmpty);
    expect(context.selectedAnomaly, isNull);
    expect(context.prompts, isEmpty);
    expect(context.geminiConfigured, isFalse);
  });

  test('parses persisted assistant messages', () {
    final message = AssistantMessage.fromJson({
      'id': 'm-1',
      'sender': 'assistant',
      'text': 'Crash is not confirmed.',
      'created_at': '2026-09-05T10:00:00Z',
    });
    expect(message.sender, 'assistant');
    expect(message.text, contains('not confirmed'));
    expect(message.createdAt, isNotNull);
  });

  test('derives websocket endpoint from the configured API origin', () {
    final uri = assistantWebSocketUri(
      'http://192.168.0.107:7000/api',
      '/ws/organizations/org/assistant/conversations/chat/?ticket=one-time',
    );
    expect(
      uri.toString(),
      'ws://192.168.0.107:7000/ws/organizations/org/assistant/conversations/chat/?ticket=one-time',
    );

    expect(
      assistantWebSocketUri(
        'https://monitor.example/api',
        '/ws/chat/?ticket=x',
      ).scheme,
      'wss',
    );
  });
}
