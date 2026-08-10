enum Severity { critical, high, warning, info }

class FleetMetric {
  const FleetMetric(this.label, this.value, this.caption, this.tone);

  final String label;
  final String value;
  final String caption;
  final Severity? tone;
}

class IncidentSummary {
  const IncidentSummary({
    required this.id,
    required this.severity,
    required this.status,
    required this.title,
    required this.server,
    required this.service,
    required this.environment,
    required this.age,
    required this.owner,
    this.aiNote,
    this.footer,
  });

  final String id;
  final Severity severity;
  final String status;
  final String title;
  final String server;
  final String service;
  final String environment;
  final String age;
  final String owner;
  final String? aiNote;
  final String? footer;
}

class AttentionItem {
  const AttentionItem(this.label, this.resource, this.value, this.severity);

  final String label;
  final String resource;
  final String value;
  final Severity? severity;
}

class AlertItem {
  const AlertItem({
    required this.severity,
    required this.title,
    required this.time,
    required this.resource,
    required this.description,
  });

  final Severity severity;
  final String title;
  final String time;
  final String resource;
  final String description;
}

class HealthItem {
  const HealthItem(this.title, this.value, this.detail, this.isHealthy);

  final String title;
  final String value;
  final String detail;
  final bool isHealthy;
}

class OverviewDashboard {
  const OverviewDashboard({
    required this.serverCount,
    required this.openIncidentCount,
    required this.updatedAt,
    required this.fleetMetrics,
    required this.criticalIncidents,
    required this.highIncidents,
    required this.attentionItems,
    required this.alerts,
    required this.healthItems,
  });

  final int serverCount;
  final int openIncidentCount;
  final String updatedAt;
  final List<FleetMetric> fleetMetrics;
  final List<IncidentSummary> criticalIncidents;
  final List<IncidentSummary> highIncidents;
  final List<AttentionItem> attentionItems;
  final List<AlertItem> alerts;
  final List<HealthItem> healthItems;
}
