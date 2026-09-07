import 'package:flutter/material.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../domain/entities/shield_entities.dart';

/// Table showing the top offending IPs with RED and GRAY hit counts.
class TopOffendingIpsCard extends StatelessWidget {
  const TopOffendingIpsCard({required this.ips, super.key});

  final List<OffendingIp> ips;

  @override
  Widget build(BuildContext context) {
    return AppPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle(
            'TOP OFFENDING IPS',
            subtitle: 'highest threat activity in last 24h',
          ),
          const SizedBox(height: 12),
          if (ips.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text(
                  'No flagged IPs in this window',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                ),
              ),
            )
          else
            ...ips.map((ip) => _IpRow(ip: ip)),
        ],
      ),
    );
  }
}

class _IpRow extends StatelessWidget {
  const _IpRow({required this.ip});

  final OffendingIp ip;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: ip.redCount > 0
                  ? const Color(0xFFEF4444)
                  : const Color(0xFFF59E0B),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              ip.ip,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 12,
                fontFamily: 'monospace',
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          _CountBadge(
            count: ip.redCount,
            color: const Color(0xFFEF4444),
            bgColor: const Color(0xFF3B1111),
          ),
          const SizedBox(width: 6),
          _CountBadge(
            count: ip.grayCount,
            color: const Color(0xFFF59E0B),
            bgColor: const Color(0xFF3B2F11),
          ),
          const SizedBox(width: 10),
          Text(
            '${ip.total}',
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 11,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  const _CountBadge({
    required this.count,
    required this.color,
    required this.bgColor,
  });

  final int count;
  final Color color;
  final Color bgColor;

  @override
  Widget build(BuildContext context) {
    if (count == 0) return const SizedBox(width: 32);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '$count',
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          fontFamily: 'monospace',
        ),
      ),
    );
  }
}
