import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/anomalies/data/anomalies_api.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  setUpAll(
    () => dotenv.loadFromString(
      envString: 'API_BASE_URL=http://example.test/api',
    ),
  );

  test('requests only the latest server anomalies with bearer auth', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/api/organizations/org-1/anomalies/');
      expect(request.url.queryParameters, {
        'server_id': 'server-1',
        'is_anomaly': 'true',
        'limit': '20',
      });
      expect(request.headers['authorization'], 'Bearer token-1');
      return http.Response(
        jsonEncode({
          'results': [
            {
              'id': 'detection-1',
              'server_id': 'server-1',
              'service_id': 'service-1',
              'is_anomaly': true,
            },
          ],
        }),
        200,
      );
    });

    final results = await AnomaliesApi(
      'token-1',
      'org-1',
      client: client,
    ).forServer('server-1');

    expect(results, hasLength(1));
    expect(results.single.isAnomaly, isTrue);
  });
}
