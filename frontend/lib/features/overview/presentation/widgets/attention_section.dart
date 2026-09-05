import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../anomalies/domain/entities/anomaly_detection.dart';
import '../../../anomalies/presentation/widgets/anomaly_evidence_tile.dart';
import '../providers/overview_providers.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';

class AttentionSection extends ConsumerStatefulWidget {
  const AttentionSection({required this.anomalies, super.key});

  final List<AnomalyDetection> anomalies;

  @override
  ConsumerState<AttentionSection> createState() => _AttentionSectionState();
}

class _AttentionSectionState extends ConsumerState<AttentionSection> {
  String? _resolvingId;

  Future<void> _resolve(AnomalyDetection anomaly) async {
    setState(() => _resolvingId = anomaly.id);
    try {
      await resolveAnomaly(ref, anomaly.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${anomaly.displayService} marked resolved.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Unable to resolve the anomaly. Try again.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _resolvingId = null);
    }
  }

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
              ...widget.anomalies.indexed.map(
                (entry) => Column(
                  children: [
                    AnomalyEvidenceTile(
                      anomaly: entry.$2,
                      resolving: _resolvingId == entry.$2.id,
                      onResolve: () => _resolve(entry.$2),
                    ),
                    if (entry.$1 != widget.anomalies.length - 1)
                      const Divider(height: 1),
                  ],
                ),
              ),
              if (widget.anomalies.isEmpty)
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
