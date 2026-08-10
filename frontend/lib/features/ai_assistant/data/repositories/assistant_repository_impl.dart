import '../../domain/entities/assistant_context.dart';
import '../../domain/repositories/assistant_repository.dart';
import '../data_sources/assistant_data_source.dart';

class AssistantRepositoryImpl implements AssistantRepository {
  const AssistantRepositoryImpl(this.source);
  final AssistantDataSource source;
  @override
  Future<AssistantContext> getContext() => source.getContext();
}
