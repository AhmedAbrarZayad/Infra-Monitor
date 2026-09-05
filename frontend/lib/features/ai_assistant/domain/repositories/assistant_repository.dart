import 'package:web_socket_channel/web_socket_channel.dart';

import '../entities/assistant_context.dart';

abstract interface class AssistantRepository {
  Future<AssistantContext> getContext({String? anomalyId});
  Future<AssistantConversation> openConversation(String anomalyId);
  Future<List<AssistantMessage>> getMessages(String conversationId);
  Future<WebSocketChannel> connect(String conversationId);
}
