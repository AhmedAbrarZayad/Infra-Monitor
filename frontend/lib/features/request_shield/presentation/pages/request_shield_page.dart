import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/async_value_view.dart';
import '../../../../shared/widgets/section_title.dart';
import '../providers/shield_providers.dart';
import '../widgets/request_log_list.dart';
import '../widgets/shield_kpi_strip.dart';
import '../widgets/source_filter_tabs.dart';
import '../widgets/threat_suggestions_card.dart';
import '../widgets/top_offending_ips_card.dart';
import '../widgets/zone_distribution_card.dart';

/// Main Request Shield dashboard page.
///
/// Shows a unified analytics overview with KPI strip, zone distribution,
/// top offending IPs, threat suggestions, and a filtered request log list.
/// The source filter tabs allow switching between External (monitored servers)
/// and Platform (self-monitoring) views.
class RequestShieldPage extends ConsumerWidget {
  const RequestShieldPage({super.key});

  static const _gap = SizedBox(height: 20);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final source = ref.watch(shieldSourceFilterProvider);
    final analytics = ref.watch(shieldAnalyticsProvider(source));
    final suggestions = ref.watch(shieldSuggestionsProvider);
    final logs = ref.watch(shieldRequestLogsProvider(
      source != null ? {'source': source} : {},
    ));

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(shieldAnalyticsProvider);
        ref.invalidate(shieldSuggestionsProvider);
        ref.invalidate(shieldRequestLogsProvider);
      },
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1180),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 40),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // ── Header bar ───────────────────────────────
                      Row(
                        children: [
                          const Icon(Icons.shield_rounded,
                              color: Color(0xFF5D9DFF), size: 18),
                          const SizedBox(width: 8),
                          const Text(
                            'REQUEST SHIELD',
                            style: TextStyle(
                              color: Color(0xFF5D9DFF),
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.5,
                            ),
                          ),
                          const Spacer(),
                          const Text(
                            'AI-POWERED THREAT MONITORING',
                            style: TextStyle(
                              color: Color(0xFF8C95A5),
                              fontSize: 10,
                              fontFamily: 'monospace',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // ── Source filter ─────────────────────────────
                      SourceFilterTabs(
                        selected: source,
                        onChanged: (value) => ref
                            .read(shieldSourceFilterProvider.notifier)
                            .state = value,
                      ),
                      _gap,

                      // ── Analytics section ────────────────────────
                      AsyncValueView(
                        value: analytics,
                        data: (data) => Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            ShieldKpiStrip(analytics: data),
                            _gap,
                            LayoutBuilder(
                              builder: (context, constraints) {
                                if (constraints.maxWidth >= 700) {
                                  return Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                        child: ZoneDistributionCard(
                                            analytics: data),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: TopOffendingIpsCard(
                                            ips: data.topOffendingIps),
                                      ),
                                    ],
                                  );
                                }
                                return Column(
                                  children: [
                                    ZoneDistributionCard(analytics: data),
                                    const SizedBox(height: 12),
                                    TopOffendingIpsCard(
                                        ips: data.topOffendingIps),
                                  ],
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                      _gap,

                      // ── Threat suggestions ───────────────────────
                      AsyncValueView(
                        value: suggestions,
                        data: (data) =>
                            ThreatSuggestionsCard(suggestions: data),
                      ),
                      _gap,

                      // ── Request log list ─────────────────────────
                      const SectionTitle(
                        'RECENT REQUESTS',
                        subtitle: 'latest classified entries',
                      ),
                      const SizedBox(height: 12),
                      _ZoneFilterChips(),
                      const SizedBox(height: 10),
                      AsyncValueView(
                        value: logs,
                        data: (data) => RequestLogList(logs: data),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Zone filter chips ────────────────────────────────────────────

final _zoneFilterProvider = StateProvider<String?>((ref) => null);

class _ZoneFilterChips extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(_zoneFilterProvider);
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _chip(ref, null, 'All', Icons.layers_outlined, selected),
          _chip(ref, 'RED', 'Malicious', Icons.dangerous_outlined, selected),
          _chip(ref, 'GRAY', 'Suspicious', Icons.help_outline_rounded, selected),
          _chip(ref, 'GREEN', 'Safe', Icons.check_circle_outline_rounded, selected),
          _chip(ref, 'UNCLASSIFIED', 'Pending', Icons.hourglass_empty_rounded,
              selected),
        ],
      ),
    );
  }

  Widget _chip(WidgetRef ref, String? zone, String label, IconData icon,
      String? selected) {
    final isActive = zone == selected;
    final color = switch (zone) {
      'RED' => const Color(0xFFEF4444),
      'GRAY' => const Color(0xFFF59E0B),
      'GREEN' => const Color(0xFF20C997),
      _ => AppColors.textSecondary,
    };
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: GestureDetector(
        onTap: () {
          ref.read(_zoneFilterProvider.notifier).state = zone;
          // Rebuild logs with new zone filter
          final source = ref.read(shieldSourceFilterProvider);
          final filters = <String, String>{};
          if (source != null) filters['source'] = source;
          if (zone != null) filters['zone'] = zone;
          ref.invalidate(shieldRequestLogsProvider);
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: isActive
                ? color.withValues(alpha: 0.15)
                : const Color(0xFF111722),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: isActive
                  ? color.withValues(alpha: 0.4)
                  : const Color(0xFF2A3445),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 12, color: isActive ? color : AppColors.textMuted),
              const SizedBox(width: 4),
              Text(
                label,
                style: TextStyle(
                  color: isActive ? color : AppColors.textMuted,
                  fontSize: 10,
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
