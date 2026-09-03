import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/api/operational_api.dart';

void main() {
  setUpAll(() => dotenv.loadFromString(envString: 'API_BASE_URL=http://example.test/api'));
  test('uses active organization path and bearer token', () async {
    final client = MockClient((request) async {
      expect(request.url.path, contains('/api/organizations/org-1/servers/'));
      expect(request.headers['authorization'], 'Bearer token-1');
      return http.Response(jsonEncode({'count': 0, 'next': null, 'previous': null, 'results': []}), 200, headers: {'content-type': 'application/json'});
    });
    final rows = await OperationalApi('token-1', 'org-1', client: client).getResults('servers/');
    expect(rows, isEmpty);
  });

  test('percentage metrics require compatible units', () {
    expect(metricPercent({'value': 42.5, 'unit': 'percent'}), 42.5);
    expect(metricPercent({'value': 42.5, 'unit': 'bytes'}), 0);
  });
}
