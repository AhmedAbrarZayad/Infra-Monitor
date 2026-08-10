import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_dialogs.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../../../shared/widgets/selection_pill.dart';
import '../providers/preferences_providers.dart';

class MorePage extends ConsumerStatefulWidget {
  const MorePage({super.key});
  @override
  ConsumerState<MorePage> createState() => _MorePageState();
}

class _MorePageState extends ConsumerState<MorePage> {
  String role = 'Administrator', environment = 'Production', stream = 'live';
  @override
  Widget build(BuildContext context) => AsyncValueView(
    value: ref.watch(preferencesProvider),
    data: (data) => ListView(
      padding: const EdgeInsets.all(14),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppPanel(
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: const Color(0xFF17263D),
                          border: Border.all(color: const Color(0xFF355681)),
                          borderRadius: BorderRadius.circular(13),
                        ),
                        child: const Text(
                          'AP',
                          style: TextStyle(
                            color: Color(0xFF5D9DFF),
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              data.name,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                            Text(
                              data.email,
                              style: const TextStyle(
                                color: Color(0xFF929CAD),
                                fontFamily: 'monospace',
                                fontSize: 9,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const Icon(
                        Icons.shield_outlined,
                        color: Color(0xFF579CFF),
                        size: 15,
                      ),
                      const SizedBox(width: 5),
                      const Text(
                        'Admin',
                        style: TextStyle(
                          color: Color(0xFF579CFF),
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
                const SectionTitle(
                  'ROLE',
                  subtitle: 'viewers get read-only access',
                ),
                const SizedBox(height: 10),
                _choices(
                  ['Administrator', 'Viewer'],
                  role,
                  (v) => setState(() => role = v),
                ),
                const SizedBox(height: 22),
                const SectionTitle('ENVIRONMENT PREFERENCE'),
                const SizedBox(height: 10),
                _choices(
                  ['Production', 'Staging'],
                  environment,
                  (v) => setState(() => environment = v),
                ),
                const SizedBox(height: 22),
                const SectionTitle(
                  'STREAM STATE',
                  subtitle: 'simulate real-time connection states',
                ),
                const SizedBox(height: 10),
                _choices(
                  ['live', 'reconnecting', 'offline'],
                  stream,
                  (v) => setState(() => stream = v),
                ),
                const SizedBox(height: 22),
                const SectionTitle('PREFERENCES'),
                const SizedBox(height: 10),
                AppPanel(
                  child: LayoutBuilder(
                    builder: (context, c) {
                      final wide = c.maxWidth > 550;
                      final cells = [
                        _preference('NOTIFICATIONS', data.notifications),
                        _preference('THEME', data.theme),
                        _preference('REFRESH INTERVAL', data.refreshInterval),
                        _preference('TIMEZONE', data.timezone),
                      ];
                      return GridView.count(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        crossAxisCount: wide ? 4 : 2,
                        childAspectRatio: 2.5,
                        children: cells,
                      );
                    },
                  ),
                ),
                const SizedBox(height: 22),
                const SectionTitle('SECURITY & AUDIT'),
                const SizedBox(height: 10),
                AppPanel(
                  child: Column(
                    children: [
                      const Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.security,
                            color: Color(0xFF35D17C),
                            size: 16,
                          ),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Secrets, tokens, API keys, session values, connection strings and customer data are masked at ingestion and never shown in logs or AI output.',
                              style: TextStyle(
                                color: Color(0xFF929CAD),
                                fontSize: 10,
                                height: 1.7,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: AppButton(
                          label: 'View audit log',
                          icon: Icons.manage_search,
                          variant: AppButtonVariant.secondary,
                          onPressed: null,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: AppButton(
                    label: 'Sign out',
                    icon: Icons.logout,
                    variant: AppButtonVariant.danger,
                    onPressed: () => AppDialogs.confirm(
                      context,
                      title: 'Sign out?',
                      message: 'Are you sure you want to end this session?',
                      confirmLabel: 'Sign out',
                      isDestructive: true,
                    ),
                  ),
                ),
                const SizedBox(height: 30),
              ],
            ),
          ),
        ),
      ],
    ),
  );
  Widget _choices(
    List<String> values,
    String selected,
    ValueChanged<String> onChange,
  ) => Wrap(
    spacing: 8,
    runSpacing: 8,
    children: values
        .map(
          (v) => SelectionPill(
            label: v,
            selected: selected == v,
            onTap: () => onChange(v),
          ),
        )
        .toList(),
  );
  Widget _preference(String label, String value) => Padding(
    padding: const EdgeInsets.all(2),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: Color(0xFF8993A4), fontSize: 9),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: const TextStyle(
            fontFamily: 'monospace',
            fontWeight: FontWeight.w700,
            fontSize: 11,
          ),
        ),
      ],
    ),
  );
}
