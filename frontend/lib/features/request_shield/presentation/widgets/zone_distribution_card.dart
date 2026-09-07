import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../domain/entities/shield_entities.dart';

/// Donut chart showing GREEN / GRAY / RED zone distribution with
/// animated arcs and a center summary.
class ZoneDistributionCard extends StatelessWidget {
  const ZoneDistributionCard({required this.analytics, super.key});

  final ShieldAnalytics analytics;

  static const _green = Color(0xFF20C997);
  static const _gray = Color(0xFFF59E0B);
  static const _red = Color(0xFFEF4444);
  static const _unclassified = Color(0xFF4B5563);

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('ZONE DISTRIBUTION', subtitle: 'last 24 hours'),
          const SizedBox(height: 16),
          SizedBox(
            height: 160,
            child: Row(
              children: [
                Expanded(
                  child: CustomPaint(
                    painter: _DonutPainter(
                      green: analytics.greenCount,
                      gray: analytics.grayCount,
                      red: analytics.redCount,
                      unclassified: analytics.unclassifiedCount,
                    ),
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '${analytics.totalRequests}',
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const Text(
                            'total',
                            style: TextStyle(
                              fontSize: 10,
                              color: AppColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 20),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _LegendItem(
                      color: _green,
                      label: 'Safe',
                      count: analytics.greenCount,
                      percent: analytics.greenPercent,
                    ),
                    const SizedBox(height: 10),
                    _LegendItem(
                      color: _gray,
                      label: 'Suspicious',
                      count: analytics.grayCount,
                      percent: analytics.grayPercent,
                    ),
                    const SizedBox(height: 10),
                    _LegendItem(
                      color: _red,
                      label: 'Malicious',
                      count: analytics.redCount,
                      percent: analytics.redPercent,
                    ),
                    if (analytics.unclassifiedCount > 0) ...[
                      const SizedBox(height: 10),
                      _LegendItem(
                        color: _unclassified,
                        label: 'Pending',
                        count: analytics.unclassifiedCount,
                        percent: analytics.totalRequests > 0
                            ? analytics.unclassifiedCount /
                                analytics.totalRequests *
                                100
                            : 0,
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({
    required this.color,
    required this.label,
    required this.count,
    required this.percent,
  });

  final Color color;
  final String label;
  final int count;
  final double percent;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$count $label',
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '${percent.toStringAsFixed(1)}%',
              style: const TextStyle(
                color: AppColors.textMuted,
                fontSize: 10,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _DonutPainter extends CustomPainter {
  _DonutPainter({
    required this.green,
    required this.gray,
    required this.red,
    required this.unclassified,
  });

  final int green;
  final int gray;
  final int red;
  final int unclassified;

  @override
  void paint(Canvas canvas, Size size) {
    final total = green + gray + red + unclassified;
    if (total == 0) {
      final paint = Paint()
        ..color = const Color(0xFF2A3445)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 20
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCenter(
          center: size.center(Offset.zero),
          width: size.shortestSide - 24,
          height: size.shortestSide - 24,
        ),
        0,
        2 * math.pi,
        false,
        paint,
      );
      return;
    }

    final rect = Rect.fromCenter(
      center: size.center(Offset.zero),
      width: size.shortestSide - 24,
      height: size.shortestSide - 24,
    );

    const gap = 0.04;
    final segments = <_Segment>[
      if (green > 0) _Segment(const Color(0xFF20C997), green / total),
      if (gray > 0) _Segment(const Color(0xFFF59E0B), gray / total),
      if (red > 0) _Segment(const Color(0xFFEF4444), red / total),
      if (unclassified > 0)
        _Segment(const Color(0xFF4B5563), unclassified / total),
    ];

    var startAngle = -math.pi / 2;
    for (final seg in segments) {
      final sweep = seg.fraction * 2 * math.pi - gap;
      if (sweep <= 0) continue;
      final paint = Paint()
        ..color = seg.color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 20
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(rect, startAngle, sweep, false, paint);
      startAngle += seg.fraction * 2 * math.pi;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter old) =>
      old.green != green ||
      old.gray != gray ||
      old.red != red ||
      old.unclassified != unclassified;
}

class _Segment {
  const _Segment(this.color, this.fraction);
  final Color color;
  final double fraction;
}
