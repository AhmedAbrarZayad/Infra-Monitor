import '../../organizations/data/organization_models.dart';

enum AssignmentResource { incident, anomaly }

class AssignmentEvent {
  const AssignmentEvent({
    required this.id,
    required this.resourceType,
    required this.action,
    required this.actor,
    required this.previousSubject,
    required this.newSubject,
    required this.createdAt,
  });

  final String id;
  final String resourceType;
  final String action;
  final MembershipUser? actor;
  final MembershipUser? previousSubject;
  final MembershipUser? newSubject;
  final DateTime? createdAt;

  factory AssignmentEvent.fromJson(Map<String, dynamic> json) =>
      AssignmentEvent(
        id: json['id']?.toString() ?? '',
        resourceType: json['resource_type']?.toString() ?? '',
        action: json['action']?.toString() ?? '',
        actor: _user(json['actor']),
        previousSubject: _user(json['previous_subject']),
        newSubject: _user(json['new_subject']),
        createdAt: DateTime.tryParse(
          json['created_at']?.toString() ?? '',
        )?.toLocal(),
      );
}

MembershipUser? assignmentUser(dynamic value) => _user(value);

MembershipUser? _user(dynamic value) => value is Map<String, dynamic>
    ? MembershipUser.fromJson(value)
    : value is Map
    ? MembershipUser.fromJson(value.cast<String, dynamic>())
    : null;

class ServiceAdminAssignments {
  const ServiceAdminAssignments({
    required this.serviceId,
    required this.admins,
  });

  final String serviceId;
  final List<OrganizationMembership> admins;

  factory ServiceAdminAssignments.fromJson(Map<String, dynamic> json) =>
      ServiceAdminAssignments(
        serviceId: json['service_id']?.toString() ?? '',
        admins: (json['admins'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(OrganizationMembership.fromJson)
            .toList(growable: false),
      );
}
