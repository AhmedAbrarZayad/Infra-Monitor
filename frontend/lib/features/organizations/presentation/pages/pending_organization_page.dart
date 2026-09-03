import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../domain/organization_context_state.dart';
import '../providers/organization_provider.dart';

class PendingOrganizationPage extends ConsumerWidget {
  const PendingOrganizationPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(organizationContextProvider);
    final pending = state is OrganizationPendingOnly ? state.context.pendingMemberships : const [];
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Awaiting approval')),
      body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 620), child: ListView(
        padding: const EdgeInsets.all(24), children: [
          const Icon(Icons.hourglass_top_rounded, size: 58, color: AppColors.primary),
          const SizedBox(height: 14),
          const Text('Your request is pending', textAlign: TextAlign.center, style: TextStyle(fontSize: 23, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          const Text('An organization owner or admin must approve your request before you can enter the app.', textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary, height: 1.5)),
          ...pending.map((item) => Padding(padding: const EdgeInsets.only(top: 14), child: AppPanel(child: ListTile(
            leading: const Icon(Icons.business_outlined), title: Text(item.organization.name), subtitle: Text(item.organization.summary),
          )))),
          const SizedBox(height: 22),
          AppButton(label: 'Check approval status', icon: Icons.refresh, onPressed: () => ref.read(organizationContextProvider.notifier).load()),
          const SizedBox(height: 10),
          AppButton(label: 'Join another organization', icon: Icons.search, variant: AppButtonVariant.secondary, onPressed: () => context.go('/organization/join')),
          TextButton(onPressed: () => ref.read(authProvider.notifier).logout(), child: const Text('Sign out')),
        ],
      ))),
    );
  }
}
