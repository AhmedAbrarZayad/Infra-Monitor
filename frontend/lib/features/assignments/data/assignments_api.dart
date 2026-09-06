import 'package:http/http.dart' as http;

import '../../../core/api/operational_api.dart';
import '../domain/assignment_models.dart';

class AssignmentsApi {
  AssignmentsApi(String token, String organizationId, {http.Client? client})
    : _api = OperationalApi(token, organizationId, client: client);

  final OperationalApi _api;

  Future<List<AssignmentEvent>> workHistory(
    AssignmentResource resource,
    String id,
  ) async => _history(
    '${resource.name == 'incident' ? 'incidents' : 'anomalies'}/$id/assignment-history/',
  );

  Future<Map<String, dynamic>> assignWork({
    required AssignmentResource resource,
    required String id,
    required int? userId,
    required int? expectedUserId,
  }) => _api.patch(
    '${resource.name == 'incident' ? 'incidents' : 'anomalies'}/$id/assignment/',
    {'user_id': userId, 'expected_user_id': expectedUserId},
  );

  Future<ServiceAdminAssignments> serviceAdmins(String serviceId) async =>
      ServiceAdminAssignments.fromJson(
        await _api.getMap('services/$serviceId/admins/'),
      );

  Future<ServiceAdminAssignments> replaceServiceAdmins(
    String serviceId,
    Iterable<String> membershipIds,
  ) async => ServiceAdminAssignments.fromJson(
    await _api.put('services/$serviceId/admins/', {
      'membership_ids': membershipIds.toList(growable: false),
    }),
  );

  Future<List<AssignmentEvent>> serviceAdminHistory(String serviceId) =>
      _history('services/$serviceId/admins/history/');

  Future<List<AssignmentEvent>> _history(String path) async =>
      (await _api.getResults(path, query: {'limit': '100'}))
          .whereType<Map<String, dynamic>>()
          .map(AssignmentEvent.fromJson)
          .toList(growable: false);
}
