import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/features/assignments/data/assignments_api.dart';
import 'package:frontend/features/assignments/domain/assignment_models.dart';

void main() {
  setUpAll(
    () => dotenv.loadFromString(
      envString: 'API_BASE_URL=http://example.test/api',
    ),
  );

  test('work assignment uses PATCH with optimistic precondition', () async {
    final api = AssignmentsApi(
      'token',
      'org-1',
      client: MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(
          request.url.path,
          '/api/organizations/org-1/incidents/incident-1/assignment/',
        );
        expect(jsonDecode(request.body), {
          'user_id': 12,
          'expected_user_id': null,
        });
        return http.Response(
          jsonEncode({
            'assigned_to': {
              'id': 12,
              'username': 'engineer',
              'email': 'engineer@example.com',
              'first_name': 'Eng',
              'last_name': 'One',
            },
          }),
          200,
        );
      }),
    );

    final result = await api.assignWork(
      resource: AssignmentResource.incident,
      id: 'incident-1',
      userId: 12,
      expectedUserId: null,
    );
    expect(result['assigned_to']['id'], 12);
  });

  test(
    'parses common history response and service Admin replacement',
    () async {
      var requestCount = 0;
      final api = AssignmentsApi(
        'token',
        'org-1',
        client: MockClient((request) async {
          requestCount++;
          if (request.method == 'PUT') {
            expect(jsonDecode(request.body), {
              'membership_ids': ['membership-1'],
            });
            return http.Response(
              jsonEncode({'service_id': 'service-1', 'admins': []}),
              200,
            );
          }
          return http.Response(
            jsonEncode({
              'count': 1,
              'next': null,
              'previous': null,
              'results': [
                {
                  'id': 'event-1',
                  'resource_type': 'ANOMALY',
                  'action': 'ASSIGNED',
                  'actor': null,
                  'previous_subject': null,
                  'new_subject': {
                    'id': 12,
                    'username': 'engineer',
                    'email': 'engineer@example.com',
                    'first_name': 'Eng',
                    'last_name': 'One',
                  },
                  'created_at': '2026-09-06T10:00:00Z',
                },
              ],
            }),
            200,
          );
        }),
      );

      final history = await api.workHistory(
        AssignmentResource.anomaly,
        'anomaly-1',
      );
      expect(history.single.newSubject?.displayName, 'Eng One');
      expect(history.single.action, 'ASSIGNED');
      final service = await api.replaceServiceAdmins('service-1', [
        'membership-1',
      ]);
      expect(service.serviceId, 'service-1');
      expect(requestCount, 2);
    },
  );
}
