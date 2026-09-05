import 'package:web_socket_channel/web_socket_channel.dart';

import '../../domain/entities/assistant_context.dart';
import '../../domain/repositories/assistant_repository.dart';
import '../data_sources/assistant_data_source.dart';

class AssistantRepositoryImpl implements AssistantRepository {
  const AssistantRepositoryImpl(this.source);
  final AssistantDataSource source;
  @override
  Future<AssistantContext> getContext({String? anomalyId}) =>
      source.getContext(anomalyId: anomalyId);
  @override
  Future<AssistantConversation> openConversation(String anomalyId) =>
      source.openConversation(anomalyId);
  @override
  Future<List<AssistantMessage>> getMessages(String conversationId) =>
      source.getMessages(conversationId);
  @override
  Future<WebSocketChannel> connect(String conversationId) async {
    final ticket = await source.createTicket(conversationId);
    return source.connect(ticket.websocketPath);
  }
}
