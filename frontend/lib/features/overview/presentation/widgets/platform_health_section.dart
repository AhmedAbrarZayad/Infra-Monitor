import 'package:flutter/material.dart';

import '../../domain/entities/overview_dashboard.dart';
import 'dashboard_panel.dart';
import 'section_header.dart';

class PlatformHealthSection extends StatelessWidget {
  const PlatformHealthSection({required this.items, super.key});

  final List<HealthItem> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionHeader(
          title: 'PLATFORM HEALTH',
          subtitle: 'ingestion & backend',
        ),
        const SizedBox(height: 10),
        DashboardPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ...items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 13),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: item.isHealthy
                                ? const Color(0xFF39C879)
                                : const Color(0xFFFFB51F),
                            boxShadow: item.isHealthy
                                ? [
                                    BoxShadow(
                                      color: const Color(
                                        0xFF39C879,
                                      ).withValues(alpha: .35),
                                      blurRadius: 5,
                                    ),
                                  ]
                                : null,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.title,
                              style: const TextStyle(
                                color: Color(0xFFE4E8EF),
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Text(
                              item.value,
                              style: const TextStyle(
                                color: Color(0xFF9AA3B2),
                                fontSize: 10,
                                fontFamily: 'monospace',
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              item.detail,
                              style: const TextStyle(
                                color: Color(0xFF6F798B),
                                fontSize: 9,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const Divider(),
              const SizedBox(height: 8),
              const Text(
                '⌁ websocket stream connected',
                style: TextStyle(
                  color: Color(0xFF35D17C),
                  fontSize: 10,
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
