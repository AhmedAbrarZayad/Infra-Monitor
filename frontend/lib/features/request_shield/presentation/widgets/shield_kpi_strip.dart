import 'package:flutter/material.dart';

import '../../../../shared/colors/colors.dart';
import '../../domain/entities/shield_entities.dart';

/// Horizontal row of shield KPI tiles — total requests, zone counts,
/// pending suggestions, and shield status.
class ShieldKpiStrip extends StatelessWidget {
  const ShieldKpiStrip({required this.analytics, super.key});

  final ShieldAnalytics analytics;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _KpiTile(
            label: 'TOTAL',
            value: '${analytics.totalRequests}',
            icon: Icons.http_rounded,
            color: AppColors.info,
          ),
          _KpiTile(
            label: 'SAFE',
            value: '${analytics.greenCount}',
            icon: Icons.check_circle_outline_rounded,
            color: const Color(0xFF20C997),
          ),
          _KpiTile(
            label: 'SUSPICIOUS',
            value: '${analytics.grayCount}',
            icon: Icons.help_outline_rounded,
            color: const Color(0xFFF59E0B),
          ),
          _KpiTile(
            label: 'MALICIOUS',
            value: '${analytics.redCount}',
            icon: Icons.dangerous_outlined,
            color: const Color(0xFFEF4444),
          ),
          _KpiTile(
            label: 'ALERTS',
            value: '${analytics.pendingSuggestions}',
            icon: Icons.notifications_active_outlined,
            color: analytics.pendingSuggestions > 0
                ? const Color(0xFFF59E0B)
                : AppColors.textMuted,
          ),
          _KpiTile(
            label: 'SHIELD',
            value: analytics.shieldEnabled ? 'ON' : 'OFF',
            icon: analytics.shieldEnabled
                ? Icons.shield_rounded
                : Icons.shield_outlined,
            color: analytics.shieldEnabled
                ? const Color(0xFF20C997)
                : const Color(0xFFEF4444),
          ),
        ],
      ),
    );
  }
}

class _KpiTile extends StatelessWidget {
  const _KpiTile({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 108,
      margin: const EdgeInsets.only(right: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF111722),
        border: Border.all(color: color.withValues(alpha: 0.2)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const Spacer(),
              Text(
                label,
                style: TextStyle(
                  color: color.withValues(alpha: 0.7),
                  fontSize: 8,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}
