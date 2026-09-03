import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_dialogs.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../../../shared/widgets/selection_pill.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../providers/preferences_providers.dart';

class MorePage extends ConsumerStatefulWidget {
  const MorePage({super.key});
  @override
  ConsumerState<MorePage> createState() => _MorePageState();
}

class _MorePageState extends ConsumerState<MorePage> {
  String environment = 'Production';
  String stream = 'live';

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final organizationState = ref.watch(organizationContextProvider);
    if (auth is! AuthAuthenticated || organizationState is! OrganizationReady) {
      return const Center(child: CircularProgressIndicator());
    }
    final user = auth.user;
    final contextData = organizationState.context;
    final active = organizationState.activeMembership;
    final members = ref.watch(organizationMembersProvider(active.organization.id));
    final displayName = '${user.firstName} ${user.lastName}'.trim().isEmpty
        ? user.username
        : '${user.firstName} ${user.lastName}'.trim();
    final initials = displayName.split(' ').where((part) => part.isNotEmpty).take(2).map((part) => part[0]).join().toUpperCase();

    return AsyncValueView(
      value: ref.watch(preferencesProvider),
      data: (preferences) => ListView(
        padding: const EdgeInsets.all(14),
        children: [Center(child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            AppPanel(child: Row(children: [
              CircleAvatar(backgroundColor: const Color(0xFF17263D), child: Text(initials, style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700))),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(displayName, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                Text(user.email, style: const TextStyle(color: AppColors.textSecondary, fontFamily: 'monospace', fontSize: 10)),
              ])),
              const Icon(Icons.shield_outlined, color: AppColors.primary, size: 16),
              const SizedBox(width: 5), Text(active.role, style: const TextStyle(color: AppColors.primary, fontSize: 10)),
            ])),
            const SizedBox(height: 22),
            const SectionTitle('ORGANIZATION'),
            const SizedBox(height: 10),
            AppPanel(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(active.organization.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text(active.organization.summary, style: const TextStyle(color: AppColors.textSecondary)),
              if (contextData.memberships.length > 1) ...[
                const SizedBox(height: 14),
                DropdownButtonFormField<String>(
                  initialValue: active.organization.id,
                  decoration: const InputDecoration(labelText: 'Active organization'),
                  items: contextData.memberships.map((item) => DropdownMenuItem(value: item.organization.id, child: Text(item.organization.name))).toList(),
                  onChanged: (value) { if (value != null) ref.read(organizationContextProvider.notifier).selectOrganization(value); },
                ),
              ],
              const SizedBox(height: 14),
              Wrap(spacing: 10, runSpacing: 10, children: [
                AppButton(label: 'Join organization', icon: Icons.group_add_outlined, variant: AppButtonVariant.secondary, onPressed: () => context.push('/organization/join')),
                if (contextData.canCreateOrganization)
                  AppButton(label: 'Create organization', icon: Icons.add_business, onPressed: () => context.push('/organization/create')),
              ]),
            ])),
            if (contextData.pendingMemberships.isNotEmpty) ...[
              const SizedBox(height: 22),
              const SectionTitle('PENDING REQUESTS'),
              const SizedBox(height: 10),
              AppPanel(child: Column(children: contextData.pendingMemberships.map((item) => ListTile(
                contentPadding: EdgeInsets.zero, leading: const Icon(Icons.hourglass_top, color: AppColors.textSecondary),
                title: Text(item.organization.name), subtitle: Text(item.organization.summary), trailing: const Text('PENDING', style: TextStyle(color: AppColors.warning, fontSize: 10)),
              )).toList())),
            ],
            const SizedBox(height: 22),
            const SectionTitle('MEMBERS'),
            const SizedBox(height: 10),
            AppPanel(child: members.when(
              loading: () => const Padding(padding: EdgeInsets.all(18), child: Center(child: CircularProgressIndicator())),
              error: (_, _) => Row(children: [const Expanded(child: Text('Unable to load members.')), IconButton(onPressed: () => ref.invalidate(organizationMembersProvider(active.organization.id)), icon: const Icon(Icons.refresh))]),
              data: (items) => Column(children: items.map((item) => ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const CircleAvatar(child: Icon(Icons.person_outline)),
                title: Text(item.user.displayName), subtitle: Text(item.user.email),
                trailing: Text(item.role, style: const TextStyle(color: AppColors.primary, fontSize: 10)),
              )).toList()),
            )),
            const SizedBox(height: 22),
            const SectionTitle('ENVIRONMENT PREFERENCE'),
            const SizedBox(height: 10),
            _choices(['Production', 'Staging'], environment, (value) => setState(() => environment = value)),
            const SizedBox(height: 22),
            const SectionTitle('STREAM STATE', subtitle: 'simulate real-time connection states'),
            const SizedBox(height: 10),
            _choices(['live', 'reconnecting', 'offline'], stream, (value) => setState(() => stream = value)),
            const SizedBox(height: 22),
            const SectionTitle('PREFERENCES'),
            const SizedBox(height: 10),
            AppPanel(child: Wrap(spacing: 28, runSpacing: 18, children: [
              _preference('NOTIFICATIONS', preferences.notifications), _preference('THEME', preferences.theme),
              _preference('REFRESH INTERVAL', preferences.refreshInterval), _preference('TIMEZONE', preferences.timezone),
            ])),
            const SizedBox(height: 22),
            SizedBox(width: double.infinity, child: AppButton(label: 'Sign out', icon: Icons.logout, variant: AppButtonVariant.danger, onPressed: () async {
              final confirmed = await AppDialogs.confirm(context, title: 'Sign out?', message: 'Are you sure you want to end this session?', confirmLabel: 'Sign out', isDestructive: true);
              if (confirmed) await ref.read(authProvider.notifier).logout();
            })),
            const SizedBox(height: 30),
          ]),
        ))],
      ),
    );
  }

  Widget _choices(List<String> values, String selected, ValueChanged<String> onChange) => Wrap(
    spacing: 8, runSpacing: 8,
    children: values.map((value) => SelectionPill(label: value, selected: selected == value, onTap: () => onChange(value))).toList(),
  );

  Widget _preference(String label, String value) => SizedBox(width: 160, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 9)),
    const SizedBox(height: 3), Text(value, style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700, fontSize: 11)),
  ]));
}
