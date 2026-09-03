import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../auth/presentation/widgets/auth_text_field.dart';
import '../providers/organization_provider.dart';

class CreateOrganizationPage extends ConsumerStatefulWidget {
  const CreateOrganizationPage({super.key});
  @override
  ConsumerState<CreateOrganizationPage> createState() => _CreateOrganizationPageState();
}

class _CreateOrganizationPageState extends ConsumerState<CreateOrganizationPage> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _summary = TextEditingController();
  final _logo = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _name.dispose(); _summary.dispose(); _logo.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting || !_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    final error = await ref.read(organizationContextProvider.notifier).createOrganization(
      name: _name.text.trim(), summary: _summary.text.trim(),
      logoUrl: _logo.text.trim().isEmpty ? null : _logo.text.trim(),
    );
    if (!mounted) return;
    setState(() => _submitting = false);
    if (error != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error), backgroundColor: AppColors.danger));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.background,
    appBar: AppBar(title: const Text('Create organization')),
    body: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 520),
      child: Form(key: _formKey, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        AuthTextField(controller: _name, label: 'Organization name', hint: 'Example Operations',
          validator: (value) => value == null || value.trim().isEmpty ? 'Organization name is required' : null),
        const SizedBox(height: 18),
        AuthTextField(controller: _summary, label: 'Short summary', hint: 'Production infrastructure team',
          validator: (value) => value == null || value.trim().isEmpty ? 'Summary is required' : null),
        const SizedBox(height: 18),
        AuthTextField(controller: _logo, label: 'Logo URL (optional)', hint: 'https://...'),
        const SizedBox(height: 26),
        AppButton(label: 'Create organization', icon: Icons.add_business,
          isLoading: _submitting, onPressed: _submitting ? null : _submit),
        const SizedBox(height: 10),
        TextButton(onPressed: _submitting ? null : () => context.pop(), child: const Text('Cancel')),
      ])),
    ))),
  );
}
