import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/servers/data/monitoring_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  setUpAll(
    () => dotenv.loadFromString(
      envString: 'API_BASE_URL=http://example.test/api',
    ),
  );

  test('uses bearer auth and tenant-scoped monitoring paths', () async {
    final paths = <String>[];
    final client = MockClient((request) async {
      paths.add(request.url.path);
      expect(request.headers['authorization'], 'Bearer token-1');
      if (request.url.path.endsWith('/servers/'))
        return http.Response(jsonEncode({'results': []}), 200);
      if (request.url.path.endsWith('/services/'))
        return http.Response(jsonEncode({'results': []}), 200);
      if (request.url.path.endsWith('/health/')) {
        return http.Response(
          jsonEncode(
            request.url.path.contains('/services/')
                ? {'id': 'service-1'}
                : {'server_id': 'server-1', 'metrics': {}},
          ),
          200,
        );
      }
      if (request.url.path.endsWith('/metrics/'))
        return http.Response(
          jsonEncode({'metric': 'cpu_r', 'available': true, 'points': []}),
          200,
        );
      return http.Response(jsonEncode({'id': 'server-1', 'metrics': {}}), 200);
    });
    final api = MonitoringApi('token-1', 'org-1', client: client);
    await api.servers();
    await api.server('server-1');
    await api.serverHealth('server-1');
    await api.services('server-1');
    await api.serviceHealth('service-1');
    final to = DateTime.utc(2026, 9, 4, 1);
    await api.serverMetrics(
      'server-1',
      metric: 'cpu_r',
      from: to.subtract(const Duration(hours: 1)),
      to: to,
      step: 15,
    );
    await api.serviceMetrics(
      'service-1',
      metric: 'mem_u',
      from: to.subtract(const Duration(hours: 1)),
      to: to,
      step: 15,
    );
    expect(
      paths,
      containsAll([
        '/api/organizations/org-1/servers/',
        '/api/organizations/org-1/servers/server-1/',
        '/api/organizations/org-1/servers/server-1/health/',
        '/api/organizations/org-1/servers/server-1/services/',
        '/api/organizations/org-1/services/service-1/health/',
        '/api/organizations/org-1/servers/server-1/metrics/',
        '/api/organizations/org-1/services/service-1/metrics/',
      ]),
    );
  });

  test('range uses UTC ISO timestamps and validated step', () async {
    final client = MockClient((request) async {
      expect(request.url.queryParameters['metric'], 'disk_r');
      expect(request.url.queryParameters['from'], '2026-09-04T00:00:00.000Z');
      expect(request.url.queryParameters['to'], '2026-09-04T01:00:00.000Z');
      expect(request.url.queryParameters['step'], '15');
      return http.Response(
        jsonEncode({'metric': 'disk_r', 'available': true, 'points': []}),
        200,
      );
    });
    await MonitoringApi('token', 'org', client: client).serverMetrics(
      'server',
      metric: 'disk_r',
      from: DateTime.utc(2026, 9, 4),
      to: DateTime.utc(2026, 9, 4, 1),
      step: 15,
    );
  });

  test('creates an organization-scoped server enrollment', () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/api/organizations/org-1/monitoring/enrollments/',
      );
      expect(request.headers['authorization'], 'Bearer token-1');
      expect(jsonDecode(request.body), {
        'server_name': 'Multipass Lab',
        'environment': 'development',
      });
      return http.Response(
        jsonEncode({
          'enrollment_id': 'enrollment-1',
          'server_name': 'Multipass Lab',
          'environment': 'development',
          'expires_at': '2026-09-04T01:15:00Z',
          'install_command': 'curl example | sudo sh',
        }),
        201,
      );
    });

    final enrollment = await MonitoringApi(
      'token-1',
      'org-1',
      client: client,
    ).createEnrollment(serverName: 'Multipass Lab', environment: 'development');

    expect(enrollment.id, 'enrollment-1');
    expect(enrollment.installCommand, 'curl example | sudo sh');
  });
}
