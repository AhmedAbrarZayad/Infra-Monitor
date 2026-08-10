class AssistantContext {
  const AssistantContext({
    required this.incidentIds,
    required this.selectedId,
    required this.title,
    required this.evidence,
    required this.prompts,
  });
  final List<String> incidentIds, evidence, prompts;
  final String selectedId, title;
}
