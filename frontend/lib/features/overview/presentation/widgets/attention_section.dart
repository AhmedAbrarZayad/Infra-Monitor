import 'package:flutter/material.dart';

import '../../domain/entities/overview_dashboard.dart';
import '../../../anomalies/domain/entities/anomaly_detection.dart';
import '../../../anomalies/presentation/widgets/anomaly_evidence_tile.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';

class AttentionSection extends StatelessWidget {
  const AttentionSection({
    required this.items,
    required this.anomalies,
    super.key,
  });

  final List<AttentionItem> items;
  final List<AnomalyDetection> anomalies;

  Color _color(Severity? severity) => switch (severity) {
    Severity.critical => const Color(0xFFFF4057),
    Severity.high || Severity.warning => const Color(0xFFFFB51F),
    Severity.info => const Color(0xFF3BB8FF),
    null => const Color(0xFF8C95A5),
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(
          title: 'NEEDS ATTENTION',
          subtitle: 'resource pressure and ML anomaly evidence',
        ),
        const SizedBox(height: 10),
        DashboardPanel(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              ...items.indexed.map((entry) {
                final (index, item) = entry;
                return Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 11,
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item.label,
                                  style: const TextStyle(
                                    color: Color(0xFF8892A4),
                                    fontSize: 9,
                                    fontFamily: 'monospace',
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  item.resource,
                                  style: const TextStyle(
                                    color: Color(0xFFE4E8EF),
                                    fontWeight: FontWeight.w700,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Text(
                            item.value,
                            style: TextStyle(
                              color: _color(item.severity),
                              fontWeight: FontWeight.w700,
                              fontFamily: 'monospace',
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (index != items.length - 1 || anomalies.isNotEmpty)
                      const Divider(height: 1),
                  ],
                );
              }),
              ...anomalies.indexed.map(
                (entry) => Column(
                  children: [
                    AnomalyEvidenceTile(anomaly: entry.$2),
                    if (entry.$1 != anomalies.length - 1)
                      const Divider(height: 1),
                  ],
                ),
              ),
              if (items.isEmpty && anomalies.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(14),
                  child: Text('No resources currently need attention.'),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
