import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:uuid/uuid.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../../core/api/operational_api.dart';
import '../../../anomalies/domain/entities/anomaly_detection.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../navigation/presentation/providers/app_navigation_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../data/data_sources/assistant_data_source.dart';
import '../../data/repositories/assistant_repository_impl.dart';
import '../../domain/entities/assistant_context.dart';
import '../../domain/repositories/assistant_repository.dart';

class AssistantState {
  const AssistantState({
    this.loading = true,
    this.context,
    this.selectedAnomaly,
    this.conversation,
    this.messages = const [],
    this.streamingText = '',
    this.connected = false,
    this.generating = false,
    this.error,
    this.lastFailedText,
  });

  final bool loading, connected, generating;
  final AssistantContext? context;
  final AnomalyDetection? selectedAnomaly;
  final AssistantConversation? conversation;
  final List<AssistantMessage> messages;
  final String streamingText;
  final String? error, lastFailedText;

  AssistantState copyWith({
    bool? loading,
    AssistantContext? context,
    AnomalyDetection? selectedAnomaly,
    AssistantConversation? conversation,
    List<AssistantMessage>? messages,
    String? streamingText,
    bool? connected,
    bool? generating,
    String? error,
    String? lastFailedText,
    bool clearError = false,
    bool clearFailedText = false,
  }) => AssistantState(
    loading: loading ?? this.loading,
    context: context ?? this.context,
    selectedAnomaly: selectedAnomaly ?? this.selectedAnomaly,
    conversation: conversation ?? this.conversation,
    messages: messages ?? this.messages,
    streamingText: streamingText ?? this.streamingText,
    connected: connected ?? this.connected,
    generating: generating ?? this.generating,
    error: clearError ? null : error ?? this.error,
    lastFailedText: clearFailedText
        ? null
        : lastFailedText ?? this.lastFailedText,
  );
}

class AssistantController extends StateNotifier<AssistantState> {
  AssistantController(this._repository, this._initialAnomalyId)
    : super(const AssistantState()) {
    Future.microtask(load);
  }

  final AssistantRepository _repository;
  final String? _initialAnomalyId;
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      AssistantContext context;
      try {
        context = await _repository.getContext(anomalyId: _initialAnomalyId);
      } catch (_) {
        if (_initialAnomalyId == null) rethrow;
        context = await _repository.getContext();
      }
      state = state.copyWith(
        context: context,
        selectedAnomaly: context.selectedAnomaly,
        loading: false,
      );
      if (context.selectedAnomaly != null) {
        await _open(context.selectedAnomaly!);
      }
    } catch (_) {
      state = state.copyWith(
        loading: false,
        error: 'Unable to load anomaly assistant.',
      );
    }
  }

  Future<void> selectAnomaly(AnomalyDetection anomaly) async {
    if (state.selectedAnomaly?.id == anomaly.id) return;
    state = state.copyWith(
      selectedAnomaly: anomaly,
      loading: true,
      messages: const [],
      streamingText: '',
      clearError: true,
    );
    await _open(anomaly);
  }

  Future<void> _open(AnomalyDetection anomaly) async {
    await _closeSocket();
    try {
      final conversation = await _repository.openConversation(anomaly.id);
      final messages = await _repository.getMessages(conversation.id);
      state = state.copyWith(
        conversation: conversation,
        messages: messages,
        loading: false,
        connected: false,
      );
      await _connect();
    } catch (_) {
      state = state.copyWith(
        loading: false,
        connected: false,
        error: 'Unable to open this anomaly conversation.',
      );
    }
  }

  Future<void> reconnect() async {
    final conversation = state.conversation;
    if (conversation == null) return;
    state = state.copyWith(loading: true, clearError: true);
    await _closeSocket();
    try {
      final messages = await _repository.getMessages(conversation.id);
      state = state.copyWith(
        messages: messages,
        streamingText: '',
        generating: false,
      );
      await _connect();
      state = state.copyWith(loading: false);
    } catch (_) {
      state = state.copyWith(
        loading: false,
        connected: false,
        error: 'Could not reconnect to the assistant.',
      );
    }
  }

  Future<void> _connect() async {
    final conversation = state.conversation;
    if (conversation == null) return;
    final channel = await _repository.connect(conversation.id);
    _channel = channel;
    _subscription = channel.stream.listen(
      (event) => _handleEvent(event),
      onError: (_) {
        if (identical(_channel, channel)) {
          state = state.copyWith(
            connected: false,
            generating: false,
            error: 'Assistant connection lost.',
          );
        }
      },
      onDone: () {
        if (identical(_channel, channel)) {
          state = state.copyWith(connected: false, generating: false);
        }
      },
    );
    state = state.copyWith(connected: true, clearError: true);
  }

  void _handleEvent(dynamic raw) {
    try {
      final event = jsonDecode(raw.toString()) as Map<String, dynamic>;
      switch (event['type']) {
        case 'message_ack':
          _append(
            AssistantMessage.fromJson(event['message'] as Map<String, dynamic>),
          );
          break;
        case 'generation_started':
          state = state.copyWith(
            generating: true,
            streamingText: '',
            clearError: true,
          );
          break;
        case 'token_delta':
          state = state.copyWith(
            streamingText: '${state.streamingText}${event['delta'] ?? ''}',
          );
          break;
        case 'generation_completed':
          final message = AssistantMessage.fromJson(
            event['message'] as Map<String, dynamic>,
          );
          _append(message);
          state = state.copyWith(
            generating: false,
            streamingText: '',
            clearFailedText: true,
          );
          break;
        case 'generation_error':
          state = state.copyWith(
            generating: false,
            streamingText: '',
            error: event['message']?.toString() ?? 'AI generation failed.',
          );
          break;
      }
    } catch (_) {
      state = state.copyWith(
        error: 'The assistant returned an unreadable event.',
      );
    }
  }

  void _append(AssistantMessage message) {
    if (state.messages.any((item) => item.id == message.id)) return;
    state = state.copyWith(messages: [...state.messages, message]);
  }

  Future<void> send(String text) async {
    final value = text.trim();
    if (value.isEmpty || value.length > 2000 || state.generating) return;
    if (state.context?.geminiConfigured != true) {
      state = state.copyWith(error: 'Gemini is not configured on the server.');
      return;
    }
    state = state.copyWith(lastFailedText: value, clearError: true);
    if (!state.connected) await reconnect();
    if (!state.connected || _channel == null) return;
    _channel!.sink.add(
      jsonEncode({
        'type': 'user_message',
        'client_message_id': const Uuid().v4(),
        'text': value,
      }),
    );
  }

  Future<void> retry() async {
    final text = state.lastFailedText;
    if (text != null) await send(text);
  }

  Future<void> _closeSocket() async {
    await _subscription?.cancel();
    _subscription = null;
    await _channel?.sink.close();
    _channel = null;
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _channel?.sink.close();
    super.dispose();
  }
}

final assistantRepositoryProvider = Provider<AssistantRepository>((ref) {
  final auth = ref.watch(authProvider);
  final organization = ref.watch(organizationContextProvider);
  if (auth is! AuthAuthenticated || organization is! OrganizationReady) {
    throw StateError('No active organization');
  }
  return AssistantRepositoryImpl(
    ApiAssistantDataSource(
      OperationalApi(
        auth.accessToken,
        organization.activeMembership.organization.id,
      ),
    ),
  );
});

final assistantControllerProvider =
    StateNotifierProvider.autoDispose<AssistantController, AssistantState>((
      ref,
    ) {
      final selected = ref.watch(appNavigationProvider).assistantAnomalyId;
      return AssistantController(
        ref.watch(assistantRepositoryProvider),
        selected,
      );
    });
