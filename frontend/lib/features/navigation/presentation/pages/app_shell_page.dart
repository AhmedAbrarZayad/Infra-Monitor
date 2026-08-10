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
import '../../../servers/presentation/pages/servers_page.dart';
import '../../../servers/presentation/providers/servers_providers.dart';
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
    final overview = ref.watch(overviewDashboardProvider);
    final overviewSubtitle = overview.when(
      data: (data) =>
          '${data.serverCount} servers  ·  ${data.openIncidentCount} open incidents',
      loading: () => 'loading infrastructure…',
      error: (error, stackTrace) => 'infrastructure unavailable',
    );
    final servers = ref.watch(serversProvider);
    final serversSubtitle = servers.when(
      data: (items) =>
          '${items.length} registered  ·  ${items.where((item) => item.lastSeen.contains('m ago')).length} stale agent',
      loading: () => 'loading servers…',
      error: (error, stackTrace) => 'servers unavailable',
    );
    final incidents = ref.watch(incidentsProvider);
    final incidentsSubtitle = incidents.when(
      data: (items) =>
          '${items.where((item) => item.status != 'RESOLVED').length} open  ·  ${items.where((item) => item.acknowledgement == 'not acknowledged').length} unacknowledged',
      loading: () => 'loading incidents…',
      error: (error, stackTrace) => 'incidents unavailable',
    );
    return Scaffold(
      appBar: CustomAppBar(
        title: _titles[_selectedIndex],
        subtitle: switch (_selectedIndex) {
          0 => overviewSubtitle,
          1 => serversSubtitle,
          2 => incidentsSubtitle,
          3 => 'advisory  ·  grounded in telemetry',
          4 => 'window 24h  ·  6 servers',
          5 => 'account  ·  preferences  ·  audit',
          _ => null,
        },
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final content = IndexedStack(index: _selectedIndex, children: _pages);
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
