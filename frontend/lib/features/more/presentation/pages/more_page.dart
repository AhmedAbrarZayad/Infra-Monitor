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
import '../../../organizations/data/organization_models.dart';
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
  String? _processingMembershipId;
  int? _processingUserId;

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: AppColors.danger),
    );
  }

  Future<void> _approveMembership(
    OrganizationReady organization,
    String membershipId,
  ) async {
    if (_processingMembershipId != null) return;
    setState(() => _processingMembershipId = membershipId);
    final error = await ref
        .read(organizationContextProvider.notifier)
        .approveMembership(
          organizationId: organization.activeMembership.organization.id,
          membershipId: membershipId,
        );
    if (!mounted) return;
    setState(() => _processingMembershipId = null);
    if (error != null) _showError(error);
  }

  Future<void> _rejectMembership(
    OrganizationReady organization,
    OrganizationMembership membership,
  ) async {
    if (_processingMembershipId != null) return;
    final confirmed = await AppDialogs.confirm(
      context,
      title: 'Reject request?',
      message: 'Reject ${membership.user.displayName} from joining this organization?',
      confirmLabel: 'Reject',
      isDestructive: true,
    );
    if (!confirmed || !mounted) return;
    setState(() => _processingMembershipId = membership.id);
    final error = await ref
        .read(organizationContextProvider.notifier)
        .rejectMembership(
          organizationId: organization.activeMembership.organization.id,
          membershipId: membership.id,
        );
    if (!mounted) return;
    setState(() => _processingMembershipId = null);
    if (error != null) _showError(error);
  }

  Future<void> _changeMemberRole(
    OrganizationReady organization,
    OrganizationMembership membership,
    String role,
  ) async {
    if (_processingUserId != null || membership.role == role) return;
    setState(() => _processingUserId = membership.user.id);
    final error = await ref
        .read(organizationContextProvider.notifier)
        .changeMemberRole(
          organizationId: organization.activeMembership.organization.id,
          userId: membership.user.id,
          role: role,
        );
    if (!mounted) return;
    setState(() => _processingUserId = null);
    if (error != null) _showError(error);
  }

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
    final members = active.capabilities.canListMembers
        ? ref.watch(organizationMembersProvider(active.organization.id))
        : null;
    final pendingRequests =
        active.capabilities.canListMembers && active.role == 'OWNER'
        ? ref.watch(pendingOrganizationMembershipsProvider(active.organization.id))
        : null;
    final displayName = '${user.firstName} ${user.lastName}'.trim().isEmpty
        ? user.username
        : '${user.firstName} ${user.lastName}'.trim();
    final initials = displayName
        .split(' ')
        .where((part) => part.isNotEmpty)
        .take(2)
        .map((part) => part[0])
        .join()
        .toUpperCase();

    return AsyncValueView(
      value: ref.watch(preferencesProvider),
      data: (preferences) => ListView(
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
                        CircleAvatar(
                          backgroundColor: const Color(0xFF17263D),
                          child: Text(
                            initials,
                            style: const TextStyle(
                              color: AppColors.primary,
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
                                displayName,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 14,
                                ),
                              ),
                              Text(
                                user.email,
                                style: const TextStyle(
                                  color: AppColors.textSecondary,
                                  fontFamily: 'monospace',
                                  fontSize: 10,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Icon(
                          Icons.shield_outlined,
                          color: AppColors.primary,
                          size: 16,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          active.role,
                          style: const TextStyle(
                            color: AppColors.primary,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 22),
                  const SectionTitle('ORGANIZATION'),
                  const SizedBox(height: 10),
                  AppPanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          active.organization.name,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          active.organization.summary,
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      if (contextData.memberships.length > 1)
                        AppButton(
                          label: 'Switch organization',
                          icon: Icons.swap_horiz,
                          onPressed: () => showModalBottomSheet<void>(
                            context: context,
                            builder: (sheetContext) => SafeArea(
                              child: ListView(
                                shrinkWrap: true,
                                padding: const EdgeInsets.only(bottom: 12),
                                children: [
                                  const ListTile(
                                    title: Text(
                                      'Switch organization',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                  ...contextData.memberships.map(
                                    (membership) => ListTile(
                                      leading: Icon(
                                        membership.organization.id ==
                                                active.organization.id
                                            ? Icons.check_circle
                                            : Icons.business_outlined,
                                        color:
                                            membership.organization.id ==
                                                active.organization.id
                                            ? AppColors.success
                                            : null,
                                      ),
                                      title: Text(membership.organization.name),
                                      subtitle: Text(membership.displayRole),
                                      selected:
                                          membership.organization.id ==
                                          active.organization.id,
                                      onTap:
                                          membership.organization.id ==
                                              active.organization.id
                                          ? null
                                          : () async {
                                              Navigator.pop(sheetContext);
                                              await ref
                                                  .read(
                                                    organizationContextProvider
                                                        .notifier,
                                                  )
                                                  .selectOrganization(
                                                    membership.organization.id,
                                                  );
                                            },
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      AppButton(
                        label: 'Join another organization',
                        icon: Icons.group_add_outlined,
                        variant: AppButtonVariant.secondary,
                        onPressed: () => context.push('/organization/join'),
                      ),
                      if (contextData.canCreateOrganization)
                        AppButton(
                          label: 'Create organization',
                          icon: Icons.add_business,
                          onPressed: () => context.push('/organization/create'),
                        ),
                    ],
                  ),
                  if (contextData.pendingMemberships.isNotEmpty) ...[
                    const SizedBox(height: 22),
                    const SectionTitle('PENDING REQUESTS'),
                    const SizedBox(height: 10),
                    AppPanel(
                      child: Column(
                        children: contextData.pendingMemberships
                            .map(
                              (item) => ListTile(
                                contentPadding: EdgeInsets.zero,
                                leading: const Icon(
                                  Icons.hourglass_top,
                                  color: AppColors.textSecondary,
                                ),
                                title: Text(item.organization.name),
                                subtitle: Text(item.organization.summary),
                                trailing: const Text(
                                  'PENDING',
                                  style: TextStyle(
                                    color: AppColors.warning,
                                    fontSize: 10,
                                  ),
                                ),
                              ),
                            )
                            .toList(),
                      ),
                    ),
                  ],
                  if (pendingRequests != null) ...[
                    const SizedBox(height: 22),
                    const SectionTitle('JOIN REQUESTS'),
                    const SizedBox(height: 10),
                    AppPanel(
                      child: pendingRequests.when(
                        loading: () => const Padding(
                          padding: EdgeInsets.all(18),
                          child: Center(child: CircularProgressIndicator()),
                        ),
                        error: (_, _) => Row(
                          children: [
                            const Expanded(
                              child: Text('Unable to load join requests.'),
                            ),
                            IconButton(
                              onPressed: () => ref.invalidate(
                                pendingOrganizationMembershipsProvider(
                                  active.organization.id,
                                ),
                              ),
                              icon: const Icon(Icons.refresh),
                            ),
                          ],
                        ),
                        data: (items) {
                          if (items.isEmpty) {
                            return const Padding(
                              padding: EdgeInsets.symmetric(vertical: 8),
                              child: Text(
                                'No pending join requests.',
                                style: TextStyle(
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            );
                          }
                          return Column(
                            children: items
                                .map(
                                  (item) => _JoinRequestRow(
                                    membership: item,
                                    isProcessing:
                                        _processingMembershipId == item.id,
                                    actionsDisabled:
                                        _processingMembershipId != null,
                                    onApprove: () => _approveMembership(
                                      organizationState,
                                      item.id,
                                    ),
                                    onReject: () => _rejectMembership(
                                      organizationState,
                                      item,
                                    ),
                                  ),
                                )
                                .toList(),
                          );
                        },
                      ),
                    ),
                  ],
                  if (members != null) ...[
                    const SizedBox(height: 22),
                    const SectionTitle('MEMBERS'),
                    const SizedBox(height: 10),
                    AppPanel(
                      child: members.when(
                        loading: () => const Padding(
                          padding: EdgeInsets.all(18),
                          child: Center(child: CircularProgressIndicator()),
                        ),
                        error: (_, _) => Row(
                          children: [
                            const Expanded(
                              child: Text('Unable to load members.'),
                            ),
                            IconButton(
                              onPressed: () => ref.invalidate(
                                organizationMembersProvider(
                                  active.organization.id,
                                ),
                              ),
                              icon: const Icon(Icons.refresh),
                            ),
                          ],
                        ),
                        data: (items) => Column(
                          children: items
                              .map(
                                (item) => _MemberRow(
                                  membership: item,
                                  canChangeRole:
                                      active.role == 'OWNER' &&
                                      item.role != 'OWNER',
                                  isProcessing:
                                      _processingUserId == item.user.id,
                                  onRoleChanged: (role) => _changeMemberRole(
                                    organizationState,
                                    item,
                                    role,
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 22),
                  const SectionTitle('ENVIRONMENT PREFERENCE'),
                  const SizedBox(height: 10),
                  _choices(
                    ['Production', 'Staging'],
                    environment,
                    (value) => setState(() => environment = value),
                  ),
                  const SizedBox(height: 22),
                  const SectionTitle('PREFERENCES'),
                  const SizedBox(height: 10),
                  AppPanel(
                    child: Wrap(
                      spacing: 28,
                      runSpacing: 18,
                      children: [
                        _preference('NOTIFICATIONS', preferences.notifications),
                        _preference('THEME', preferences.theme),
                        _preference(
                          'REFRESH INTERVAL',
                          preferences.refreshInterval,
                        ),
                        _preference('TIMEZONE', preferences.timezone),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  AppButton(
                    label: preferences.notifications == 'enabled'
                        ? 'Disable notifications'
                        : 'Enable notifications',
                    variant: AppButtonVariant.secondary,
                    onPressed: () => setNotifications(
                      ref,
                      preferences.notifications != 'enabled',
                    ),
                  ),
                  const SizedBox(height: 22),
                  SizedBox(
                    width: double.infinity,
                    child: AppButton(
                      label: 'Sign out',
                      icon: Icons.logout,
                      variant: AppButtonVariant.danger,
                      onPressed: () async {
                        final confirmed = await AppDialogs.confirm(
                          context,
                          title: 'Sign out?',
                          message: 'Are you sure you want to end this session?',
                          confirmLabel: 'Sign out',
                          isDestructive: true,
                        );
                        if (confirmed)
                          await ref.read(authProvider.notifier).logout();
                      },
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
  }

  Widget _choices(
    List<String> values,
    String selected,
    ValueChanged<String> onChange,
  ) => Wrap(
    spacing: 8,
    runSpacing: 8,
    children: values
        .map(
          (value) => SelectionPill(
            label: value,
            selected: selected == value,
            onTap: () => onChange(value),
          ),
        )
        .toList(),
  );

  Widget _preference(String label, String value) => SizedBox(
    width: 160,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 9),
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

class _JoinRequestRow extends StatelessWidget {
  const _JoinRequestRow({
    required this.membership,
    required this.isProcessing,
    required this.actionsDisabled,
    required this.onApprove,
    required this.onReject,
  });

  final OrganizationMembership membership;
  final bool isProcessing;
  final bool actionsDisabled;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  @override
  Widget build(BuildContext context) {
    final actions = Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.end,
      children: [
        AppButton(
          label: 'Reject',
          icon: Icons.close,
          variant: AppButtonVariant.secondary,
          isLoading: isProcessing,
          onPressed: actionsDisabled ? null : onReject,
        ),
        AppButton(
          label: 'Approve',
          icon: Icons.check,
          isLoading: isProcessing,
          onPressed: actionsDisabled ? null : onApprove,
        ),
      ],
    );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 520;
          final identity = Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const CircleAvatar(child: Icon(Icons.person_add_alt_1)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      membership.user.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      membership.user.email,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                identity,
                const SizedBox(height: 10),
                Align(alignment: Alignment.centerRight, child: actions),
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: identity),
              const SizedBox(width: 16),
              Flexible(child: actions),
            ],
          );
        },
      ),
    );
  }
}

class _MemberRow extends StatelessWidget {
  const _MemberRow({
    required this.membership,
    required this.canChangeRole,
    required this.isProcessing,
    required this.onRoleChanged,
  });

  final OrganizationMembership membership;
  final bool canChangeRole;
  final bool isProcessing;
  final ValueChanged<String> onRoleChanged;

  @override
  Widget build(BuildContext context) {
    final roleControl = canChangeRole
        ? DropdownButton<String>(
            value: membership.role,
            items: const [
              DropdownMenuItem(value: 'ADMIN', child: Text('Admin')),
              DropdownMenuItem(value: 'ENGINEER', child: Text('Engineer')),
            ],
            onChanged: isProcessing
                ? null
                : (role) {
                    if (role != null) onRoleChanged(role);
                  },
          )
        : Text(
            membership.role,
            style: const TextStyle(color: AppColors.primary, fontSize: 10),
          );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 520;
          final identity = Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const CircleAvatar(child: Icon(Icons.person_outline)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      membership.user.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      membership.user.email,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                identity,
                const SizedBox(height: 8),
                Align(alignment: Alignment.centerRight, child: roleControl),
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: identity),
              const SizedBox(width: 16),
              roleControl,
            ],
          );
        },
      ),
    );
  }
}
