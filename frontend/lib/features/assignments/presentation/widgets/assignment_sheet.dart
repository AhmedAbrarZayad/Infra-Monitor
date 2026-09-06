import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../ai_assistant/presentation/providers/assistant_providers.dart';
import '../../../anomalies/presentation/providers/anomaly_providers.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../incidents/presentation/providers/incidents_providers.dart';
import '../../../organizations/data/organization_models.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../../overview/presentation/providers/overview_providers.dart';
import '../../../servers/presentation/providers/servers_providers.dart';
import '../../domain/assignment_models.dart';
import '../providers/assignment_providers.dart';

Future<void> showWorkAssignmentSheet({
  required BuildContext context,
  required AssignmentResource resource,
  required String resourceId,
  required MembershipUser? currentAssignee,
  String? serverId,
}) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  builder: (_) => WorkAssignmentSheet(
    resource: resource,
    resourceId: resourceId,
    currentAssignee: currentAssignee,
    serverId: serverId,
  ),
);

Future<void> showServiceAdminAssignmentSheet({
  required BuildContext context,
  required String serviceId,
  required String serverId,
}) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  builder: (_) =>
      ServiceAdminAssignmentSheet(serviceId: serviceId, serverId: serverId),
);

class WorkAssignmentSheet extends ConsumerStatefulWidget {
  const WorkAssignmentSheet({
    required this.resource,
    required this.resourceId,
    required this.currentAssignee,
    this.serverId,
    super.key,
  });

  final AssignmentResource resource;
  final String resourceId;
  final MembershipUser? currentAssignee;
  final String? serverId;

  @override
  ConsumerState<WorkAssignmentSheet> createState() =>
      _WorkAssignmentSheetState();
}

class _WorkAssignmentSheetState extends ConsumerState<WorkAssignmentSheet> {
  late MembershipUser? _current = widget.currentAssignee;
  int? _selectedId;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _selectedId = _current?.id;
  }

  Future<void> _save() async {
    final api = ref.read(assignmentsApiProvider);
    if (api == null) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final response = await api.assignWork(
        resource: widget.resource,
        id: widget.resourceId,
        userId: _selectedId,
        expectedUserId: _current?.id,
      );
      if (!mounted) return;
      setState(() {
        _current = assignmentUser(response['assigned_to']);
        _selectedId = _current?.id;
      });
      _refreshRelated();
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.statusCode == 409 &&
          error.body['code'] == 'assignment_changed') {
        setState(() {
          _current = assignmentUser(error.body['assigned_to']);
          _selectedId = _current?.id;
          _error =
              'Assignment changed by another user. The latest value is shown.';
        });
        _refreshRelated();
      } else {
        setState(() => _error = error.message);
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Unable to update assignment.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _refreshRelated() {
    final key = WorkAssignmentKey(widget.resource, widget.resourceId);
    ref.invalidate(workAssignmentHistoryProvider(key));
    ref.invalidate(overviewDashboardProvider);
    if (widget.resource == AssignmentResource.incident) {
      ref.invalidate(incidentsProvider);
    } else {
      if (widget.serverId != null) {
        ref.invalidate(serverAnomaliesProvider(widget.serverId!));
      }
      ref.invalidate(assistantControllerProvider);
    }
  }

  @override
  Widget build(BuildContext context) {
    final organization = ref.watch(organizationContextProvider);
    if (organization is! OrganizationReady) return const SizedBox.shrink();
    final editable = organization.activeMembership.capabilities.canAssignWork;
    final members = editable
        ? ref.watch(
            organizationMembersProvider(
              organization.activeMembership.organization.id,
            ),
          )
        : const AsyncData<List<OrganizationMembership>>([]);
    final history = ref.watch(
      workAssignmentHistoryProvider(
        WorkAssignmentKey(widget.resource, widget.resourceId),
      ),
    );
    return _SheetFrame(
      title: '${widget.resource.name} assignment',
      children: [
        Text('Current Engineer: ${_current?.displayName ?? 'Unassigned'}'),
        const SizedBox(height: 12),
        if (editable)
          members.when(
            loading: () => const LinearProgressIndicator(),
            error: (error, _) => Text('Unable to load Engineers: $error'),
            data: (items) {
              final engineers = items
                  .where((item) => item.approved && item.role == 'ENGINEER')
                  .toList();
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<int?>(
                    key: ValueKey(_current?.id),
                    initialValue: _selectedId,
                    decoration: const InputDecoration(labelText: 'Engineer'),
                    items: [
                      const DropdownMenuItem<int?>(
                        value: null,
                        child: Text('Unassigned'),
                      ),
                      ...engineers.map(
                        (item) => DropdownMenuItem<int?>(
                          value: item.user.id,
                          child: Text(item.user.displayName),
                        ),
                      ),
                    ],
                    onChanged: _saving
                        ? null
                        : (value) => setState(() => _selectedId = value),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _saving || _selectedId == _current?.id
                        ? null
                        : _save,
                    child: Text(_saving ? 'Saving…' : 'Save assignment'),
                  ),
                ],
              );
            },
          )
        else
          const Text('Assignment is read-only for Engineers.'),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(
            _error!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ],
        const SizedBox(height: 20),
        const Text(
          'ASSIGNMENT HISTORY',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        AssignmentTimeline(history: history),
      ],
    );
  }
}

class ServiceAdminAssignmentSheet extends ConsumerStatefulWidget {
  const ServiceAdminAssignmentSheet({
    required this.serviceId,
    required this.serverId,
    super.key,
  });
  final String serviceId;
  final String serverId;

  @override
  ConsumerState<ServiceAdminAssignmentSheet> createState() =>
      _ServiceAdminAssignmentSheetState();
}

class _ServiceAdminAssignmentSheetState
    extends ConsumerState<ServiceAdminAssignmentSheet> {
  Set<String>? _selected;
  bool _saving = false;
  String? _error;

  Future<void> _save() async {
    final api = ref.read(assignmentsApiProvider);
    if (api == null || _selected == null) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await api.replaceServiceAdmins(widget.serviceId, _selected!);
      ref.invalidate(serviceAdminsProvider(widget.serviceId));
      ref.invalidate(serviceAdminHistoryProvider(widget.serviceId));
      ref.invalidate(serverServicesProvider(widget.serverId));
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final organization = ref.watch(organizationContextProvider);
    if (organization is! OrganizationReady) return const SizedBox.shrink();
    final assignments = ref.watch(serviceAdminsProvider(widget.serviceId));
    final members = ref.watch(
      organizationMembersProvider(
        organization.activeMembership.organization.id,
      ),
    );
    final history = ref.watch(serviceAdminHistoryProvider(widget.serviceId));
    return _SheetFrame(
      title: 'Manage service Admins',
      children: [
        assignments.when(
          loading: () => const LinearProgressIndicator(),
          error: (error, _) => Text('Unable to load assignments: $error'),
          data: (current) {
            _selected ??= current.admins.map((item) => item.id).toSet();
            return members.when(
              loading: () => const LinearProgressIndicator(),
              error: (error, _) => Text('Unable to load Admins: $error'),
              data: (items) {
                final admins = items
                    .where((item) => item.approved && item.role == 'ADMIN')
                    .toList();
                return Column(
                  children: [
                    if (admins.isEmpty)
                      const Text('No approved Admins are available.'),
                    ...admins.map(
                      (admin) => CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _selected!.contains(admin.id),
                        title: Text(admin.user.displayName),
                        subtitle: Text(admin.user.email),
                        onChanged: _saving
                            ? null
                            : (selected) => setState(() {
                                if (selected == true) {
                                  _selected!.add(admin.id);
                                } else {
                                  _selected!.remove(admin.id);
                                }
                              }),
                      ),
                    ),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: _saving ? null : _save,
                        child: Text(_saving ? 'Saving…' : 'Save Admins'),
                      ),
                    ),
                  ],
                );
              },
            );
          },
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(
            _error!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ],
        const SizedBox(height: 20),
        const Text(
          'ASSIGNMENT HISTORY',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        AssignmentTimeline(history: history),
      ],
    );
  }
}

class AssignmentTimeline extends StatelessWidget {
  const AssignmentTimeline({required this.history, super.key});
  final AsyncValue<List<AssignmentEvent>> history;

  @override
  Widget build(BuildContext context) => history.when(
    loading: () => const LinearProgressIndicator(),
    error: (error, _) => Text('Unable to load history: $error'),
    data: (events) => events.isEmpty
        ? const Text('No assignment changes recorded.')
        : Column(
            children: events.reversed
                .map((event) {
                  final subject = event.newSubject ?? event.previousSubject;
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      event.action == 'UNASSIGNED'
                          ? Icons.person_remove_outlined
                          : Icons.person_add_alt_outlined,
                    ),
                    title: Text(
                      '${event.action}: ${subject?.displayName ?? 'Legacy/unknown'}',
                    ),
                    subtitle: Text(
                      'By ${event.actor?.displayName ?? 'Legacy/system'} · ${_when(event.createdAt)}',
                    ),
                  );
                })
                .toList(growable: false),
          ),
  );
}

class _SheetFrame extends StatelessWidget {
  const _SheetFrame({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => SafeArea(
    child: DraggableScrollableSheet(
      expand: false,
      initialChildSize: .72,
      maxChildSize: .95,
      builder: (context, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.all(20),
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 18),
          ...children,
        ],
      ),
    ),
  );
}

String _when(DateTime? date) => date == null
    ? 'Unknown time'
    : date.toLocal().toIso8601String().replaceFirst('T', ' ').split('.').first;
