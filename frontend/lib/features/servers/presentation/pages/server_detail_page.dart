import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/api/operational_api.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/selection_pill.dart';
import '../../../anomalies/domain/entities/anomaly_detection.dart';
import '../../../anomalies/presentation/providers/anomaly_providers.dart';
import '../../../anomalies/presentation/widgets/anomaly_evidence_tile.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../../overview/presentation/providers/overview_providers.dart';
import '../../domain/entities/server.dart';
import '../providers/servers_providers.dart';
import '../widgets/metric_history_chart.dart';
import '../widgets/server_status_badge.dart';
import '../widgets/service_lifecycle_tile.dart';

const _metricLabels = <String, String>{
  'cpu_r': 'CPU utilization',
  'mem_u': 'Memory utilization',
  'load_1': 'Load average (1m)',
  'load_5': 'Load average (5m)',
  'disk_u': 'Disk utilization',
  'disk_r': 'Disk read',
  'disk_w': 'Disk write',
  'disk_q': 'Disk queue',
  'eth1_fi': 'Network input',
  'eth1_fo': 'Network output',
  'tcp_timeouts': 'TCP timeouts',
};
const _ranges = <String, Duration>{
  '1h': Duration(hours: 1),
  '24h': Duration(days: 1),
  '7d': Duration(days: 7),
  '30d': Duration(days: 30),
};

class ServerDetailPage extends ConsumerStatefulWidget {
  const ServerDetailPage({required this.serverId, super.key});
  final String serverId;

  @override
  ConsumerState<ServerDetailPage> createState() => _ServerDetailPageState();
}

class _ServerDetailPageState extends ConsumerState<ServerDetailPage> {
  String metric = 'cpu_r';
  String range = '1h';
  String? _resolvingId;

  Future<void> _refresh() async {
    final organization = ref.read(organizationContextProvider);
    final canViewHostMetrics =
        organization is OrganizationReady &&
        organization.activeMembership.capabilities.canViewHostMetrics;
    ref.invalidate(serverProvider(widget.serverId));
    ref.invalidate(serverServicesProvider(widget.serverId));
    ref.invalidate(serverAnomaliesProvider(widget.serverId));
    if (canViewHostMetrics) {
      ref.invalidate(serverHealthProvider(widget.serverId));
      ref.invalidate(
        serverMetricProvider(
          MetricRequest(
            serverId: widget.serverId,
            metric: metric,
            range: _ranges[range]!,
          ),
        ),
      );
      await ref.read(serverHealthProvider(widget.serverId).future);
    } else {
      await ref.read(serverProvider(widget.serverId).future);
    }
  }

  Future<void> _resolve(AnomalyDetection anomaly) async {
    setState(() => _resolvingId = anomaly.id);
    try {
      await resolveAnomaly(ref, anomaly.id);
      ref.invalidate(serverAnomaliesProvider(widget.serverId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${anomaly.displayService} marked resolved.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to resolve the anomaly.')),
        );
      }
    } finally {
      if (mounted) setState(() => _resolvingId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final server = ref.watch(serverProvider(widget.serverId));
    final organization = ref.watch(organizationContextProvider);
    final canViewHostMetrics =
        organization is OrganizationReady &&
        organization.activeMembership.capabilities.canViewHostMetrics;
    final health = canViewHostMetrics
        ? ref.watch(serverHealthProvider(widget.serverId))
        : null;
    final services = ref.watch(serverServicesProvider(widget.serverId));
    final anomalies = ref.watch(serverAnomaliesProvider(widget.serverId));
    final series = canViewHostMetrics
        ? ref.watch(
            serverMetricProvider(
              MetricRequest(
                serverId: widget.serverId,
                metric: metric,
                range: _ranges[range]!,
              ),
            ),
          )
        : null;
    return Scaffold(
      appBar: AppBar(
        title: Text(server.asData?.value.name ?? 'Server details'),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(12),
          children: [
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1180),
              child: server.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, _) => _ErrorPanel(
                  message: '$error',
                  onRetry: () =>
                      ref.invalidate(serverProvider(widget.serverId)),
                ),
                data: (summary) => Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _Header(summary: summary, health: health?.asData?.value),
                    if (canViewHostMetrics) ...[
                      const SizedBox(height: 12),
                      health!.when(
                        loading: () =>
                            const AppPanel(child: LinearProgressIndicator()),
                        error: (error, _) => _ErrorPanel(
                          message: 'Health unavailable: $error',
                          onRetry: () => ref.invalidate(
                            serverHealthProvider(widget.serverId),
                          ),
                        ),
                        data: (value) => _HealthGrid(health: value),
                      ),
                      const SizedBox(height: 12),
                      _HistoryPanel(
                        metric: metric,
                        range: range,
                        series: series!,
                        onMetric: (value) => setState(() => metric = value),
                        onRange: (value) => setState(() => range = value),
                      ),
                    ],
                    const SizedBox(height: 12),
                    services.when(
                      loading: () =>
                          const AppPanel(child: LinearProgressIndicator()),
                      error: (error, _) => _ErrorPanel(
                        message: 'Services unavailable: $error',
                        onRetry: () => ref.invalidate(
                          serverServicesProvider(widget.serverId),
                        ),
                      ),
                      data: (items) => _LifecycleServicesPanel(
                        services: items,
                        canManageAdmins:
                            organization is OrganizationReady &&
                            organization
                                .activeMembership
                                .capabilities
                                .canManageServiceAdmins,
                      ),
                    ),
                    const SizedBox(height: 12),
                    anomalies.when(
                      loading: () =>
                          const AppPanel(child: LinearProgressIndicator()),
                      error: (error, _) => _ErrorPanel(
                        message: 'Anomaly history unavailable: $error',
                        onRetry: () => ref.invalidate(
                          serverAnomaliesProvider(widget.serverId),
                        ),
                      ),
                      data: (items) => _AnomalyHistoryPanel(
                        anomalies: items,
                        resolvingId: _resolvingId,
                        onResolve: _resolve,
                        canAssign:
                            organization is OrganizationReady &&
                            organization
                                .activeMembership
                                .capabilities
                                .canAssignWork,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.summary, required this.health});
  final ServerSummary summary;
  final ServerHealth? health;
  @override
  Widget build(BuildContext context) => AppPanel(
    child: Wrap(
      spacing: 20,
      runSpacing: 12,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        ServerStatusBadge(status: health?.status ?? summary.status),
        _Fact('HOST', summary.hostName.isEmpty ? 'Unknown' : summary.hostName),
        _Fact('ENVIRONMENT', summary.environment),
        _Fact(
          'LAST SEEN',
          relativeTime(health?.lastSeenAt ?? summary.lastSeenAt),
        ),
        _Fact('ACTIVE ALERTS', '${health?.activeAlerts ?? summary.alertCount}'),
      ],
    ),
  );
}

class _Fact extends StatelessWidget {
  const _Fact(this.label, this.value);
  final String label, value;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(color: Color(0xFF8993A4), fontSize: 9),
      ),
      const SizedBox(height: 3),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
    ],
  );
}

class _HealthGrid extends StatelessWidget {
  const _HealthGrid({required this.health});
  final ServerHealth health;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final width = constraints.maxWidth >= 700
          ? (constraints.maxWidth - 24) / 3
          : constraints.maxWidth;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: _metricLabels.entries
            .map(
              (entry) => SizedBox(
                width: width,
                child: _MetricTile(
                  label: entry.value,
                  reading: health.metrics[entry.key],
                ),
              ),
            )
            .toList(),
      );
    },
  );
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.label, required this.reading});
  final String label;
  final MetricReading? reading;
  @override
  Widget build(BuildContext context) => AppPanel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: Color(0xFF8993A4), fontSize: 10),
        ),
        const SizedBox(height: 8),
        Text(
          reading == null
              ? 'No data'
              : '${_compact(reading!.value)} ${_unit(reading!.unit)}',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: reading == null ? const Color(0xFF8993A4) : Colors.white,
          ),
        ),
      ],
    ),
  );
}

class _HistoryPanel extends StatelessWidget {
  const _HistoryPanel({
    required this.metric,
    required this.range,
    required this.series,
    required this.onMetric,
    required this.onRange,
  });
  final String metric, range;
  final AsyncValue<MetricSeries> series;
  final ValueChanged<String> onMetric, onRange;
  @override
  Widget build(BuildContext context) => AppPanel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'METRIC HISTORY',
          style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 1.2),
        ),
        const SizedBox(height: 12),
        DropdownButton<String>(
          value: metric,
          isExpanded: true,
          items: _metricLabels.entries
              .map(
                (entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Text(entry.value),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value != null) onMetric(value);
          },
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: _ranges.keys
              .map(
                (item) => SelectionPill(
                  label: item,
                  selected: range == item,
                  onTap: () => onRange(item),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 220,
          child: series.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => Center(
              child: Text(
                'Unable to load telemetry\n$error',
                textAlign: TextAlign.center,
              ),
            ),
            data: (value) => !value.available
                ? const Center(child: Text('Telemetry unavailable'))
                : value.points.isEmpty
                ? const Center(child: Text('No samples in this period'))
                : Column(
                    children: [
                      Align(
                        alignment: Alignment.centerRight,
                        child: Text(
                          '${_compact(value.points.last.value)} ${_unit(value.unit ?? 'unknown')}',
                          style: const TextStyle(fontFamily: 'monospace'),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Expanded(child: MetricHistoryChart(points: value.points)),
                    ],
                  ),
          ),
        ),
      ],
    ),
  );
}

class _LifecycleServicesPanel extends StatelessWidget {
  const _LifecycleServicesPanel({
    required this.services,
    required this.canManageAdmins,
  });
  final List<MonitoredService> services;
  final bool canManageAdmins;

  @override
  Widget build(BuildContext context) => AppPanel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'DISCOVERED SERVICES (${services.length})',
          style: const TextStyle(
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 12),
        if (services.isEmpty)
          const Text('No monitored Docker services discovered.')
        else
          ...services.map(
            (service) => ServiceLifecycleTile(
              service: service,
              canManageAdmins: canManageAdmins,
            ),
          ),
      ],
    ),
  );
}

class _AnomalyHistoryPanel extends StatelessWidget {
  const _AnomalyHistoryPanel({
    required this.anomalies,
    required this.resolvingId,
    required this.onResolve,
    required this.canAssign,
  });

  final List<AnomalyDetection> anomalies;
  final String? resolvingId;
  final Future<void> Function(AnomalyDetection) onResolve;
  final bool canAssign;

  @override
  Widget build(BuildContext context) => AppPanel(
    padding: EdgeInsets.zero,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
          child: Text(
            'ANOMALY HISTORY (${anomalies.length})',
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
        ),
        if (anomalies.isEmpty)
          const Padding(
            padding: EdgeInsets.fromLTRB(14, 0, 14, 14),
            child: Text(
              'No abnormal inference windows have been detected for this server.',
            ),
          )
        else
          ...anomalies.indexed.map(
            (entry) => Column(
              children: [
                AnomalyEvidenceTile(
                  anomaly: entry.$2,
                  canAssign: canAssign,
                  resolving: resolvingId == entry.$2.id,
                  onResolve: () => onResolve(entry.$2),
                ),
                if (entry.$1 != anomalies.length - 1) const Divider(height: 1),
              ],
            ),
          ),
      ],
    ),
  );
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => AppPanel(
    child: Row(
      children: [
        Expanded(child: Text(message)),
        TextButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    ),
  );
}

String _compact(double value) => value.abs() >= 1000
    ? value.toStringAsFixed(0)
    : value.toStringAsFixed(value.abs() < 10 ? 2 : 1);
String _unit(String unit) => switch (unit) {
  'percent' => '%',
  'bytes_per_second' => 'B/s',
  'seconds_per_second' => 's/s',
  'timeouts_per_second' => 'timeouts/s',
  _ => unit,
};
