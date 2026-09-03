import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../domain/auth_state.dart';
import '../providers/auth_provider.dart';

class SessionRestoreErrorPage extends ConsumerWidget {
  const SessionRestoreErrorPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final message = auth is AuthSessionRestoreError
        ? auth.message
        : 'Unable to restore your session.';
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.cloud_off_outlined, size: 58, color: AppColors.danger),
                const SizedBox(height: 16),
                Text(message, textAlign: TextAlign.center),
                const SizedBox(height: 20),
                AppButton(
                  label: 'Try again',
                  icon: Icons.refresh,
                  onPressed: () => ref.read(authProvider.notifier).retrySessionRestore(),
                ),
                TextButton(
                  onPressed: () => ref.read(authProvider.notifier).clearSession(),
                  child: const Text('Return to sign in'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
