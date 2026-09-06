import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/api/operational_api.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../domain/entities/incident.dart';
import '../../../assignments/domain/assignment_models.dart';

OperationalApi? incidentApi(Ref ref) {
  final a = ref.watch(authProvider);
  final o = ref.watch(organizationContextProvider);
  return a is AuthAuthenticated && o is OrganizationReady
      ? OperationalApi(
          a.accessToken,
          o.activeMembership.organization.id,
          client: ref.watch(authenticatedHttpClientProvider),
        )
      : null;
}

final incidentsProvider = FutureProvider<List<Incident>>((ref) async {
  final api = incidentApi(ref);
  if (api == null) return const [];
  final rows = await api.getResults('incidents/', query: {'limit': '100'});
  return rows.map((r) {
    final x = r as Map<String, dynamic>;
    final assignedTo = assignmentUser(x['assigned_to']);
    return Incident(
      apiId: x['id'].toString(),
      id: x['code'] ?? x['id'].toString(),
      severity: x['severity'] ?? '',
      status: x['status'] ?? '',
      title: x['title'] ?? '',
      server: x['server'] ?? '',
      service: x['service'] ?? '',
      serviceId: x['service_id']?.toString(),
      environment: x['environment'] ?? '',
      age: relativeTime(x['detected_at']),
      owner: assignedTo?.displayName ?? 'unassigned',
      assignedTo: assignedTo,
      aiConfidence: x['ai_confidence'] == null
          ? 'Not analyzed'
          : '${((x['ai_confidence'] as num) * 100).round()}%',
      acknowledgement: x['acknowledged_at'] == null
          ? 'not acknowledged'
          : 'acknowledged ${relativeTime(x['acknowledged_at'])}',
    );
  }).toList();
});
final incidentActionsProvider = Provider((ref) => IncidentActions(ref));

class IncidentActions {
  IncidentActions(this.ref);
  final Ref ref;
  Future<void> acknowledgeCritical(List<String> ids) async {
    final api = incidentApi(ref);
    if (api == null) return;
    await api.post('incidents/bulk-acknowledge/', {'incident_ids': ids});
    ref.invalidate(incidentsProvider);
  }
}
