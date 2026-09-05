import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/api/authenticated_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('refreshes once and retries a 401 with the new token', () async {
    var token = 'expired';
    var requests = 0;
    var refreshes = 0;
    var cleared = false;
    final client = AuthenticatedClient(
      accessToken: () => token,
      refreshSession: () async {
        refreshes++;
        token = 'fresh';
        return true;
      },
      clearSession: () async => cleared = true,
      inner: MockClient((request) async {
        requests++;
        return request.headers['Authorization'] == 'Bearer fresh'
            ? http.Response(jsonEncode({'ok': true}), 200)
            : http.Response(jsonEncode({'detail': 'expired'}), 401);
      }),
    );

    final response = await client.get(Uri.parse('http://test/protected'));

    expect(response.statusCode, 200);
    expect(requests, 2);
    expect(refreshes, 1);
    expect(cleared, false);
  });

  test('concurrent 401 responses share one token refresh', () async {
    var token = 'expired';
    var refreshes = 0;
    final client = AuthenticatedClient(
      accessToken: () => token,
      refreshSession: () async {
        refreshes++;
        await Future<void>.delayed(const Duration(milliseconds: 10));
        token = 'fresh';
        return true;
      },
      clearSession: () async {},
      inner: MockClient(
        (request) async => http.Response(
          '{}',
          request.headers['Authorization'] == 'Bearer fresh' ? 200 : 401,
        ),
      ),
    );

    final responses = await Future.wait([
      client.get(Uri.parse('http://test/one')),
      client.get(Uri.parse('http://test/two')),
    ]);

    expect(responses.map((response) => response.statusCode), everyElement(200));
    expect(refreshes, 1);
  });

  test('clears the session when refresh is rejected', () async {
    var cleared = false;
    final client = AuthenticatedClient(
      accessToken: () => 'expired',
      refreshSession: () async => false,
      clearSession: () async => cleared = true,
      inner: MockClient((_) async => http.Response('{}', 401)),
    );

    final response = await client.get(Uri.parse('http://test/protected'));

    expect(response.statusCode, 401);
    expect(cleared, true);
  });
}
