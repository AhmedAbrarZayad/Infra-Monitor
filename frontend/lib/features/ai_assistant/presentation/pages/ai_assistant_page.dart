import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../../anomalies/domain/entities/anomaly_detection.dart';
import '../../domain/entities/assistant_context.dart';
import '../providers/assistant_providers.dart';

const _purple = Color(0xFFC697F5);
const _muted = Color(0xFF929CAD);
const _warning = Color(0xFFFFB51F);

class AiAssistantPage extends ConsumerStatefulWidget {
  const AiAssistantPage({super.key});

  @override
  ConsumerState<AiAssistantPage> createState() => _AiAssistantPageState();
}

class _AiAssistantPageState extends ConsumerState<AiAssistantPage> {
  final controller = TextEditingController();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(assistantControllerProvider);
    final notifier = ref.read(assistantControllerProvider.notifier);
    if (state.loading && state.context == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.context == null) return _LoadFailure(onRetry: notifier.load);
    if (state.context!.anomalies.isEmpty) return const _EmptyAssistant();

    final anomaly = state.selectedAnomaly ?? state.context!.anomalies.first;
    return ListView(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 28),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1000),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'AI advice — crash not confirmed',
                  style: TextStyle(
                    color: _warning,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Gemini explains stored anomaly evidence. Django lifecycle checks remain authoritative.',
                  style: TextStyle(color: _muted, fontSize: 11),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  key: ValueKey(anomaly.id),
                  initialValue: anomaly.id,
                  decoration: const InputDecoration(
                    labelText: 'Anomaly context',
                  ),
                  items: state.context!.anomalies
                      .map(
                        (item) => DropdownMenuItem(
                          value: item.id,
                          child: Text(
                            '${item.displayService} · ${item.displayServer}',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      )
                      .toList(),
                  onChanged: state.loading
                      ? null
                      : (id) {
                          final selected = state.context!.anomalies.firstWhere(
                            (item) => item.id == id,
                          );
                          notifier.selectAnomaly(selected);
                        },
                ),
                const SizedBox(height: 14),
                _EvidencePanel(anomaly: anomaly),
                const SizedBox(height: 18),
                Row(
                  children: [
                    const SectionTitle('CONVERSATION'),
                    const Spacer(),
                    Icon(
                      state.connected ? Icons.circle : Icons.circle_outlined,
                      color: state.connected
                          ? const Color(0xFF35D17C)
                          : _warning,
                      size: 10,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      state.connected ? 'connected' : 'disconnected',
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 10,
                        fontFamily: 'monospace',
                      ),
                    ),
                    if (!state.connected)
                      TextButton(
                        onPressed: state.loading ? null : notifier.reconnect,
                        child: const Text('Reconnect'),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                _Messages(
                  messages: state.messages,
                  streamingText: state.streamingText,
                  generating: state.generating,
                ),
                if (state.error != null) ...[
                  const SizedBox(height: 10),
                  _ErrorBanner(
                    message: state.error!,
                    onRetry: state.lastFailedText == null
                        ? notifier.reconnect
                        : notifier.retry,
                  ),
                ],
                const SizedBox(height: 18),
                const SectionTitle('SUGGESTED PROMPTS'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: state.context!.prompts
                      .map(
                        (prompt) => ActionChip(
                          label: Text(
                            prompt,
                            style: const TextStyle(fontSize: 10),
                          ),
                          onPressed: () {
                            controller.text = prompt;
                            setState(() {});
                          },
                        ),
                      )
                      .toList(),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: controller,
                  minLines: 1,
                  maxLines: 4,
                  maxLength: 2000,
                  onChanged: (_) => setState(() {}),
                  onSubmitted: (_) => _send(notifier, state),
                  decoration: InputDecoration(
                    hintText:
                        'Ask what the anomaly means or what to check next…',
                    suffixIcon: IconButton(
                      onPressed:
                          controller.text.trim().isEmpty ||
                              state.generating ||
                              !state.context!.geminiConfigured
                          ? null
                          : () => _send(notifier, state),
                      icon: const Icon(Icons.send_rounded, color: _purple),
                    ),
                  ),
                ),
                if (!state.context!.geminiConfigured)
                  const Text(
                    'Gemini is not configured. Add GEMINI_API_KEY to backend/.env and rebuild the backend.',
                    style: TextStyle(color: _warning, fontSize: 10),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _send(AssistantController notifier, AssistantState state) async {
    final text = controller.text.trim();
    if (text.isEmpty || state.generating) return;
    controller.clear();
    setState(() {});
    await notifier.send(text);
  }
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({required this.anomaly});
  final AnomalyDetection anomaly;

  @override
  Widget build(BuildContext context) => AppPanel(
    borderColor: const Color(0xFF483161),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          anomaly.displayService,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text(
          '${anomaly.displayServer} · model ${anomaly.modelVersion}',
          style: const TextStyle(color: _muted, fontSize: 10),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _chip('score ${anomaly.anomalyScore.toStringAsFixed(4)}'),
            _chip(
              'confidence ${(anomaly.confidenceScore * 100).clamp(0, 100).round()}%',
            ),
            ..._features.entries.map(
              (entry) => _chip(
                '${entry.value.$1} ${_metric(anomaly.featureValues[entry.key], entry.value.$2)}',
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

class _Messages extends StatelessWidget {
  const _Messages({
    required this.messages,
    required this.streamingText,
    required this.generating,
  });
  final List<AssistantMessage> messages;
  final String streamingText;
  final bool generating;

  @override
  Widget build(BuildContext context) => AppPanel(
    child: messages.isEmpty && !generating
        ? const SizedBox(
            height: 100,
            child: Center(
              child: Text(
                'Ask Gemini about the selected anomaly.',
                style: TextStyle(color: _muted),
              ),
            ),
          )
        : Column(
            children: [
              ...messages.map((message) => _MessageBubble(message: message)),
              if (generating)
                _MessageBubble(
                  message: AssistantMessage(
                    id: 'streaming',
                    sender: 'assistant',
                    text: streamingText.isEmpty ? 'Thinking…' : streamingText,
                    createdAt: null,
                    streaming: true,
                  ),
                ),
            ],
          ),
  );
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});
  final AssistantMessage message;

  @override
  Widget build(BuildContext context) {
    final user = message.sender == 'user';
    return Align(
      alignment: user ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 720),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: user ? const Color(0xFF213A63) : const Color(0xFF1E1729),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: user ? const Color(0xFF315A94) : const Color(0xFF483161),
          ),
        ),
        child: SelectableText(
          message.text,
          style: TextStyle(
            color: message.streaming && message.text == 'Thinking…'
                ? _muted
                : null,
            height: 1.4,
          ),
        ),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => AppPanel(
    borderColor: const Color(0xFF6B2835),
    child: Row(
      children: [
        Expanded(child: Text(message)),
        TextButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    ),
  );
}

class _LoadFailure extends StatelessWidget {
  const _LoadFailure({required this.onRetry});
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Center(
    child: FilledButton(
      onPressed: onRetry,
      child: const Text('Retry anomaly assistant'),
    ),
  );
}

class _EmptyAssistant extends StatelessWidget {
  const _EmptyAssistant();
  @override
  Widget build(BuildContext context) => const Center(
    child: Padding(
      padding: EdgeInsets.all(24),
      child: Text(
        'No anomalous service windows are available yet. Generate and detect an anomaly before starting an AI conversation.',
        textAlign: TextAlign.center,
      ),
    ),
  );
}

const _features = <String, (String, String)>{
  'cpu_r': ('CPU', '%'),
  'mem_u': ('memory', '%'),
  'disk_r': ('disk read', 'B/s'),
  'disk_w': ('disk write', 'B/s'),
  'eth1_fi': ('network in', 'B/s'),
  'eth1_fo': ('network out', 'B/s'),
};

Widget _chip(String text) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
  decoration: BoxDecoration(
    color: const Color(0xFF2D2142),
    border: Border.all(color: const Color(0xFF614880)),
    borderRadius: BorderRadius.circular(20),
  ),
  child: Text(
    text,
    style: const TextStyle(
      color: _purple,
      fontSize: 9,
      fontFamily: 'monospace',
    ),
  ),
);
String _metric(double? value, String unit) =>
    value == null ? 'no data' : '${value.toStringAsFixed(2)} $unit';
