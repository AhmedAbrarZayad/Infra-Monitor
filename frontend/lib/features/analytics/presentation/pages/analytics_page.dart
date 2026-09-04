import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../domain/entities/analytics_dashboard.dart';
import '../providers/analytics_providers.dart';
import '../widgets/metric_chart.dart';

class AnalyticsPage extends ConsumerWidget {
  const AnalyticsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => AsyncValueView(
    value: ref.watch(analyticsProvider),
    data: (data) => ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1100),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'ALL AVAILABLE HISTORY',
                  style: TextStyle(color: Color(0xFF8993A4), fontSize: 10),
                ),
                const SizedBox(height: 24),
                const SectionTitle('OPERATIONAL METRICS'),
                const SizedBox(height: 10),
                _metricGrid(data.metrics),
                const SizedBox(height: 24),
                const SectionTitle(
                  'RESOURCE TRENDS',
                  subtitle: 'fleet average',
                ),
                const SizedBox(height: 10),
                _chartPanel(
                  'CPU utilization',
                  data.cpu,
                  const Color(0xFF539CFF),
                ),
                const SizedBox(height: 10),
                _chartPanel(
                  'Memory usage',
                  data.memory,
                  const Color(0xFFFFB51F),
                ),
                const SizedBox(height: 10),
                _chartPanel(
                  'API latency',
                  data.latency,
                  const Color(0xFFFF4057),
                ),
                const SizedBox(height: 24),
                const SectionTitle('INCIDENT TRENDS'),
                const SizedBox(height: 10),
                _chartPanel(
                  'Incident frequency',
                  data.frequency,
                  const Color(0xFFFF4057),
                  type: MetricChartType.bars,
                ),
                const SizedBox(height: 10),
                _chartPanel(
                  'Open vs resolved',
                  data.opened,
                  const Color(0xFFFF4057),
                  secondary: data.resolved,
                ),
                const SizedBox(height: 10),
                _chartPanel(
                  'Server uptime (last 7d, %)',
                  data.uptime,
                  const Color(0xFF47C879),
                  type: MetricChartType.bars,
                  footer:
                      'baseline 99.80% · bars show basis points above baseline',
                ),
                const SizedBox(height: 24),
                const SectionTitle('MOST COMMON CATEGORIES'),
                const SizedBox(height: 10),
                _rankPanel(data.categories, false),
                const SizedBox(height: 24),
                const SectionTitle('TOP AFFECTED SERVERS'),
                const SizedBox(height: 10),
                _rankPanel(data.servers, true),
                const SizedBox(height: 24),
                const SectionTitle('INSIGHTS'),
                const SizedBox(height: 10),
                ...data.insights.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppPanel(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 11,
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.lightbulb_outline,
                            color: Color(0xFFFFB51F),
                            size: 16,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              item,
                              style: const TextStyle(
                                color: Color(0xFF929CAD),
                                fontSize: 10,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 30),
              ],
            ),
          ),
        ),
      ],
    ),
  );

  Widget _metricGrid(List<AnalyticsMetric> items) => LayoutBuilder(
    builder: (context, c) {
      final columns = c.maxWidth > 700 ? 4 : 2;
      const gap = 8.0;
      final width = (c.maxWidth - gap * (columns - 1)) / columns;
      return Wrap(
        spacing: gap,
        runSpacing: gap,
        children: items
            .map(
              (m) => SizedBox(
                width: width,
                height: 104,
                child: AppPanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        m.label,
                        style: const TextStyle(
                          color: Color(0xFF8993A4),
                          fontSize: 9,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        m.value,
                        style: const TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                        ),
                      ),
                      Text(
                        m.change,
                        style: const TextStyle(
                          color: Color(0xFF8993A4),
                          fontSize: 9,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )
            .toList(),
      );
    },
  );
  Widget _chartPanel(
    String title,
    List<double> values,
    Color color, {
    List<double>? secondary,
    MetricChartType type = MetricChartType.line,
    String? footer,
  }) => AppPanel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 140,
          child: MetricChart(
            values: values,
            color: color,
            secondary: secondary,
            secondaryColor: const Color(0xFF47C879),
            type: type,
          ),
        ),
        if (footer != null) ...[
          const SizedBox(height: 12),
          Text(
            footer,
            style: const TextStyle(
              color: Color(0xFF8993A4),
              fontSize: 9,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ],
    ),
  );
  Widget _rankPanel(Map<String, int> items, bool alerts) {
    if (items.isEmpty) {
      return const AppPanel(child: Text('No analytics data available yet.'));
    }
    final max = items.values.reduce((a, b) => a > b ? a : b);
    return AppPanel(
      child: Column(
        children: items.entries.indexed.map((pair) {
          final (i, e) = pair;
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            e.key,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        Text(
                          alerts ? '${e.value} alerts' : '${e.value}',
                          style: TextStyle(
                            color: alerts
                                ? const Color(0xFFFFB51F)
                                : Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                    if (!alerts) ...[
                      const SizedBox(height: 6),
                      LinearProgressIndicator(
                        value: e.value / max,
                        minHeight: 4,
                        color: const Color(0xFF579CFF),
                        backgroundColor: const Color(0xFF202838),
                      ),
                    ],
                  ],
                ),
              ),
              if (alerts && i != items.length - 1) const Divider(height: 1),
            ],
          );
        }).toList(),
      ),
    );
  }
}
