import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../data/organization_models.dart';
import '../providers/organization_provider.dart';

class JoinOrganizationPage extends ConsumerStatefulWidget {
  const JoinOrganizationPage({super.key});
  @override
  ConsumerState<JoinOrganizationPage> createState() => _JoinOrganizationPageState();
}

class _JoinOrganizationPageState extends ConsumerState<JoinOrganizationPage> {
  final _query = TextEditingController();
  List<Organization> _results = const [];
  bool _searching = false;
  String? _error;
  String? _joiningId;
  int _offset = 0;
  bool _hasMore = false;

  @override
  void dispose() { _query.dispose(); super.dispose(); }

  Future<void> _search({bool append = false}) async {
    if (_searching) return;
    setState(() { _searching = true; _error = null; });
    try {
      final repository = ref.read(organizationRepositoryProvider);
      if (repository == null) throw StateError('Session unavailable');
      final page = await repository.search(_query.text.trim(), offset: append ? _offset : 0);
      if (!mounted) return;
      setState(() {
        _results = append ? [..._results, ...page.results] : page.results;
        _offset = _results.length;
        _hasMore = page.next != null;
      });
    } catch (_) {
      if (mounted) setState(() => _error = 'Unable to search organizations. Please try again.');
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<void> _join(Organization organization) async {
    if (_joiningId != null) return;
    setState(() => _joiningId = organization.id);
    final error = await ref.read(organizationContextProvider.notifier).requestToJoin(organization.id);
    if (!mounted) return;
    setState(() => _joiningId = null);
    if (error != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error), backgroundColor: AppColors.danger));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.background,
    appBar: AppBar(title: const Text('Join organization')),
    body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 760), child: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Row(children: [
          Expanded(child: TextField(controller: _query, textInputAction: TextInputAction.search,
            onSubmitted: (_) => _search(), decoration: const InputDecoration(labelText: 'Search organizations', prefixIcon: Icon(Icons.search)))),
          const SizedBox(width: 10),
          AppButton(label: 'Search', onPressed: _searching ? null : () => _search()),
        ]),
        if (_searching) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
        if (_error != null) Padding(padding: const EdgeInsets.all(20), child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.danger))),
        if (!_searching && _error == null && _results.isEmpty)
          const Padding(padding: EdgeInsets.all(32), child: Text('Search by organization name or summary.', textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary))),
        ..._results.map((organization) => Padding(padding: const EdgeInsets.only(top: 12), child: AppPanel(child: Row(children: [
          CircleAvatar(child: Text(organization.name.substring(0, 1).toUpperCase())),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(organization.name, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4), Text(organization.summary, style: const TextStyle(color: AppColors.textSecondary)),
          ])),
          const SizedBox(width: 10),
          AppButton(label: 'Request to join', isLoading: _joiningId == organization.id,
            onPressed: _joiningId == null ? () => _join(organization) : null),
        ])))),
        if (_hasMore) Padding(padding: const EdgeInsets.only(top: 16), child: AppButton(label: 'Load more', variant: AppButtonVariant.secondary, onPressed: _searching ? null : () => _search(append: true))),
      ],
    ))),
  );
}
