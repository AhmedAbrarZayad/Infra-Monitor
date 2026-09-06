import '../../../organizations/data/organization_models.dart';

class Incident {
  const Incident({
    this.apiId,
    required this.id,
    required this.severity,
    required this.status,
    required this.title,
    required this.server,
    required this.service,
    required this.environment,
    required this.age,
    required this.owner,
    required this.aiConfidence,
    required this.acknowledgement,
    this.assignedTo,
    this.serviceId,
  });
  final String? apiId;
  final String id,
      severity,
      status,
      title,
      server,
      service,
      environment,
      age,
      owner,
      aiConfidence,
      acknowledgement;
  final MembershipUser? assignedTo;
  final String? serviceId;
}
