import '../../../anomalies/domain/entities/anomaly_detection.dart';

class AssistantContext {
  const AssistantContext({
    required this.anomalies,
    required this.selectedAnomaly,
    required this.prompts,
    required this.geminiConfigured,
  });
  final List<AnomalyDetection> anomalies;
  final AnomalyDetection? selectedAnomaly;
  final List<String> prompts;
  final bool geminiConfigured;

  factory AssistantContext.fromJson(Map<String, dynamic> json) {
    final selected = json['selected_anomaly'];
    return AssistantContext(
      anomalies: (json['anomalies'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(AnomalyDetection.fromJson)
          .toList(growable: false),
      selectedAnomaly: selected is Map<String, dynamic>
          ? AnomalyDetection.fromJson(selected)
          : null,
      prompts: (json['suggested_prompts'] as List? ?? const [])
          .map((item) => item.toString())
          .toList(growable: false),
      geminiConfigured: json['gemini_configured'] == true,
    );
  }
}

class AssistantConversation {
  const AssistantConversation({
    required this.id,
    required this.anomalyId,
    required this.title,
  });
  final String id, anomalyId, title;
  factory AssistantConversation.fromJson(Map<String, dynamic> json) =>
      AssistantConversation(
        id: json['id']?.toString() ?? '',
        anomalyId: json['anomaly_id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
      );
}

class AssistantMessage {
  const AssistantMessage({
    required this.id,
    required this.sender,
    required this.text,
    required this.createdAt,
    this.streaming = false,
  });
  final String id, sender, text;
  final DateTime? createdAt;
  final bool streaming;
  factory AssistantMessage.fromJson(Map<String, dynamic> json) =>
      AssistantMessage(
        id: json['id']?.toString() ?? '',
        sender: json['sender']?.toString() ?? 'assistant',
        text: json['text']?.toString() ?? '',
        createdAt: DateTime.tryParse(
          json['created_at']?.toString() ?? '',
        )?.toLocal(),
      );
}

class AssistantSocketTicket {
  const AssistantSocketTicket({required this.websocketPath});
  final String websocketPath;
  factory AssistantSocketTicket.fromJson(Map<String, dynamic> json) =>
      AssistantSocketTicket(
        websocketPath: json['websocket_path']?.toString() ?? '',
      );
}
