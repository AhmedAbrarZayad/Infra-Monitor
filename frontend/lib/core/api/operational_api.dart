import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/env_config.dart';
import '../../features/auth/data/auth_repository.dart';

class OperationalApi {
  OperationalApi(this.token, this.organizationId, {http.Client? client})
    : _client = client ?? http.Client();
  final String token, organizationId;
  final http.Client _client;
  Map<String, String> get _headers => {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  };
  Uri _uri(String path, [Map<String, String>? query]) => Uri.parse(
    '${EnvConfig.apiBaseUrl}/organizations/$organizationId/$path',
  ).replace(queryParameters: query);
  dynamic _decode(http.Response r) {
    final body = r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
    if (r.statusCode >= 400)
      throw ApiException(
        r.statusCode,
        body is Map<String, dynamic> ? body : {'detail': body.toString()},
      );
    return body;
  }

  Future<Map<String, dynamic>> getMap(
    String path, {
    Map<String, String>? query,
  }) async =>
      _decode(await _client.get(_uri(path, query), headers: _headers))
          as Map<String, dynamic>;
  Future<Map<String, dynamic>> getApiMap(String path) async =>
      _decode(
            await _client.get(
              Uri.parse('${EnvConfig.apiBaseUrl}/$path'),
              headers: _headers,
            ),
          )
          as Map<String, dynamic>;
  Future<Map<String, dynamic>> patchApi(
    String path,
    Map<String, dynamic> body,
  ) async =>
      _decode(
            await _client.patch(
              Uri.parse('${EnvConfig.apiBaseUrl}/$path'),
              headers: _headers,
              body: jsonEncode(body),
            ),
          )
          as Map<String, dynamic>;
  Future<List<dynamic>> getResults(
    String path, {
    Map<String, String>? query,
  }) async =>
      (await getMap(path, query: query))['results'] as List<dynamic>? ??
      const [];
  Future<Map<String, dynamic>> post(
    String path, [
    Map<String, dynamic>? body,
  ]) async =>
      _decode(
            await _client.post(
              _uri(path),
              headers: _headers,
              body: jsonEncode(body ?? {}),
            ),
          )
          as Map<String, dynamic>;
  Future<Map<String, dynamic>> patch(
    String path,
    Map<String, dynamic> body,
  ) async =>
      _decode(
            await _client.patch(
              _uri(path),
              headers: _headers,
              body: jsonEncode(body),
            ),
          )
          as Map<String, dynamic>;
  Future<Map<String, dynamic>> put(
    String path,
    Map<String, dynamic> body,
  ) async =>
      _decode(
            await _client.put(
              _uri(path),
              headers: _headers,
              body: jsonEncode(body),
            ),
          )
          as Map<String, dynamic>;
}

double? metricPercent(dynamic metric) {
  if (metric is! Map || metric['value'] == null) return null;
  final unit = '${metric['unit']}'.toLowerCase();
  if (!{'percent', '%', 'percentage'}.contains(unit)) return null;
  return (metric['value'] as num).toDouble().clamp(0, 100);
}

String relativeTime(dynamic raw) {
  if (raw == null) return 'never';
  final d = DateTime.tryParse(raw.toString())?.toLocal();
  if (d == null) return raw.toString();
  final diff = DateTime.now().difference(d);
  if (diff.inDays > 0) return '${diff.inDays}d ago';
  if (diff.inHours > 0) return '${diff.inHours}h ago';
  if (diff.inMinutes > 0) return '${diff.inMinutes}m ago';
  return '${diff.inSeconds.clamp(0, 59)}s ago';
}
