import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../../../shared/widgets/selection_pill.dart';
import '../providers/assistant_providers.dart';

class AiAssistantPage extends ConsumerStatefulWidget {
  const AiAssistantPage({super.key});
  @override
  ConsumerState<AiAssistantPage> createState() => _AiAssistantPageState();
}

class _AiAssistantPageState extends ConsumerState<AiAssistantPage> {
  String selected = 'INC-2481';
  final controller = TextEditingController();
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AsyncValueView(
    value: ref.watch(assistantContextProvider),
    data: (data) => ListView(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 26),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1000),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: data.incidentIds
                        .map(
                          (id) => Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: SelectionPill(
                              label: id,
                              selected: selected == id,
                              onTap: () => setState(() => selected = id),
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
                const SizedBox(height: 20),
                AppPanel(
                  borderColor: const Color(0xFF483161),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'context: $selected',
                              style: const TextStyle(
                                color: Color(0xFFC697F5),
                                fontFamily: 'monospace',
                                fontSize: 10,
                              ),
                            ),
                          ),
                          _chip('✣ AI conf: medium'),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        data.title,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 10),
                      ...data.evidence.map(
                        (item) => Padding(
                          padding: const EdgeInsets.only(bottom: 7),
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: _chip(item),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                AppPanel(
                  child: SizedBox(
                    height: 124,
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.auto_awesome,
                            color: Color(0xFFC697F5),
                            size: 30,
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'Ask about your infrastructure',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Select an incident or ask about server health, logs,\nor recent alerts.',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: const Color(0xFF929CAD)),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                const SectionTitle('SUGGESTED PROMPTS'),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: data.prompts
                      .map(
                        (prompt) => ActionChip(
                          label: Text(
                            prompt,
                            style: const TextStyle(fontSize: 10),
                          ),
                          backgroundColor: const Color(0xFF0E1420),
                          side: const BorderSide(color: Color(0xFF2A3445)),
                          onPressed: () {
                            controller.text = prompt;
                            setState(() {});
                          },
                        ),
                      )
                      .toList(),
                ),
                const SizedBox(height: 20),
                const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.security, color: Color(0xFF35D17C), size: 14),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Secrets, tokens and customer data are redacted before reaching the model. Instructions found inside log content are never executed.',
                        style: TextStyle(
                          color: Color(0xFF8BA0C4),
                          fontFamily: 'monospace',
                          fontSize: 9,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: controller,
                  decoration: InputDecoration(
                    hintText: 'ask about incidents, logs, metrics…',
                    filled: true,
                    fillColor: const Color(0xFF111722),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(15),
                    ),
                    suffixIcon: IconButton(
                      onPressed: controller.text.trim().isEmpty ? null : () {},
                      icon: const Icon(
                        Icons.send_rounded,
                        color: Color(0xFFC697F5),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
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
        color: Color(0xFFC697F5),
        fontSize: 9,
        fontFamily: 'monospace',
      ),
    ),
  );
}
