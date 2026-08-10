import '../../domain/entities/assistant_context.dart';

abstract interface class AssistantDataSource {
  Future<AssistantContext> getContext();
}

class DummyAssistantDataSource implements AssistantDataSource {
  @override
  Future<AssistantContext> getContext() async => const AssistantContext(
    incidentIds: ['No context', 'INC-2481', 'INC-2480', 'INC-2479', 'INC-2478'],
    selectedId: 'INC-2481',
    title: 'Database connection timeout on Payment Service',
    evidence: [
      'cpu.utilization · payment-service-prod · 12:34–12:48',
      '42 log lines · payment-api · level=ERROR',
      'deploy event · release 4.18.2 · 12:38:10',
    ],
    prompts: [
      'Summarize this incident',
      'What are the possible root causes?',
      'Which logs are most relevant?',
      'What should I check first?',
      'Are there similar historical incidents?',
      'What evidence supports this conclusion?',
    ],
  );
}
