import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../../core/api/operational_api.dart';
import '../../../../core/config/env_config.dart';
import '../../domain/entities/assistant_context.dart';

abstract interface class AssistantDataSource {
  Future<AssistantContext> getContext({String? anomalyId});
  Future<AssistantConversation> openConversation(String anomalyId);
  Future<List<AssistantMessage>> getMessages(String conversationId);
  Future<AssistantSocketTicket> createTicket(String conversationId);
  Future<WebSocketChannel> connect(String websocketPath);
}

class ApiAssistantDataSource implements AssistantDataSource {
  ApiAssistantDataSource(this._api);
  final OperationalApi _api;

  @override
  Future<AssistantContext> getContext({String? anomalyId}) async =>
      AssistantContext.fromJson(
        await _api.getMap(
          'assistant/context/',
          query: anomalyId == null ? null : {'anomaly_id': anomalyId},
        ),
      );

  @override
  Future<AssistantConversation> openConversation(String anomalyId) async =>
      AssistantConversation.fromJson(
        await _api.post('assistant/conversations/', {'anomaly_id': anomalyId}),
      );

  @override
  Future<List<AssistantMessage>> getMessages(String conversationId) async =>
      (await _api.getResults(
            'assistant/conversations/$conversationId/messages/',
            query: {'limit': '100'},
          ))
          .whereType<Map<String, dynamic>>()
          .map(AssistantMessage.fromJson)
          .toList(growable: false);

  @override
  Future<AssistantSocketTicket> createTicket(String conversationId) async =>
      AssistantSocketTicket.fromJson(
        await _api.post('assistant/websocket-tickets/', {
          'conversation_id': conversationId,
        }),
      );

  @override
  Future<WebSocketChannel> connect(String websocketPath) async {
    final uri = assistantWebSocketUri(EnvConfig.apiBaseUrl, websocketPath);
    final channel = WebSocketChannel.connect(uri);
    await channel.ready;
    return channel;
  }
}

Uri assistantWebSocketUri(String apiBaseUrl, String websocketPath) {
  final apiUri = Uri.parse(apiBaseUrl);
  final socketPath = Uri.parse(websocketPath);
  return apiUri.replace(
    scheme: apiUri.scheme == 'https' ? 'wss' : 'ws',
    path: socketPath.path,
    query: socketPath.query,
  );
}
