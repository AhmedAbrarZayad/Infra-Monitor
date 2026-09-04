import 'package:flutter/material.dart';

import '../../domain/entities/overview_dashboard.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';

class FleetStatusSection extends StatelessWidget {
  const FleetStatusSection({required this.metrics, super.key});

  final List<FleetMetric> metrics;

  Color _valueColor(FleetMetric metric) => switch (metric.tone) {
    Severity.critical => const Color(0xFFFF4057),
    Severity.warning || Severity.high => const Color(0xFFFFB51F),
    Severity.info => const Color(0xFF3BB8FF),
    null =>
      metric.label == 'HEALTHY'
          ? const Color(0xFF35D17C)
          : const Color(0xFFDDE3EE),
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(
          title: 'FLEET STATUS',
          subtitle: 'status counts across selected environment',
        ),
        const SizedBox(height: 10),
        LayoutBuilder(
          builder: (context, constraints) {
            final columns = constraints.maxWidth >= 850 ? 6 : 3;
            const gap = 8.0;
            final width =
                (constraints.maxWidth - gap * (columns - 1)) / columns;
            return Wrap(
              spacing: gap,
              runSpacing: gap,
              children: metrics
                  .map(
                    (metric) => SizedBox(
                      width: width,
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 90),
                        child: DashboardPanel(
                          padding: const EdgeInsets.all(11),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                metric.label,
                                style: const TextStyle(
                                  color: Color(0xFF8993A4),
                                  fontSize: 10,
                                  fontFamily: 'monospace',
                                ),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                metric.value,
                                style: TextStyle(
                                  color: _valueColor(metric),
                                  fontSize: 21,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(),
                              Text(
                                metric.caption,
                                style: const TextStyle(
                                  color: Color(0xFF8C95A5),
                                  fontSize: 10,
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            );
          },
        ),
      ],
    );
  }
}
