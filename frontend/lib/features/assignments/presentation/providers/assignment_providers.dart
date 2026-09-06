import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../data/assignments_api.dart';
import '../../domain/assignment_models.dart';

class WorkAssignmentKey {
  const WorkAssignmentKey(this.resource, this.id);
  final AssignmentResource resource;
  final String id;

  @override
  bool operator ==(Object other) =>
      other is WorkAssignmentKey &&
      other.resource == resource &&
      other.id == id;
  @override
  int get hashCode => Object.hash(resource, id);
}

final assignmentsApiProvider = Provider.autoDispose<AssignmentsApi?>((ref) {
  final auth = ref.watch(authProvider);
  final organization = ref.watch(organizationContextProvider);
  if (auth is! AuthAuthenticated || organization is! OrganizationReady) {
    return null;
  }
  return AssignmentsApi(
    auth.accessToken,
    organization.activeMembership.organization.id,
    client: ref.watch(authenticatedHttpClientProvider),
  );
});

final workAssignmentHistoryProvider = FutureProvider.autoDispose
    .family<List<AssignmentEvent>, WorkAssignmentKey>((ref, key) async {
      final api = ref.watch(assignmentsApiProvider);
      if (api == null) return const [];
      return api.workHistory(key.resource, key.id);
    });

final serviceAdminsProvider = FutureProvider.autoDispose
    .family<ServiceAdminAssignments, String>((ref, serviceId) async {
      final api = ref.watch(assignmentsApiProvider);
      if (api == null) throw StateError('No active organization');
      return api.serviceAdmins(serviceId);
    });

final serviceAdminHistoryProvider = FutureProvider.autoDispose
    .family<List<AssignmentEvent>, String>((ref, serviceId) async {
      final api = ref.watch(assignmentsApiProvider);
      if (api == null) return const [];
      return api.serviceAdminHistory(serviceId);
    });
