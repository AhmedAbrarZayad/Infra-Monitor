import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/features/organizations/data/organization_repository.dart';

Map<String, dynamic> membershipJson({bool approved = true, String? role}) => {
  'id': '10000000-0000-0000-0000-000000000001',
  'organization': {
    'id': '20000000-0000-0000-0000-000000000001',
    'name': 'Example Operations',
    'summary': 'Production team',
    'logo_url': null,
  },
  'user': {
    'id': 1,
    'username': 'alex',
    'email': 'alex@example.com',
    'first_name': 'Alex',
    'last_name': 'Perera',
  },
  'role': role ?? (approved ? 'OWNER' : 'ENGINEER'),
  'approved': approved,
  'created_at': '2026-01-01T00:00:00Z',
  'updated_at': '2026-01-01T00:00:00Z',
};

void main() {
  test('loads and parses organization context with authorization', () async {
    final repository = OrganizationRepository(
      'access-token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer access-token');
        expect(request.url.path, '/api/organizations/context/');
        return http.Response(jsonEncode({
          'memberships': [membershipJson()],
          'pending_memberships': [membershipJson(approved: false)],
          'can_create_organization': false,
          'recommended_organization_id': '20000000-0000-0000-0000-000000000001',
        }), 200);
      }),
    );
    final context = await repository.getContext();
    expect(context.memberships.single.role, 'OWNER');
    expect(context.pendingMemberships.single.approved, false);
    expect(context.canCreateOrganization, false);
  });

  test('search sends q and parses paginated public results', () async {
    final repository = OrganizationRepository(
      'token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.url.queryParameters['q'], 'example');
        return http.Response(jsonEncode({
          'count': 1,
          'next': null,
          'previous': null,
          'results': [{
            'id': '20000000-0000-0000-0000-000000000001',
            'name': 'Example Operations',
            'summary': 'Production team',
            'logo_url': null,
          }],
        }), 200);
      }),
    );
    final result = await repository.search('example');
    expect(result.count, 1);
    expect(result.results.single.name, 'Example Operations');
  });

  test('join posts to the selected organization', () async {
    final repository = OrganizationRepository(
      'token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/organizations/org-id/memberships/');
        return http.Response(jsonEncode(membershipJson(approved: false)), 201);
      }),
    );
    final result = await repository.join('org-id');
    expect(result.approved, false);
  });

  test('loads pending memberships for owner review', () async {
    final repository = OrganizationRepository(
      'token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/organizations/org-id/memberships/');
        expect(request.url.queryParameters['approved'], 'false');
        return http.Response(jsonEncode({
          'count': 1,
          'next': null,
          'previous': null,
          'results': [membershipJson(approved: false)],
        }), 200);
      }),
    );
    final result = await repository.getPendingMemberships('org-id');
    expect(result.single.approved, false);
  });

  test('approves a pending membership', () async {
    final repository = OrganizationRepository(
      'token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/api/organizations/org-id/memberships/member-id/approve/',
        );
        return http.Response(jsonEncode(membershipJson(role: 'ADMIN')), 200);
      }),
    );
    final result = await repository.approveMembership(
      organizationId: 'org-id',
      membershipId: 'member-id',
    );
    expect(result.approved, true);
  });

  test('rejects a pending membership', () async {
    final repository = OrganizationRepository(
      'token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(
          request.url.path,
          '/api/organizations/org-id/memberships/member-id/reject/',
        );
        return http.Response('', 204);
      }),
    );
    await repository.rejectMembership(
      organizationId: 'org-id',
      membershipId: 'member-id',
    );
  });

  test('changes an approved member role', () async {
    final repository = OrganizationRepository(
      'token',
      baseUrl: 'http://test/api/organizations',
      client: MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/api/organizations/org-id/members/7/role/');
        expect(jsonDecode(request.body), {'role': 'ADMIN'});
        return http.Response(jsonEncode(membershipJson(role: 'ADMIN')), 200);
      }),
    );
    final result = await repository.changeMemberRole(
      organizationId: 'org-id',
      userId: 7,
      role: 'ADMIN',
    );
    expect(result.role, 'ADMIN');
  });
}
