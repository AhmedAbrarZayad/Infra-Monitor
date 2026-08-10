import 'package:flutter/material.dart';

import '../../domain/entities/overview_dashboard.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';
import 'severity_chip.dart';

class IncidentsSection extends StatelessWidget {
  const IncidentsSection({
    required this.title,
    required this.subtitle,
    required this.incidents,
    this.showAll = false,
    super.key,
  });

  final String title;
  final String subtitle;
  final List<IncidentSummary> incidents;
  final bool showAll;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: title,
          subtitle: subtitle,
          action: showAll
              ? const Text(
                  'all ↗',
                  style: TextStyle(
                    color: Color(0xFF4C91FF),
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                )
              : null,
        ),
        const SizedBox(height: 10),
        ...incidents.map(
          (incident) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _IncidentCard(incident: incident),
          ),
        ),
      ],
    );
  }
}

class _IncidentCard extends StatelessWidget {
  const _IncidentCard({required this.incident});

  final IncidentSummary incident;

  @override
  Widget build(BuildContext context) {
    final critical = incident.severity == Severity.critical;
    return DashboardPanel(
      borderColor: critical ? const Color(0xFF6B2835) : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SeverityChip(
                label: incident.severity.name,
                severity: incident.severity,
              ),
              const SizedBox(width: 7),
              SeverityChip(
                label: incident.status,
                severity: incident.status == 'NEW'
                    ? Severity.critical
                    : Severity.info,
              ),
              const Spacer(),
              Text(
                incident.id,
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
            incident.title,
            style: const TextStyle(
              color: Color(0xFFE8EBF1),
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '▰ ${incident.server}  ·  ${incident.service}  ·  ${incident.environment}',
            style: const TextStyle(
              color: Color(0xFF8892A4),
              fontSize: 10,
              fontFamily: 'monospace',
            ),
          ),
          const SizedBox(height: 9),
          Wrap(
            spacing: 14,
            runSpacing: 7,
            children: [
              Text(
                '◷ ${incident.age}',
                style: const TextStyle(
                  color: Color(0xFF8C95A5),
                  fontSize: 10,
                  fontFamily: 'monospace',
                ),
              ),
              Text(
                '♙ ${incident.owner}',
                style: const TextStyle(
                  color: Color(0xFF8C95A5),
                  fontSize: 10,
                  fontFamily: 'monospace',
                ),
              ),
              if (incident.aiNote != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFF382856),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '✣ ${incident.aiNote}',
                    style: const TextStyle(
                      color: Color(0xFFC9A8FF),
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
            ],
          ),
          if (incident.footer != null) ...[
            const SizedBox(height: 10),
            Text(
              incident.footer!,
              style: const TextStyle(
                color: Color(0xFF697487),
                fontSize: 9,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ],
      ),
    );
  }
}
