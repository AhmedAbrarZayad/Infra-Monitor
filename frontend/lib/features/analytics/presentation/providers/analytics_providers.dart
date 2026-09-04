import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/api/operational_api.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../domain/entities/analytics_dashboard.dart';
import '../../../servers/presentation/providers/servers_providers.dart';

String duration(dynamic seconds) =>
    seconds == null ? 'Unavailable' : '${((seconds as num) / 60).round()}m';
final analyticsProvider = FutureProvider.autoDispose<AnalyticsDashboard>((
  ref,
) async {
  final a = ref.watch(authProvider);
  final o = ref.watch(organizationContextProvider);
  if (a is! AuthAuthenticated || o is! OrganizationReady)
    throw StateError('No active organization');
  final x = await OperationalApi(
    a.accessToken,
    o.activeMembership.organization.id,
  ).getMap('analytics/');
  final m = x['metrics'] as Map<String, dynamic>? ?? {};
  final series = x['series'] as Map<String, dynamic>? ?? {};
  List<double> s(String k) => (series[k] as List? ?? [])
      .whereType<num>()
      .map((v) => v.toDouble())
      .toList();
  final interval = await ref.watch(monitoringRefreshIntervalProvider.future);
  final timer = Timer(interval, ref.invalidateSelf);
  ref.onDispose(timer.cancel);
  return AnalyticsDashboard(
    metrics: [
      AnalyticsMetric(
        'MEAN TIME TO ACKNOWLEDGE',
        duration(m['mtta_seconds']),
        '',
      ),
      AnalyticsMetric('MEAN TIME TO RESOLVE', duration(m['mttr_seconds']), ''),
      AnalyticsMetric('OPEN INCIDENTS', '${m['open'] ?? 0}', ''),
      AnalyticsMetric('RESOLVED (7D)', '${m['resolved_7d'] ?? 0}', ''),
    ],
    cpu: s('cpu'),
    memory: s('memory'),
    latency: s('latency'),
    frequency: s('frequency'),
    opened: s('opened'),
    resolved: s('resolved'),
    uptime: s('uptime'),
    categories: Map<String, int>.from(x['categories'] ?? {}),
    servers: Map<String, int>.from(x['servers'] ?? {}),
    insights: List<String>.from(x['insights'] ?? []),
  );
});
