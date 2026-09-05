class AnomalyDetection {
  const AnomalyDetection({
    required this.id,
    required this.serverId,
    required this.serverName,
    required this.serviceId,
    required this.serviceName,
    required this.isAnomaly,
    required this.anomalyScore,
    required this.confidenceScore,
    required this.featureValues,
    required this.modelVersion,
    required this.windowStartedAt,
    required this.windowEndedAt,
    required this.detectedAt,
  });

  final String id;
  final String serverId;
  final String serverName;
  final String serviceId;
  final String serviceName;
  final bool isAnomaly;
  final double anomalyScore;
  final double confidenceScore;
  final Map<String, double> featureValues;
  final String modelVersion;
  final DateTime? windowStartedAt;
  final DateTime? windowEndedAt;
  final DateTime? detectedAt;

  factory AnomalyDetection.fromJson(Map<String, dynamic> json) {
    final rawFeatures = json['feature_values'] as Map? ?? const {};
    final features = <String, double>{};
    for (final entry in rawFeatures.entries) {
      if (entry.value case final num value) {
        features[entry.key.toString()] = value.toDouble();
      }
    }
    return AnomalyDetection(
      id: json['id']?.toString() ?? '',
      serverId: json['server_id']?.toString() ?? '',
      serverName: json['server_name']?.toString() ?? '',
      serviceId: json['service_id']?.toString() ?? '',
      serviceName: json['service_name']?.toString() ?? '',
      isAnomaly: json['is_anomaly'] == true,
      anomalyScore: (json['anomaly_score'] as num?)?.toDouble() ?? 0,
      confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 0,
      featureValues: features,
      modelVersion: json['model_version']?.toString() ?? 'Unknown',
      windowStartedAt: _date(json['window_started_at']),
      windowEndedAt: _date(json['window_ended_at']),
      detectedAt: _date(json['detected_at']),
    );
  }

  String get displayService => serviceName.isNotEmpty
      ? serviceName
      : serviceId.isNotEmpty
      ? serviceId
      : 'Unknown service';

  String get displayServer => serverName.isNotEmpty
      ? serverName
      : serverId.isNotEmpty
      ? serverId
      : 'Unknown server';
}

DateTime? _date(dynamic value) =>
    value == null ? null : DateTime.tryParse(value.toString())?.toLocal();
