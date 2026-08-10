class Incident {
  const Incident({
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
  });
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
}
