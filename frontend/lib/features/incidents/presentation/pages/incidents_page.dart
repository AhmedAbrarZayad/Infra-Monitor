import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../shared/widgets/app_button.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../../../shared/widgets/selection_pill.dart';
import '../../domain/entities/incident.dart';
import '../providers/incidents_providers.dart';
import '../../../assignments/domain/assignment_models.dart';
import '../../../assignments/presentation/widgets/assignment_sheet.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';

class IncidentsPage extends ConsumerStatefulWidget {
  const IncidentsPage({super.key});
  @override
  ConsumerState<IncidentsPage> createState() => _IncidentsPageState();
}

class _IncidentsPageState extends ConsumerState<IncidentsPage> {
  String filter = 'All';
  String query = '';
  @override
  Widget build(BuildContext context) => AsyncValueView(
    value: ref.watch(incidentsProvider),
    data: (items) {
      final visible = items
          .where(
            (item) =>
                (filter == 'All' ||
                    item.severity == filter.toUpperCase() ||
                    item.status == filter.toUpperCase()) &&
                (query.isEmpty ||
                    '${item.title} ${item.server} ${item.id}'
                        .toLowerCase()
                        .contains(query)),
          )
          .toList();
      return CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1100),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        onChanged: (value) =>
                            setState(() => query = value.toLowerCase()),
                        decoration: InputDecoration(
                          prefixIcon: const Icon(Icons.search),
                          hintText: 'search title, server or INC id…',
                          filled: true,
                          fillColor: const Color(0xFF0E1420),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children:
                              [
                                    'All',
                                    'Critical',
                                    'High',
                                    'Warning',
                                    'Info',
                                    'Open',
                                    'Acknowledged',
                                  ]
                                  .map(
                                    (name) => Padding(
                                      padding: const EdgeInsets.only(right: 8),
                                      child: SelectionPill(
                                        label: name,
                                        selected: filter == name,
                                        onTap: () =>
                                            setState(() => filter = name),
                                      ),
                                    ),
                                  )
                                  .toList(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(
                            child: AppButton(
                              label: 'Acknowledge all critical',
                              onPressed:
                                  visible.any(
                                    (item) =>
                                        item.severity == 'CRITICAL' &&
                                        item.status == 'NEW',
                                  )
                                  ? () => ref
                                        .read(incidentActionsProvider)
                                        .acknowledgeCritical(
                                          visible
                                              .where(
                                                (item) =>
                                                    item.severity ==
                                                        'CRITICAL' &&
                                                    item.status == 'NEW',
                                              )
                                              .map((item) => item.apiId!)
                                              .toList(),
                                        )
                                  : null,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      SectionTitle(
                        'INCIDENT QUEUE',
                        subtitle:
                            '${visible.length} incidents · sorted by detection time',
                      ),
                      const SizedBox(height: 10),
                      if (visible.isEmpty)
                        const AppPanel(
                          child: Text(
                            'No incidents found for this organization.',
                          ),
                        ),
                      ...visible.map(
                        (item) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _IncidentCard(item),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      );
    },
  );
}

class _IncidentCard extends ConsumerWidget {
  const _IncidentCard(this.item);
  final Incident item;
  Color get color => item.severity == 'CRITICAL'
      ? const Color(0xFFFF4057)
      : item.severity == 'HIGH' || item.severity == 'WARNING'
      ? const Color(0xFFFFB51F)
      : const Color(0xFF3BB8FF);
  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPanel(
    borderColor: item.severity == 'CRITICAL' ? const Color(0xFF682936) : null,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _tag(item.severity, color),
            const SizedBox(width: 7),
            _tag(
              item.status,
              item.status == 'NEW'
                  ? const Color(0xFFFF4057)
                  : const Color(0xFF4A9AFF),
            ),
            const Spacer(),
            Text(
              item.id,
              style: const TextStyle(
                color: Color(0xFF8C95A5),
                fontSize: 10,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          item.title,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        ),
        const SizedBox(height: 10),
        Builder(
          builder: (context) {
            final organization = ref.watch(organizationContextProvider);
            final editable =
                organization is OrganizationReady &&
                organization.activeMembership.capabilities.canAssignWork;
            return AppButton(
              label: editable
                  ? (item.assignedTo == null
                        ? 'Assign Engineer'
                        : 'Reassign Engineer')
                  : 'View assignment',
              variant: AppButtonVariant.secondary,
              onPressed: item.apiId == null
                  ? null
                  : () => showWorkAssignmentSheet(
                      context: context,
                      resource: AssignmentResource.incident,
                      resourceId: item.apiId!,
                      currentAssignee: item.assignedTo,
                    ),
            );
          },
        ),
        const SizedBox(height: 8),
        Text(
          '▰ ${item.server}  ·  ${item.service}  ·  ${item.environment}',
          style: const TextStyle(
            color: Color(0xFF8993A4),
            fontSize: 10,
            fontFamily: 'monospace',
          ),
        ),
        const SizedBox(height: 9),
        Wrap(
          spacing: 14,
          runSpacing: 7,
          children: [
            Text('◷ ${item.age}', style: _meta),
            Text('♙ ${item.owner}', style: _meta),
            _tag('✣ ${item.aiConfidence}', const Color(0xFFC08DFF)),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          item.acknowledgement,
          style: const TextStyle(
            color: Color(0xFF697487),
            fontSize: 9,
            fontFamily: 'monospace',
          ),
        ),
      ],
    ),
  );
  static const _meta = TextStyle(
    color: Color(0xFF8993A4),
    fontSize: 10,
    fontFamily: 'monospace',
  );
  Widget _tag(String text, Color shade) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
    decoration: BoxDecoration(
      color: shade.withValues(alpha: .12),
      border: Border.all(color: shade.withValues(alpha: .55)),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      text,
      style: TextStyle(color: shade, fontSize: 9, fontWeight: FontWeight.w700),
    ),
  );
}
