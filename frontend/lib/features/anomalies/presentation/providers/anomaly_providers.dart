import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../../servers/presentation/providers/servers_providers.dart';
import '../../data/anomalies_api.dart';
import '../../domain/entities/anomaly_detection.dart';

final anomaliesApiProvider = Provider.autoDispose<AnomaliesApi?>((ref) {
  final auth = ref.watch(authProvider);
  final organization = ref.watch(organizationContextProvider);
  if (auth is! AuthAuthenticated || organization is! OrganizationReady) {
    return null;
  }
  return AnomaliesApi(
    auth.accessToken,
    organization.activeMembership.organization.id,
    client: ref.watch(authenticatedHttpClientProvider),
  );
});

final serverAnomaliesProvider = FutureProvider.autoDispose
    .family<List<AnomalyDetection>, String>((ref, serverId) async {
      final api = ref.watch(anomaliesApiProvider);
      if (api == null) throw StateError('No active organization');
      final result = await api.forServer(serverId);
      final interval = await ref.watch(
        monitoringRefreshIntervalProvider.future,
      );
      final timer = Timer(interval, ref.invalidateSelf);
      ref.onDispose(timer.cancel);
      return result;
    });
