import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/components/appbar/app_bar.dart';
import '../../../ai_assistant/presentation/pages/ai_assistant_page.dart';
import '../../../analytics/presentation/pages/analytics_page.dart';
import '../../../incidents/presentation/pages/incidents_page.dart';
import '../../../incidents/presentation/providers/incidents_providers.dart';
import '../../../more/presentation/pages/more_page.dart';
import '../../../overview/presentation/pages/overview_page.dart';
import '../../../overview/presentation/providers/overview_providers.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../../servers/presentation/pages/servers_page.dart';
import '../../../servers/presentation/providers/servers_providers.dart';
import '../../../servers/domain/entities/server.dart';
import '../widgets/app_bottom_navigation.dart';

class AppShellPage extends ConsumerStatefulWidget {
  const AppShellPage({super.key});

  @override
  ConsumerState<AppShellPage> createState() => _AppShellPageState();
}

class _AppShellPageState extends ConsumerState<AppShellPage> {
  int _selectedIndex = 0;

  static const _titles = [
    'Overview',
    'Servers',
    'Incidents',
    'AI',
    'Analytics',
    'More',
  ];
  static const _pages = <Widget>[
    OverviewPage(),
    ServersPage(),
    IncidentsPage(),
    AiAssistantPage(),
    AnalyticsPage(),
    MorePage(),
  ];

  @override
  Widget build(BuildContext context) {
    final organizationState = ref.watch(organizationContextProvider);
    final role = organizationState is OrganizationReady
        ? organizationState.activeMembership.displayRole
        : '';
    final subtitle = switch (_selectedIndex) {
      0 =>
        ref
            .watch(overviewDashboardProvider)
            .when(
              data: (data) =>
                  '${data.serverCount} servers · ${data.openIncidentCount} open incidents',
              loading: () => 'loading infrastructure…',
              error: (_, _) => 'infrastructure unavailable',
            ),
      1 =>
        ref
            .watch(serversProvider)
            .when(
              data: (items) =>
                  '${items.length} registered · ${items.where((item) => item.status == ServerStatus.healthy).length} healthy',
              loading: () => 'loading servers…',
              error: (_, _) => 'servers unavailable',
            ),
      2 =>
        ref
            .watch(incidentsProvider)
            .when(
              data: (items) =>
                  '${items.where((item) => item.status != 'RESOLVED').length} open · ${items.where((item) => item.acknowledgement == 'not acknowledged').length} unacknowledged',
              loading: () => 'loading incidents…',
              error: (_, _) => 'incidents unavailable',
            ),
      3 => 'advisory · grounded in telemetry',
      4 => 'operational summary',
      5 => 'account · preferences · audit',
      _ => null,
    };
    return Scaffold(
      appBar: CustomAppBar(
        title: _titles[_selectedIndex],
        role: role,
        subtitle: subtitle,
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final content = _pages[_selectedIndex];
          if (constraints.maxWidth < 900) return content;
          return Row(
            children: [
              NavigationRail(
                selectedIndex: _selectedIndex,
                onDestinationSelected: (index) =>
                    setState(() => _selectedIndex = index),
                labelType: NavigationRailLabelType.all,
                destinations: AppBottomNavigation.destinations
                    .map(
                      (item) => NavigationRailDestination(
                        icon: item.icon,
                        selectedIcon: item.selectedIcon,
                        label: Text(item.label),
                      ),
                    )
                    .toList(),
              ),
              const VerticalDivider(width: 1),
              Expanded(child: content),
            ],
          );
        },
      ),
      bottomNavigationBar: MediaQuery.sizeOf(context).width < 900
          ? AppBottomNavigation(
              currentIndex: _selectedIndex,
              onDestinationSelected: (index) =>
                  setState(() => _selectedIndex = index),
            )
          : null,
    );
  }
}
