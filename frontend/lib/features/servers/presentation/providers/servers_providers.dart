import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/api/operational_api.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../data/monitoring_api.dart';
import '../../domain/entities/server.dart';

final monitoringApiProvider = Provider.autoDispose<MonitoringApi?>((ref) {
  final auth = ref.watch(authProvider);
  final organization = ref.watch(organizationContextProvider);
  if (auth is! AuthAuthenticated || organization is! OrganizationReady)
    return null;
  return MonitoringApi(
    auth.accessToken,
    organization.activeMembership.organization.id,
  );
});

final monitoringRefreshIntervalProvider = FutureProvider.autoDispose<Duration>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  final organization = ref.watch(organizationContextProvider);
  if (auth is! AuthAuthenticated || organization is! OrganizationReady)
    return const Duration(seconds: 10);
  final data = await OperationalApi(
    auth.accessToken,
    organization.activeMembership.organization.id,
  ).getApiMap('auth/me/preferences/');
  final seconds = ((data['refresh_interval_seconds'] as num?)?.toInt() ?? 10)
      .clamp(5, 3600);
  return Duration(seconds: seconds);
});

Future<void> _poll(Ref ref) async {
  final interval = await ref.watch(monitoringRefreshIntervalProvider.future);
  final timer = Timer(interval, ref.invalidateSelf);
  ref.onDispose(timer.cancel);
}

final serversProvider = FutureProvider.autoDispose<List<ServerSummary>>((
  ref,
) async {
  final api = ref.watch(monitoringApiProvider);
  if (api == null) return const [];
  final result = await api.servers();
  await _poll(ref);
  return result;
});

final serverProvider = FutureProvider.autoDispose.family<ServerSummary, String>(
  (ref, id) async {
    final api = ref.watch(monitoringApiProvider);
    if (api == null) throw StateError('No active organization');
    return api.server(id);
  },
);

final serverHealthProvider = FutureProvider.autoDispose
    .family<ServerHealth, String>((ref, id) async {
      final api = ref.watch(monitoringApiProvider);
      if (api == null) throw StateError('No active organization');
      final result = await api.serverHealth(id);
      await _poll(ref);
      return result;
    });

final serverServicesProvider = FutureProvider.autoDispose
    .family<List<MonitoredService>, String>((ref, id) async {
      final api = ref.watch(monitoringApiProvider);
      if (api == null) throw StateError('No active organization');
      final services = await api.services(id);
      final result = await Future.wait(
        services.map((service) async {
          try {
            return await api.serviceHealth(service.id);
          } catch (_) {
            return service;
          }
        }),
      );
      await _poll(ref);
      return result;
    });

class MetricRequest {
  const MetricRequest({
    required this.serverId,
    required this.metric,
    required this.range,
  });
  final String serverId;
  final String metric;
  final Duration range;
  @override
  bool operator ==(Object other) =>
      other is MetricRequest &&
      other.serverId == serverId &&
      other.metric == metric &&
      other.range == range;
  @override
  int get hashCode => Object.hash(serverId, metric, range);
}

int metricStep(Duration range) {
  if (range <= const Duration(hours: 1)) return 15;
  if (range <= const Duration(days: 1)) return 60;
  if (range <= const Duration(days: 7)) return 300;
  return 1800;
}

final serverMetricProvider = FutureProvider.autoDispose
    .family<MetricSeries, MetricRequest>((ref, request) async {
      final api = ref.watch(monitoringApiProvider);
      if (api == null) throw StateError('No active organization');
      final to = DateTime.now().toUtc();
      final result = await api.serverMetrics(
        request.serverId,
        metric: request.metric,
        from: to.subtract(request.range),
        to: to,
        step: metricStep(request.range),
      );
      await _poll(ref);
      return result;
    });
