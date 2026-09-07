/// Domain entities for the Request Shield feature.

class ShieldAnalytics {
  const ShieldAnalytics({
    required this.zoneDistribution,
    required this.topOffendingIps,
    required this.zoneTrend,
    required this.totalRequests,
    required this.pendingSuggestions,
    required this.shieldEnabled,
    required this.hours,
  });

  final Map<String, int> zoneDistribution;
  final List<OffendingIp> topOffendingIps;
  final List<ZoneTrendEntry> zoneTrend;
  final int totalRequests;
  final int pendingSuggestions;
  final bool shieldEnabled;
  final int hours;

  int get greenCount => zoneDistribution['GREEN'] ?? 0;
  int get grayCount => zoneDistribution['GRAY'] ?? 0;
  int get redCount => zoneDistribution['RED'] ?? 0;
  int get unclassifiedCount => zoneDistribution['UNCLASSIFIED'] ?? 0;

  double get greenPercent =>
      totalRequests > 0 ? greenCount / totalRequests * 100 : 0;
  double get grayPercent =>
      totalRequests > 0 ? grayCount / totalRequests * 100 : 0;
  double get redPercent =>
      totalRequests > 0 ? redCount / totalRequests * 100 : 0;
}

class OffendingIp {
  const OffendingIp({
    required this.ip,
    required this.redCount,
    required this.grayCount,
    required this.total,
  });
  final String ip;
  final int redCount;
  final int grayCount;
  final int total;

  factory OffendingIp.fromJson(Map<String, dynamic> json) => OffendingIp(
        ip: json['source_ip'] ?? '',
        redCount: json['red_count'] ?? 0,
        grayCount: json['gray_count'] ?? 0,
        total: json['total'] ?? 0,
      );
}

class ZoneTrendEntry {
  const ZoneTrendEntry({
    required this.bucket,
    required this.zone,
    required this.count,
  });
  final String bucket;
  final String zone;
  final int count;

  factory ZoneTrendEntry.fromJson(Map<String, dynamic> json) =>
      ZoneTrendEntry(
        bucket: json['bucket'] ?? '',
        zone: json['zone'] ?? '',
        count: json['count'] ?? 0,
      );
}

class RequestLogEntry {
  const RequestLogEntry({
    required this.id,
    required this.timestamp,
    required this.sourceIp,
    required this.method,
    required this.path,
    required this.statusCode,
    required this.userAgent,
    required this.zone,
    required this.confidence,
    required this.threatSignals,
    required this.classifiedBy,
    required this.source,
    this.adminVerdict,
  });

  final String id;
  final String timestamp;
  final String sourceIp;
  final String method;
  final String path;
  final int? statusCode;
  final String userAgent;
  final String zone;
  final double? confidence;
  final List<String> threatSignals;
  final String classifiedBy;
  final String source;
  final String? adminVerdict;

  factory RequestLogEntry.fromJson(Map<String, dynamic> json) =>
      RequestLogEntry(
        id: json['id'] ?? '',
        timestamp: json['timestamp'] ?? '',
        sourceIp: json['source_ip'] ?? '',
        method: json['method'] ?? '',
        path: json['path'] ?? '',
        statusCode: json['status_code'],
        userAgent: json['user_agent'] ?? '',
        zone: json['zone'] ?? 'UNCLASSIFIED',
        confidence: (json['confidence'] as num?)?.toDouble(),
        threatSignals: (json['threat_signals'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        classifiedBy: json['classified_by'] ?? '',
        source: json['source'] ?? '',
        adminVerdict: json['admin_verdict'],
      );
}

class ThreatSuggestion {
  const ThreatSuggestion({
    required this.id,
    required this.ipAddress,
    required this.triggerZone,
    required this.requestCount,
    required this.samplePaths,
    required this.topThreatSignals,
    required this.status,
    required this.createdAt,
    this.geminiAnalysis,
    this.adminNotes,
  });

  final String id;
  final String ipAddress;
  final String triggerZone;
  final int requestCount;
  final List<String> samplePaths;
  final List<String> topThreatSignals;
  final String status;
  final String createdAt;
  final String? geminiAnalysis;
  final String? adminNotes;

  factory ThreatSuggestion.fromJson(Map<String, dynamic> json) =>
      ThreatSuggestion(
        id: json['id'] ?? '',
        ipAddress: json['ip_address'] ?? '',
        triggerZone: json['trigger_zone'] ?? '',
        requestCount: json['request_count'] ?? 0,
        samplePaths: (json['sample_paths'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        topThreatSignals: (json['top_threat_signals'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        status: json['status'] ?? 'PENDING',
        createdAt: json['created_at'] ?? '',
        geminiAnalysis: json['gemini_analysis'],
        adminNotes: json['admin_notes'],
      );
}

class ShieldConfig {
  const ShieldConfig({
    required this.enabled,
    required this.geminiEscalation,
    required this.platformSelfMonitor,
    required this.redSuggestionThreshold,
    required this.graySuggestionThreshold,
    required this.suggestionWindowMinutes,
    required this.notifyOnRed,
  });

  final bool enabled;
  final bool geminiEscalation;
  final bool platformSelfMonitor;
  final int redSuggestionThreshold;
  final int graySuggestionThreshold;
  final int suggestionWindowMinutes;
  final bool notifyOnRed;

  factory ShieldConfig.fromJson(Map<String, dynamic> json) => ShieldConfig(
        enabled: json['enabled'] ?? false,
        geminiEscalation: json['gemini_escalation'] ?? true,
        platformSelfMonitor: json['platform_self_monitor'] ?? true,
        redSuggestionThreshold: json['red_suggestion_threshold'] ?? 5,
        graySuggestionThreshold: json['gray_suggestion_threshold'] ?? 20,
        suggestionWindowMinutes: json['suggestion_window_minutes'] ?? 60,
        notifyOnRed: json['notify_on_red'] ?? true,
      );
}
