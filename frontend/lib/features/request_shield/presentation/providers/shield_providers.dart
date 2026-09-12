import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';

import '../../../../core/api/operational_api.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../../servers/presentation/providers/servers_providers.dart';
import '../../domain/entities/shield_entities.dart';

// ── Helpers ──────────────────────────────────────────────────────

OperationalApi _api(Ref ref) {
  final a = ref.watch(authProvider);
  final o = ref.watch(organizationContextProvider);
  if (a is! AuthAuthenticated || o is! OrganizationReady) {
    throw StateError('No active organization');
  }
  return OperationalApi(
    a.accessToken,
    o.activeMembership.organization.id,
    client: ref.watch(authenticatedHttpClientProvider),
  );
}

OperationalApi _widgetApi(WidgetRef ref) {
  final a = ref.watch(authProvider);
  final o = ref.watch(organizationContextProvider);
  if (a is! AuthAuthenticated || o is! OrganizationReady) {
    throw StateError('No active organization');
  }
  return OperationalApi(
    a.accessToken,
    o.activeMembership.organization.id,
    client: ref.watch(authenticatedHttpClientProvider),
  );
}

// ── Analytics ────────────────────────────────────────────────────

final shieldAnalyticsProvider =
    FutureProvider.autoDispose.family<ShieldAnalytics, String?>(
  (ref, source) async {
    final api = _api(ref);
    final query = <String, String>{'hours': '24'};
    if (source != null) query['source'] = source;
    final json = await api.getMap('request-shield/analytics/', query: query);

    final dist = (json['zone_distribution'] as Map<String, dynamic>? ?? {})
        .map((k, v) => MapEntry(k, (v as num).toInt()));
    final topIps = (json['top_offending_ips'] as List? ?? [])
        .map((e) => OffendingIp.fromJson(e as Map<String, dynamic>))
        .toList();
    final trend = (json['zone_trend'] as List? ?? [])
        .map((e) => ZoneTrendEntry.fromJson(e as Map<String, dynamic>))
        .toList();

    // Auto-refresh every 30s
    final timer = Timer(const Duration(seconds: 30), ref.invalidateSelf);
    ref.onDispose(timer.cancel);

    return ShieldAnalytics(
      zoneDistribution: dist,
      topOffendingIps: topIps,
      zoneTrend: trend,
      totalRequests: json['total_requests'] ?? 0,
      pendingSuggestions: json['pending_suggestions'] ?? 0,
      shieldEnabled: json['shield_enabled'] ?? false,
      hours: json['hours'] ?? 24,
    );
  },
);

// ── Request Logs ─────────────────────────────────────────────────

final shieldRequestLogsProvider =
    FutureProvider.autoDispose.family<List<RequestLogEntry>, Map<String, String>>(
  (ref, filters) async {
    final api = _api(ref);
    final results =
        await api.getResults('request-shield/requests/', query: filters);
    return results
        .map((e) => RequestLogEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  },
);

// ── Threat Suggestions ───────────────────────────────────────────

final shieldSuggestionsProvider =
    FutureProvider.autoDispose<List<ThreatSuggestion>>(
  (ref) async {
    final api = _api(ref);
    final results = await api.getResults('request-shield/suggestions/',
        query: {'status': 'PENDING'});
    return results
        .map((e) => ThreatSuggestion.fromJson(e as Map<String, dynamic>))
        .toList();
  },
);

// ── Shield Config ────────────────────────────────────────────────

final shieldConfigProvider = FutureProvider.autoDispose<ShieldConfig>(
  (ref) async {
    final api = _api(ref);
    final json = await api.getMap('request-shield/config/');
    return ShieldConfig.fromJson(json);
  },
);

// ── Actions ──────────────────────────────────────────────────────

Future<void> resolveSuggestion(
  WidgetRef ref, {
  required String suggestionId,
  required String action,
  String notes = '',
}) async {
  final api = _widgetApi(ref);
  await api.post('request-shield/suggestions/$suggestionId/action/', {
    'action': action,
    'notes': notes,
  });
  ref.invalidate(shieldSuggestionsProvider);
  ref.invalidate(shieldAnalyticsProvider);
}

Future<void> setRequestVerdict(
  WidgetRef ref, {
  required String logId,
  required String verdict,
}) async {
  final api = _widgetApi(ref);
  await api.post('request-shield/requests/$logId/verdict/', {
    'verdict': verdict,
  });
  ref.invalidate(shieldRequestLogsProvider);
}

Future<void> updateShieldConfig(
  WidgetRef ref,
  Map<String, dynamic> updates,
) async {
  final api = _widgetApi(ref);
  await api.patch('request-shield/config/', updates);
  ref.invalidate(shieldConfigProvider);
  ref.invalidate(shieldAnalyticsProvider);
}

// ── Tab selection state ──────────────────────────────────────────

final shieldTabProvider = StateProvider<int>((ref) => 0);
final shieldSourceFilterProvider = StateProvider<String?>((ref) => null);
