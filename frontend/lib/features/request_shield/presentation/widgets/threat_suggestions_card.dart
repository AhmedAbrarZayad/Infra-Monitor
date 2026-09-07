import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../domain/entities/shield_entities.dart';
import '../providers/shield_providers.dart';

/// Shows pending threat suggestions with accept / dismiss actions.
class ThreatSuggestionsCard extends ConsumerWidget {
  const ThreatSuggestionsCard({required this.suggestions, super.key});

  final List<ThreatSuggestion> suggestions;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle(
          'THREAT SUGGESTIONS',
          subtitle: '${suggestions.length} pending review',
        ),
        const SizedBox(height: 12),
        if (suggestions.isEmpty)
          const AppPanel(
            child: Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Column(
                  children: [
                    Icon(Icons.verified_user_outlined,
                        color: Color(0xFF20C997), size: 28),
                    SizedBox(height: 8),
                    Text(
                      'No pending threats',
                      style:
                          TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
          )
        else
          ...suggestions
              .map((s) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _SuggestionTile(suggestion: s),
                  ))
              .toList(),
      ],
    );
  }
}

class _SuggestionTile extends ConsumerWidget {
  const _SuggestionTile({required this.suggestion});

  final ThreatSuggestion suggestion;

  Color _zoneColor(String zone) => switch (zone) {
        'RED' => const Color(0xFFEF4444),
        _ => const Color(0xFFF59E0B),
      };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zoneColor = _zoneColor(suggestion.triggerZone);

    return AppPanel(
      borderColor: zoneColor.withValues(alpha: 0.3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: zoneColor, size: 18),
              const SizedBox(width: 8),
              Text(
                suggestion.ipAddress,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'monospace',
                ),
              ),
              const Spacer(),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: zoneColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                  border:
                      Border.all(color: zoneColor.withValues(alpha: 0.3)),
                ),
                child: Text(
                  '${suggestion.requestCount} ${suggestion.triggerZone} hits',
                  style: TextStyle(
                    color: zoneColor,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (suggestion.topThreatSignals.isNotEmpty) ...[
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: suggestion.topThreatSignals
                  .map(
                    (signal) => Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: Text(
                        signal.replaceAll('_', ' '),
                        style: TextStyle(
                          color: zoneColor,
                          fontSize: 9,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 8),
          ],
          if (suggestion.samplePaths.isNotEmpty) ...[
            Text(
              'Sample paths:',
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 9,
              ),
            ),
            const SizedBox(height: 2),
            ...suggestion.samplePaths.take(3).map(
                  (path) => Text(
                    path,
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            const SizedBox(height: 10),
          ],
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              _ActionButton(
                label: 'Dismiss',
                icon: Icons.check_circle_outline,
                color: const Color(0xFF20C997),
                onTap: () => resolveSuggestion(
                  ref,
                  suggestionId: suggestion.id,
                  action: 'dismiss',
                ),
              ),
              const SizedBox(width: 8),
              _ActionButton(
                label: 'Acknowledge Threat',
                icon: Icons.shield_outlined,
                color: const Color(0xFFEF4444),
                onTap: () => resolveSuggestion(
                  ref,
                  suggestionId: suggestion.id,
                  action: 'accept',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
