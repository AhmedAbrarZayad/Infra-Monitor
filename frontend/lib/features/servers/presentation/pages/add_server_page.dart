import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../auth/presentation/widgets/auth_text_field.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../data/monitoring_api.dart';
import '../providers/servers_providers.dart';

class AddServerPage extends ConsumerStatefulWidget {
  const AddServerPage({super.key});

  @override
  ConsumerState<AddServerPage> createState() => _AddServerPageState();
}

class _AddServerPageState extends ConsumerState<AddServerPage> {
  final _formKey = GlobalKey<FormState>();
  final _serverName = TextEditingController();
  String _environment = 'development';
  bool _submitting = false;
  ServerEnrollment? _enrollment;

  @override
  void dispose() {
    _serverName.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting || !_formKey.currentState!.validate()) return;
    final api = ref.read(monitoringApiProvider);
    if (api == null) return;
    setState(() => _submitting = true);
    try {
      final enrollment = await api.createEnrollment(
        serverName: _serverName.text.trim(),
        environment: _environment,
      );
      if (!mounted) return;
      setState(() => _enrollment = enrollment);
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.message),
          backgroundColor: AppColors.danger,
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to create the enrollment. Try again.'),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _copyCommand() async {
    final command = _enrollment?.installCommand;
    if (command == null) return;
    await Clipboard.setData(ClipboardData(text: command));
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Install command copied.')));
  }

  @override
  Widget build(BuildContext context) {
    final organization = ref.watch(organizationContextProvider);
    final allowed =
        organization is OrganizationReady &&
        const {'OWNER', 'ADMIN'}.contains(organization.activeMembership.role);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Add server')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: !allowed
                ? AppPanel(
                    child: Column(
                      children: [
                        const Icon(Icons.lock_outline, size: 36),
                        const SizedBox(height: 12),
                        const Text(
                          'Owner or admin access is required to add a server.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 16),
                        AppButton(label: 'Go back', onPressed: context.pop),
                      ],
                    ),
                  )
                : _enrollment == null
                ? _form()
                : _result(_enrollment!),
          ),
        ),
      ),
    );
  }

  Widget _form() => Form(
    key: _formKey,
    child: AppPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Enroll a monitored server',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          const Text(
            'Generate a single-use command, then run it on the Linux server.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 22),
          AuthTextField(
            controller: _serverName,
            label: 'Server name',
            hint: 'Multipass Lab',
            validator: (value) => value == null || value.trim().isEmpty
                ? 'Server name is required'
                : null,
          ),
          const SizedBox(height: 18),
          DropdownButtonFormField<String>(
            initialValue: _environment,
            decoration: const InputDecoration(labelText: 'Environment'),
            items: const [
              DropdownMenuItem(
                value: 'development',
                child: Text('Development'),
              ),
              DropdownMenuItem(value: 'staging', child: Text('Staging')),
              DropdownMenuItem(value: 'production', child: Text('Production')),
            ],
            onChanged: _submitting
                ? null
                : (value) =>
                      setState(() => _environment = value ?? _environment),
          ),
          const SizedBox(height: 24),
          AppButton(
            label: 'Generate install command',
            icon: Icons.key_outlined,
            isLoading: _submitting,
            onPressed: _submitting ? null : _submit,
          ),
        ],
      ),
    ),
  );

  Widget _result(ServerEnrollment enrollment) => AppPanel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Row(
          children: [
            Icon(Icons.check_circle, color: AppColors.success),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                'Enrollment command ready',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text('${enrollment.serverName} • ${enrollment.environment}'),
        const SizedBox(height: 4),
        Text(
          'Expires ${enrollment.expiresAt.toLocal()}',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF0B1018),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppColors.border),
          ),
          child: SelectableText(
            enrollment.installCommand,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'This command contains a secret, single-use token. Do not share it. '
          'Install Docker first, then run the command on the target Linux server.',
          style: TextStyle(color: AppColors.warning, fontSize: 12),
        ),
        const SizedBox(height: 20),
        AppButton(
          label: 'Copy command',
          icon: Icons.copy,
          onPressed: _copyCommand,
        ),
        const SizedBox(height: 10),
        AppButton(
          label: 'Done',
          variant: AppButtonVariant.secondary,
          onPressed: () {
            ref.invalidate(serversProvider);
            context.pop();
          },
        ),
      ],
    ),
  );
}
