import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../domain/organization_context_state.dart';
import '../providers/organization_provider.dart';

class OrganizationOnboardingPage extends ConsumerWidget {
  const OrganizationOnboardingPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(Icons.hub_outlined, size: 68, color: AppColors.primary),
                    const SizedBox(height: 20),
                    const Text('Choose your organization', textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 25, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 10),
                    const Text('Create a workspace for your team or request access to an existing one.',
                        textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary, height: 1.5)),
                    const SizedBox(height: 32),
                    AppButton(label: 'Create organization', icon: Icons.add_business,
                        onPressed: () => context.go('/organization/create')),
                    const SizedBox(height: 12),
                    AppButton(label: 'Join organization', icon: Icons.group_add_outlined,
                        variant: AppButtonVariant.secondary,
                        onPressed: () => context.go('/organization/join')),
                    const SizedBox(height: 24),
                    TextButton(onPressed: () => ref.read(authProvider.notifier).logout(), child: const Text('Sign out')),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class OrganizationLoadingPage extends StatelessWidget {
  const OrganizationLoadingPage({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold(
        backgroundColor: AppColors.background,
        body: Center(child: CircularProgressIndicator()),
      );
}

class OrganizationErrorPage extends ConsumerWidget {
  const OrganizationErrorPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(organizationContextProvider);
    final message = state is OrganizationContextError ? state.message : 'Unable to load organization access.';
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Icon(Icons.cloud_off_outlined, size: 58, color: AppColors.danger),
              const SizedBox(height: 16),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 20),
              AppButton(label: 'Try again', icon: Icons.refresh,
                  onPressed: () => ref.read(organizationContextProvider.notifier).load()),
              TextButton(onPressed: () => ref.read(authProvider.notifier).logout(), child: const Text('Sign out')),
            ]),
          ),
        ),
      ),
    );
  }
}
