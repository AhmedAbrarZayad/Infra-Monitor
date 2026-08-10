import 'package:flutter/material.dart';

import '../../domain/entities/overview_dashboard.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';
import 'severity_chip.dart';

class AlertsSection extends StatelessWidget {
  const AlertsSection({required this.alerts, super.key});

  final List<AlertItem> alerts;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(title: 'LATEST ALERTS', subtitle: 'streaming feed'),
        const SizedBox(height: 10),
        DashboardPanel(
          padding: EdgeInsets.zero,
          child: Column(
            children: alerts.indexed.map((entry) {
              final (index, alert) = entry;
              return Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            SeverityChip(
                              label: alert.severity.name,
                              severity: alert.severity,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                alert.title,
                                style: const TextStyle(
                                  color: Color(0xFFE4E8EF),
                                  fontWeight: FontWeight.w700,
                                  fontFamily: 'monospace',
                                  fontSize: 11,
                                ),
                              ),
                            ),
                            Text(
                              alert.time,
                              style: const TextStyle(
                                color: Color(0xFF8C95A5),
                                fontFamily: 'monospace',
                                fontSize: 10,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          alert.resource,
                          style: const TextStyle(
                            color: Color(0xFF4C91D8),
                            fontSize: 10,
                            fontFamily: 'monospace',
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          alert.description,
                          style: const TextStyle(
                            color: Color(0xFF8C95A5),
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (index != alerts.length - 1) const Divider(height: 1),
                ],
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
