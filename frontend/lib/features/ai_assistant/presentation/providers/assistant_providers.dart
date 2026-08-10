import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/data_sources/assistant_data_source.dart';
import '../../data/repositories/assistant_repository_impl.dart';
import '../../domain/entities/assistant_context.dart';
import '../../domain/repositories/assistant_repository.dart';

final assistantDataSourceProvider = Provider<AssistantDataSource>(
  (ref) => DummyAssistantDataSource(),
);
final assistantRepositoryProvider = Provider<AssistantRepository>(
  (ref) => AssistantRepositoryImpl(ref.watch(assistantDataSourceProvider)),
);
final assistantContextProvider = FutureProvider<AssistantContext>(
  (ref) => ref.watch(assistantRepositoryProvider).getContext(),
);
