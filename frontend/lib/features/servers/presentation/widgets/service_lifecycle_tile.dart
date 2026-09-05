import 'package:flutter/material.dart';

import '../../../../core/api/operational_api.dart';
import '../../domain/entities/server.dart';
import 'server_status_badge.dart';

class ServiceLifecycleTile extends StatelessWidget {
  const ServiceLifecycleTile({required this.service, super.key});

  final MonitoredService service;

  @override
  Widget build(BuildContext context) {
    final collectorUnavailable =
        service.lifecycleReason == 'collector_unavailable';
    final reasonColor = collectorUnavailable
        ? const Color(0xFFFFB51F)
        : const Color(0xFF8993A4);
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      childrenPadding: const EdgeInsets.only(bottom: 14),
      title: Row(
        children: [
          Expanded(
            child: Text(
              service.displayName.isEmpty ? service.name : service.displayName,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          ServerStatusBadge(status: service.status),
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Row(
          children: [
            if (collectorUnavailable) ...[
              const Icon(
                Icons.warning_amber_rounded,
                size: 15,
                color: Color(0xFFFFB51F),
              ),
              const SizedBox(width: 5),
            ],
            Expanded(
              child: Text(
                serviceLifecycleMessage(service.lifecycleReason),
                style: TextStyle(color: reasonColor, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Wrap(
            spacing: 20,
            runSpacing: 12,
            children: [
              _Detail('LAST REPORTED', relativeTime(service.lastReportedAt)),
              _Detail('STATUS CHANGED', relativeTime(service.statusChangedAt)),
              _Detail('PORT', service.port?.toString() ?? 'Unknown'),
              _Detail('ACTIVE ALERTS', '${service.alertCount}'),
              _Detail('CPU', _reading(service.metrics['cpu_r'])),
              _Detail('MEMORY', _reading(service.metrics['mem_u'])),
              if (service.consecutiveFailureObservations == 1)
                const _Detail(
                  'FAILED CHECKS',
                  '1 of 2 - awaiting confirmation',
                ),
            ],
          ),
        ),
      ],
    );
  }
}

String serviceLifecycleMessage(String reason) => switch (reason) {
  'application_unreachable' => 'Application health checks failed.',
  'service_telemetry_timeout' => 'Service stopped reporting.',
  'service_telemetry_delayed' => 'Service telemetry is delayed.',
  'collector_unavailable' =>
    'Collector unavailable; service crash is unconfirmed.',
  'monitoring_disconnected' => 'Monitoring is disconnected.',
  'monitoring_not_configured' => 'Monitoring is not configured.',
  'telemetry_received' => 'Service telemetry is being received.',
  'application_up' => 'Application health checks are passing.',
  'awaiting_telemetry' => 'Waiting for the first service telemetry.',
  _ => 'Service lifecycle state is unknown.',
};

class _Detail extends StatelessWidget {
  const _Detail(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(color: Color(0xFF8993A4), fontSize: 9),
      ),
      const SizedBox(height: 3),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
    ],
  );
}

String _reading(MetricReading? reading) {
  if (reading == null) return 'No data';
  final value = reading.value.abs() >= 1000
      ? reading.value.toStringAsFixed(0)
      : reading.value.toStringAsFixed(reading.value.abs() < 10 ? 2 : 1);
  final unit = switch (reading.unit) {
    'percent' => '%',
    'bytes_per_second' => 'B/s',
    _ => reading.unit,
  };
  return '$value $unit';
}
