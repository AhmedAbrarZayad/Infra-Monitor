import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config/env_config.dart';
import '../../auth/data/auth_repository.dart';
import 'organization_models.dart';

class OrganizationRepository {
  final http.Client _client;
  final String _baseUrl;
  final String _accessToken;

  OrganizationRepository(this._accessToken, {http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? '${EnvConfig.apiBaseUrl}/organizations';

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_accessToken',
      };

  Map<String, dynamic> _decode(http.Response response) {
    if (response.body.isEmpty) return <String, dynamic>{};
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Map<String, dynamic> _accept(http.Response response) {
    final body = _decode(response);
    if (response.statusCode >= 400) throw ApiException(response.statusCode, body);
    return body;
  }

  Future<OrganizationContext> getContext() async {
    final response = await _client.get(Uri.parse('$_baseUrl/context/'), headers: _headers);
    return OrganizationContext.fromJson(_accept(response));
  }

  Future<PaginatedOrganizations> search(String query, {int offset = 0}) async {
    final uri = Uri.parse('$_baseUrl/search/').replace(queryParameters: {
      'q': query,
      'limit': '10',
      'offset': '$offset',
    });
    final response = await _client.get(uri, headers: _headers);
    return PaginatedOrganizations.fromJson(_accept(response));
  }

  Future<OrganizationMembership> create({
    required String name,
    required String summary,
    String? logoUrl,
  }) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/'),
      headers: _headers,
      body: jsonEncode({'name': name, 'summary': summary, 'logo_url': logoUrl}),
    );
    final body = _accept(response);
    return OrganizationMembership.fromJson(body['membership'] as Map<String, dynamic>);
  }

  Future<OrganizationMembership> join(String organizationId) async {
    final response = await _client.post(
      Uri.parse('$_baseUrl/$organizationId/memberships/'),
      headers: _headers,
    );
    return OrganizationMembership.fromJson(_accept(response));
  }

  Future<List<OrganizationMembership>> getMembers(String organizationId) async {
    final response = await _client.get(
      Uri.parse('$_baseUrl/$organizationId/members/?limit=100'),
      headers: _headers,
    );
    final body = _accept(response);
    return (body['results'] as List<dynamic>)
        .map((item) => OrganizationMembership.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
