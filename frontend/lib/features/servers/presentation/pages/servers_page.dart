import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../shared/widgets/async_value_view.dart';
import '../../domain/entities/server.dart';
import '../providers/servers_providers.dart';
import '../widgets/server_card.dart';
import '../widgets/server_filter_chip.dart';

class ServersPage extends ConsumerStatefulWidget {
  const ServersPage({super.key});

  @override
  ConsumerState<ServersPage> createState() => _ServersPageState();
}

class _ServersPageState extends ConsumerState<ServersPage> {
  final _searchController = TextEditingController();
  ServerStatus? _status;
  String _environment = 'All envs';
  bool _highUsageOnly = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final servers = ref.watch(serversProvider);
    return AsyncValueView(
      value: servers,
      data: (allServers) {
        final query = _searchController.text.toLowerCase().trim();
        final filtered = allServers.where((server) {
          final matchesSearch =
              query.isEmpty || server.name.toLowerCase().contains(query);
          final matchesStatus = _status == null || server.status == _status;
          final matchesEnvironment =
              _environment == 'All envs' || server.environment == _environment;
          final matchesUsage =
              !_highUsageOnly ||
              (server.cpu?.value ?? 0) > 70 ||
              (server.memory?.value ?? 0) > 70 ||
              (server.disk?.value ?? 0) > 70;
          return matchesSearch &&
              matchesStatus &&
              matchesEnvironment &&
              matchesUsage;
        }).toList();

        return RefreshIndicator(
          onRefresh: () => ref.refresh(serversProvider.future),
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1180),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(9, 16, 9, 10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          TextField(
                            controller: _searchController,
                            onChanged: (_) => setState(() {}),
                            style: const TextStyle(
                              fontSize: 12,
                              fontFamily: 'monospace',
                            ),
                            decoration: InputDecoration(
                              hintText: 'search server name or host…',
                              hintStyle: const TextStyle(
                                color: Color(0xFF71809A),
                                fontSize: 12,
                                fontFamily: 'monospace',
                              ),
                              prefixIcon: const Icon(
                                Icons.search,
                                size: 20,
                                color: Color(0xFF8993A4),
                              ),
                              filled: true,
                              fillColor: const Color(0xFF0E1420),
                              contentPadding: const EdgeInsets.symmetric(
                                vertical: 11,
                              ),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                                borderSide: const BorderSide(
                                  color: Color(0xFF2A3445),
                                ),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                                borderSide: const BorderSide(
                                  color: Color(0xFF2A3445),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                          _statusFilters(allServers),
                          const SizedBox(height: 8),
                          _environmentFilters(),
                          const SizedBox(height: 22),
                          const Text(
                            'MONITORED SERVERS',
                            style: TextStyle(
                              color: Color(0xFFA7B8DC),
                              fontSize: 13,
                              letterSpacing: 1.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            '${filtered.length} match current filters',
                            style: const TextStyle(
                              color: Color(0xFF6880AC),
                              fontSize: 9,
                              fontFamily: 'monospace',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(9, 0, 9, 40),
                sliver: SliverLayoutBuilder(
                  builder: (context, constraints) {
                    final columns = constraints.crossAxisExtent >= 1000 ? 2 : 1;
                    return SliverGrid.builder(
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: columns,
                        mainAxisExtent: 164,
                        crossAxisSpacing: 10,
                        mainAxisSpacing: 10,
                      ),
                      itemCount: filtered.length,
                      itemBuilder: (context, index) => ServerCard(
                        server: filtered[index],
                        onTap: () =>
                            context.push('/servers/${filtered[index].id}'),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _statusFilters(List<Server> servers) {
    int count(ServerStatus status) =>
        servers.where((server) => server.status == status).length;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          ServerFilterChip(
            label: 'all ${servers.length}',
            selected: _status == null,
            onTap: () => setState(() => _status = null),
          ),
          const SizedBox(width: 8),
          for (final status in [
            ServerStatus.critical,
            ServerStatus.warning,
            ServerStatus.healthy,
            ServerStatus.offline,
            ServerStatus.unknown,
          ]) ...[
            ServerFilterChip(
              label: '${status.name} ${count(status)}',
              selected: _status == status,
              onTap: () => setState(() => _status = status),
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }

  Widget _environmentFilters() => SingleChildScrollView(
    scrollDirection: Axis.horizontal,
    child: Row(
      children: [
        for (final environment in ['All envs', 'Production', 'Staging']) ...[
          ServerFilterChip(
            label: environment,
            selected: _environment == environment,
            onTap: () => setState(() => _environment = environment),
          ),
          const SizedBox(width: 8),
        ],
        ServerFilterChip(
          label: 'Usage > 70%',
          selected: _highUsageOnly,
          onTap: () => setState(() => _highUsageOnly = !_highUsageOnly),
        ),
      ],
    ),
  );
}
