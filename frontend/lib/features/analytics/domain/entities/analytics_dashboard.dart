class AnalyticsMetric {
  const AnalyticsMetric(this.label, this.value, this.change);
  final String label, value, change;
}

class AnalyticsDashboard {
  const AnalyticsDashboard({
    required this.metrics,
    required this.cpu,
    required this.memory,
    required this.latency,
    required this.frequency,
    required this.opened,
    required this.resolved,
    required this.uptime,
    required this.categories,
    required this.servers,
    required this.insights,
  });
  final List<AnalyticsMetric> metrics;
  final List<double> cpu, memory, latency, frequency, opened, resolved, uptime;
  final Map<String, int> categories, servers;
  final List<String> insights;
}
