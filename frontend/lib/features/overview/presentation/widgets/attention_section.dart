import 'package:flutter/material.dart';

import '../../../anomalies/domain/entities/anomaly_detection.dart';
import '../../../anomalies/presentation/widgets/anomaly_evidence_tile.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';

class AttentionSection extends StatelessWidget {
  const AttentionSection({required this.anomalies, super.key});

  final List<AnomalyDetection> anomalies;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(
          title: 'NEEDS ATTENTION',
          subtitle: 'services flagged by ML anomaly detection',
        ),
        const SizedBox(height: 10),
        DashboardPanel(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              ...anomalies.indexed.map(
                (entry) => Column(
                  children: [
                    AnomalyEvidenceTile(anomaly: entry.$2),
                    if (entry.$1 != anomalies.length - 1)
                      const Divider(height: 1),
                  ],
                ),
              ),
              if (anomalies.isEmpty)
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
