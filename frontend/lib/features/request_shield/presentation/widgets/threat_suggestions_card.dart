import 'package:flutter/material.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../domain/entities/shield_entities.dart';

/// Shows pending threat suggestions.
class ThreatSuggestionsCard extends StatelessWidget {
  const ThreatSuggestionsCard({required this.suggestions, super.key});

  final List<ThreatSuggestion> suggestions;

  @override
  Widget build(BuildContext context) {
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
                    Icon(
                      Icons.verified_user_outlined,
                      color: Color(0xFF20C997),
                      size: 28,
                    ),
                    SizedBox(height: 8),
                    Text(
                      'No pending threats',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
        else
          ...suggestions.map(
            (s) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _SuggestionTile(suggestion: s),
            ),
          ),
      ],
    );
  }
}

class _SuggestionTile extends StatelessWidget {
  const _SuggestionTile({required this.suggestion});

  final ThreatSuggestion suggestion;

  Color _zoneColor(String zone) => switch (zone) {
    'RED' => const Color(0xFFEF4444),
    _ => const Color(0xFFF59E0B),
  };

  @override
  Widget build(BuildContext context) {
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
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: zoneColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: zoneColor.withValues(alpha: 0.3)),
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
                        horizontal: 6,
                        vertical: 2,
                      ),
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
              style: TextStyle(color: AppColors.textMuted, fontSize: 9),
            ),
            const SizedBox(height: 2),
            ...suggestion.samplePaths
                .take(3)
                .map(
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
        ],
      ),
    );
  }
}
