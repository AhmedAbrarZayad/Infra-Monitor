class Organization {
  final String id;
  final String name;
  final String summary;
  final String? logoUrl;

  const Organization({required this.id, required this.name, required this.summary, this.logoUrl});

  factory Organization.fromJson(Map<String, dynamic> json) => Organization(
        id: json['id'] as String,
        name: json['name'] as String,
        summary: json['summary'] as String,
        logoUrl: json['logo_url'] as String?,
      );
}

class MembershipUser {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;

  const MembershipUser({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
  });

  factory MembershipUser.fromJson(Map<String, dynamic> json) => MembershipUser(
        id: json['id'] as int,
        username: json['username'] as String,
        email: json['email'] as String,
        firstName: json['first_name'] as String? ?? '',
        lastName: json['last_name'] as String? ?? '',
      );

  String get displayName {
    final name = '$firstName $lastName'.trim();
    return name.isEmpty ? username : name;
  }
}

class OrganizationMembership {
  final String id;
  final Organization organization;
  final MembershipUser user;
  final String role;
  final bool approved;
  final DateTime createdAt;
  final DateTime updatedAt;

  const OrganizationMembership({
    required this.id,
    required this.organization,
    required this.user,
    required this.role,
    required this.approved,
    required this.createdAt,
    required this.updatedAt,
  });

  factory OrganizationMembership.fromJson(Map<String, dynamic> json) => OrganizationMembership(
        id: json['id'] as String,
        organization: Organization.fromJson(json['organization'] as Map<String, dynamic>),
        user: MembershipUser.fromJson(json['user'] as Map<String, dynamic>),
        role: json['role'] as String,
        approved: json['approved'] as bool,
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );

  String get displayRole => switch (role) {
        'OWNER' => 'Super admin',
        'ADMIN' => 'Admin',
        'ENGINEER' => 'Engineer',
        final value => value,
      };
}

class OrganizationContext {
  final List<OrganizationMembership> memberships;
  final List<OrganizationMembership> pendingMemberships;
  final bool canCreateOrganization;
  final String? recommendedOrganizationId;

  const OrganizationContext({
    required this.memberships,
    required this.pendingMemberships,
    required this.canCreateOrganization,
    required this.recommendedOrganizationId,
  });

  factory OrganizationContext.fromJson(Map<String, dynamic> json) => OrganizationContext(
        memberships: (json['memberships'] as List<dynamic>)
            .map((item) => OrganizationMembership.fromJson(item as Map<String, dynamic>))
            .toList(),
        pendingMemberships: (json['pending_memberships'] as List<dynamic>)
            .map((item) => OrganizationMembership.fromJson(item as Map<String, dynamic>))
            .toList(),
        canCreateOrganization: json['can_create_organization'] as bool,
        recommendedOrganizationId: json['recommended_organization_id'] as String?,
      );
}

class PaginatedOrganizations {
  final int count;
  final String? next;
  final List<Organization> results;

  const PaginatedOrganizations({required this.count, required this.next, required this.results});

  factory PaginatedOrganizations.fromJson(Map<String, dynamic> json) => PaginatedOrganizations(
        count: json['count'] as int,
        next: json['next'] as String?,
        results: (json['results'] as List<dynamic>)
            .map((item) => Organization.fromJson(item as Map<String, dynamic>))
            .toList(),
      );
}
