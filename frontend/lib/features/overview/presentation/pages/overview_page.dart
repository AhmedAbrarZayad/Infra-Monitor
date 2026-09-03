import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/widgets/async_value_view.dart';
import '../providers/overview_providers.dart';
import '../widgets/alerts_section.dart';
import '../widgets/attention_section.dart';
import '../widgets/fleet_status_section.dart';
import '../widgets/incidents_section.dart';
import '../widgets/platform_health_section.dart';

class OverviewPage extends ConsumerWidget {
  const OverviewPage({super.key});

  static const _gap = SizedBox(height: 24);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(overviewDashboardProvider);
    return AsyncValueView(
      value: dashboard,
      data: (data) => RefreshIndicator(
        onRefresh: () => ref.refresh(overviewDashboardProvider.future),
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1180),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 40),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _EnvironmentBar(updatedAt: data.updatedAt),
                        const SizedBox(height: 20),
                        if (data.serverCount == 0) ...[
                          const Center(child: Padding(padding: EdgeInsets.symmetric(vertical: 32), child: Text('No infrastructure connected.'))),
                          const SizedBox(height: 20),
                        ],
                        FleetStatusSection(metrics: data.fleetMetrics),
                        _gap,
                        IncidentsSection(
                          title: 'OPEN CRITICAL',
                          subtitle:
                              '${data.criticalIncidents.length} incidents require immediate action',
                          incidents: data.criticalIncidents,
                          showAll: true,
                        ),
                        _gap,
                        IncidentsSection(
                          title: 'OPEN HIGH',
                          subtitle: '${data.highIncidents.length} incident',
                          incidents: data.highIncidents,
                        ),
                        _gap,
                        AttentionSection(items: data.attentionItems),
                        _gap,
                        AlertsSection(alerts: data.alerts),
                        _gap,
                        PlatformHealthSection(items: data.healthItems),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EnvironmentBar extends StatefulWidget {
  const _EnvironmentBar({required this.updatedAt});

  final String updatedAt;

  @override
  State<_EnvironmentBar> createState() => _EnvironmentBarState();
}

class _EnvironmentBarState extends State<_EnvironmentBar> {
  bool production = true;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: const Color(0xFF111722),
            border: Border.all(color: const Color(0xFF2A3445)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              _tab(
                'Production',
                production,
                () => setState(() => production = true),
              ),
              _tab(
                'Staging',
                !production,
                () => setState(() => production = false),
              ),
            ],
          ),
        ),
        const Spacer(),
        Text(
          'updated ${widget.updatedAt}',
          style: const TextStyle(
            color: Color(0xFF8C95A5),
            fontSize: 10,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }

  Widget _tab(String label, bool selected, VoidCallback onTap) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(9),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: selected ? const Color(0xFF162A48) : null,
        borderRadius: BorderRadius.circular(9),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: selected ? const Color(0xFF5D9DFF) : const Color(0xFF8C95A5),
          fontSize: 10,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
  );
}
