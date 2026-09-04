enum ServerStatus { critical, warning, healthy, offline, unknown }

ServerStatus serverStatusFromJson(dynamic value) =>
    ServerStatus.values.firstWhere(
      (status) => status.name == value.toString().toLowerCase(),
      orElse: () => ServerStatus.unknown,
    );

double? _number(dynamic value) => value is num ? value.toDouble() : null;
DateTime? _date(dynamic value) =>
    value == null ? null : DateTime.tryParse(value.toString())?.toLocal();

class MetricReading {
  const MetricReading({
    required this.value,
    required this.unit,
    required this.recordedAt,
    this.labels = const {},
  });
  final double value;
  final String unit;
  final DateTime? recordedAt;
  final Map<String, String> labels;

  factory MetricReading.fromJson(Map<String, dynamic> json) => MetricReading(
    value: _number(json['value']) ?? 0,
    unit: json['unit']?.toString() ?? 'unknown',
    recordedAt: _date(json['recorded_at'] ?? json['timestamp']),
    labels:
        (json['labels'] as Map?)?.map(
          (key, value) => MapEntry(key.toString(), value.toString()),
        ) ??
        const {},
  );

  static MetricReading? maybe(dynamic json) =>
      json is Map<String, dynamic> && json['value'] is num
      ? MetricReading.fromJson(json)
      : null;
}

class MetricPoint {
  const MetricPoint({required this.timestamp, required this.value});
  final DateTime timestamp;
  final double value;

  static MetricPoint? maybe(dynamic json) {
    if (json is! Map<String, dynamic>) return null;
    final timestamp = _date(json['timestamp']);
    final value = _number(json['value']);
    return timestamp == null || value == null
        ? null
        : MetricPoint(timestamp: timestamp, value: value);
  }
}

class MetricSeries {
  const MetricSeries({
    required this.code,
    required this.unit,
    required this.available,
    required this.points,
  });
  final String code;
  final String? unit;
  final bool available;
  final List<MetricPoint> points;

  factory MetricSeries.fromJson(Map<String, dynamic> json) => MetricSeries(
    code: json['metric']?.toString() ?? '',
    unit: json['unit']?.toString(),
    available: json['available'] == true,
    points: (json['points'] as List? ?? const [])
        .map(MetricPoint.maybe)
        .whereType<MetricPoint>()
        .toList(growable: false),
  );
}

class ServerSummary {
  const ServerSummary({
    required this.id,
    required this.name,
    required this.hostName,
    required this.environment,
    required this.status,
    required this.alertCount,
    required this.cpu,
    required this.memory,
    required this.disk,
    required this.lastSeenAt,
    required this.serviceCount,
    required this.cpuHistory,
  });
  final String id;
  final String name;
  final String hostName;
  final String environment;
  final ServerStatus status;
  final int alertCount;
  final MetricReading? cpu;
  final MetricReading? memory;
  final MetricReading? disk;
  final DateTime? lastSeenAt;
  final int serviceCount;
  final List<double> cpuHistory;

  factory ServerSummary.fromJson(Map<String, dynamic> json) {
    final metrics = json['metrics'] is Map<String, dynamic>
        ? json['metrics'] as Map<String, dynamic>
        : const <String, dynamic>{};
    return ServerSummary(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      hostName: json['host_name']?.toString() ?? '',
      environment: json['environment']?.toString() ?? '',
      status: serverStatusFromJson(json['status']),
      alertCount: (json['alert_count'] as num?)?.toInt() ?? 0,
      cpu: MetricReading.maybe(metrics['cpu_r']),
      memory: MetricReading.maybe(metrics['mem_u']),
      disk: MetricReading.maybe(metrics['disk_u']),
      lastSeenAt: _date(json['last_seen_at']),
      serviceCount: (json['service_count'] as num?)?.toInt() ?? 0,
      cpuHistory: (json['cpu_history'] as List? ?? const [])
          .whereType<num>()
          .map((value) => (value.toDouble() / 100).clamp(0.0, 1.0))
          .toList(growable: false),
    );
  }
}

typedef Server = ServerSummary;

class ServerHealth {
  const ServerHealth({
    required this.serverId,
    required this.status,
    required this.lastSeenAt,
    required this.activeAlerts,
    required this.metrics,
  });
  final String serverId;
  final ServerStatus status;
  final DateTime? lastSeenAt;
  final int activeAlerts;
  final Map<String, MetricReading?> metrics;

  factory ServerHealth.fromJson(Map<String, dynamic> json) {
    final raw = json['metrics'] is Map<String, dynamic>
        ? json['metrics'] as Map<String, dynamic>
        : const <String, dynamic>{};
    return ServerHealth(
      serverId: json['server_id']?.toString() ?? '',
      status: serverStatusFromJson(json['status']),
      lastSeenAt: _date(json['last_seen_at']),
      activeAlerts: (json['active_alerts'] as num?)?.toInt() ?? 0,
      metrics: raw.map(
        (code, value) => MapEntry(code, MetricReading.maybe(value)),
      ),
    );
  }
}

class MonitoredService {
  const MonitoredService({
    required this.id,
    required this.serverId,
    required this.name,
    required this.displayName,
    required this.status,
    required this.port,
    required this.lastReportedAt,
    required this.alertCount,
    this.metrics = const {},
  });
  final String id;
  final String serverId;
  final String name;
  final String displayName;
  final String status;
  final int? port;
  final DateTime? lastReportedAt;
  final int alertCount;
  final Map<String, MetricReading?> metrics;

  factory MonitoredService.fromJson(Map<String, dynamic> json) {
    final raw = json['metrics'] is Map<String, dynamic>
        ? json['metrics'] as Map<String, dynamic>
        : const <String, dynamic>{};
    return MonitoredService(
      id: json['id']?.toString() ?? '',
      serverId: json['server_id']?.toString() ?? '',
      name: json['service_name']?.toString() ?? '',
      displayName: json['display_name']?.toString() ?? '',
      status: json['status']?.toString() ?? 'UNKNOWN',
      port: (json['port'] as num?)?.toInt(),
      lastReportedAt: _date(json['last_reported_at']),
      alertCount: (json['alert_count'] as num?)?.toInt() ?? 0,
      metrics: raw.map(
        (code, value) => MapEntry(code, MetricReading.maybe(value)),
      ),
    );
  }
}
