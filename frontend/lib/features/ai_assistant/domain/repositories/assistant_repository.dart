import '../entities/assistant_context.dart';

abstract interface class AssistantRepository {
  Future<AssistantContext> getContext();
}
