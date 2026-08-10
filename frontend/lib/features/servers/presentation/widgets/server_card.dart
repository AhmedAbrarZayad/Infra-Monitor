import 'package:flutter/material.dart';

import '../../domain/entities/server.dart';
import '../../../overview/presentation/widgets/dashboard_panel.dart';
import 'server_status_badge.dart';
import 'sparkline.dart';

class ServerCard extends StatelessWidget {
  const ServerCard({required this.server, super.key});

  final Server server;

  Color _metricColor(int value) {
    if (value >= 90) return const Color(0xFFFF4057);
    if (value >= 70) return const Color(0xFFFFB51F);
    return const Color(0xFF35D17C);
  }

  @override
  Widget build(BuildContext context) {
    final trendColor = server.status == ServerStatus.critical
        ? const Color(0xFFFF4057)
        : const Color(0xFFFFB51F);
    return DashboardPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  server.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFE6EAF1),
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  SizedBox(
                    width: 80,
                    height: 28,
                    child: Sparkline(
                      values: server.cpuHistory,
                      color: trendColor,
                    ),
                  ),
                  const Text(
                    'cpu 1h',
                    style: TextStyle(
                      color: Color(0xFF808A9B),
                      fontSize: 8,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 7,
            runSpacing: 6,
            children: [
              ServerStatusBadge(status: server.status),
              _SmallBadge(label: server.environment),
              if (server.alertCount > 0)
                _SmallBadge(label: '△ ${server.alertCount}', danger: true),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _Metric(
                  label: 'CPU',
                  value: server.cpu,
                  color: _metricColor(server.cpu),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _Metric(
                  label: 'MEM',
                  value: server.memory,
                  color: _metricColor(server.memory),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _Metric(
                  label: 'DISK',
                  value: server.disk,
                  color: _metricColor(server.disk),
                ),
              ),
            ],
          ),
          const SizedBox(height: 11),
          Row(
            children: [
              Expanded(
                child: Text(
                  'agent seen ${server.lastSeen}',
                  style: const TextStyle(
                    color: Color(0xFF8993A4),
                    fontSize: 9,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
              Text(
                'uptime ${server.uptime}  ›',
                style: const TextStyle(
                  color: Color(0xFF8993A4),
                  fontSize: 9,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SmallBadge extends StatelessWidget {
  const _SmallBadge({required this.label, this.danger = false});
  final String label;
  final bool danger;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
    decoration: BoxDecoration(
      color: danger ? const Color(0xFF4C1721) : const Color(0xFF242B38),
      border: Border.all(
        color: danger ? const Color(0xFF853040) : const Color(0xFF343D4D),
      ),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      label,
      style: TextStyle(
        color: danger ? const Color(0xFFFF4057) : const Color(0xFF929CAD),
        fontSize: 9,
        fontWeight: FontWeight.w600,
      ),
    ),
  );
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.label,
    required this.value,
    required this.color,
  });
  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Row(
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF929CAD),
              fontSize: 9,
              fontFamily: 'monospace',
            ),
          ),
          const Spacer(),
          Text(
            '$value%',
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontFamily: 'monospace',
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
      const SizedBox(height: 6),
      ClipRRect(
        borderRadius: BorderRadius.circular(3),
        child: LinearProgressIndicator(
          value: value / 100,
          minHeight: 4,
          color: color,
          backgroundColor: const Color(0xFF202838),
        ),
      ),
    ],
  );
}
