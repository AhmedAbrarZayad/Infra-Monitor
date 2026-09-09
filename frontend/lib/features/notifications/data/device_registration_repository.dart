import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config/env_config.dart';

class DeviceRegistrationRepository {
  DeviceRegistrationRepository(this._client);

  final http.Client _client;

  Future<void> register({
    required String installationId,
    required String token,
  }) async {
    final response = await _client.put(
      Uri.parse('${EnvConfig.apiBaseUrl}/auth/me/devices/$installationId/'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'token': token}),
    );
    if (response.statusCode >= 400) {
      throw StateError('Device registration failed (${response.statusCode}).');
    }
  }
}
