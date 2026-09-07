import 'package:flutter/material.dart';

import '../../../../shared/colors/colors.dart';
import '../../../../shared/widgets/app_panel.dart';
import '../../../../shared/widgets/section_title.dart';
import '../../domain/entities/shield_entities.dart';

/// Individual request log entry list with zone badges, threat signals,
/// and expandable details.
class RequestLogList extends StatelessWidget {
  const RequestLogList({required this.logs, this.onVerdict, super.key});

  final List<RequestLogEntry> logs;
  final void Function(String logId, String verdict)? onVerdict;

  @override
  Widget build(BuildContext context) {
    if (logs.isEmpty) {
      return const AppPanel(
        child: Center(
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 32),
            child: Text(
              'No request logs matching filters',
              style: TextStyle(color: AppColors.textMuted, fontSize: 12),
            ),
          ),
        ),
      );
    }

    return Column(
      children: logs.map((log) => _RequestLogTile(log: log, onVerdict: onVerdict)).toList(),
    );
  }
}

class _RequestLogTile extends StatelessWidget {
  const _RequestLogTile({required this.log, this.onVerdict});

  final RequestLogEntry log;
  final void Function(String logId, String verdict)? onVerdict;

  Color _zoneColor(String zone) => switch (zone) {
        'GREEN' => const Color(0xFF20C997),
        'GRAY' => const Color(0xFFF59E0B),
        'RED' => const Color(0xFFEF4444),
        _ => const Color(0xFF4B5563),
      };

  Color _zoneBgColor(String zone) => switch (zone) {
        'GREEN' => const Color(0xFF0D3325),
        'GRAY' => const Color(0xFF3B2F11),
        'RED' => const Color(0xFF3B1111),
        _ => const Color(0xFF1E293B),
      };

  String _zoneLabel(String zone) => switch (zone) {
        'GREEN' => 'SAFE',
        'GRAY' => 'SUSPICIOUS',
        'RED' => 'MALICIOUS',
        _ => 'PENDING',
      };

  IconData _methodIcon(String method) => switch (method.toUpperCase()) {
        'GET' => Icons.arrow_downward_rounded,
        'POST' => Icons.arrow_upward_rounded,
        'PUT' => Icons.swap_vert_rounded,
        'DELETE' => Icons.delete_outline_rounded,
        _ => Icons.http_rounded,
      };

  String _timeAgo(String timestamp) {
    final dt = DateTime.tryParse(timestamp)?.toLocal();
    if (dt == null) return timestamp;
    final diff = DateTime.now().difference(dt);
    if (diff.inDays > 0) return '${diff.inDays}d ago';
    if (diff.inHours > 0) return '${diff.inHours}h ago';
    if (diff.inMinutes > 0) return '${diff.inMinutes}m ago';
    return '${diff.inSeconds.clamp(0, 59)}s ago';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: AppPanel(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        borderColor: _zoneColor(log.zone).withValues(alpha: 0.2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _methodIcon(log.method),
                  size: 14,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 6),
                Text(
                  log.method,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    log.path,
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                      fontFamily: 'monospace',
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: _zoneBgColor(log.zone),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: _zoneColor(log.zone).withValues(alpha: 0.3),
                    ),
                  ),
                  child: Text(
                    _zoneLabel(log.zone),
                    style: TextStyle(
                      color: _zoneColor(log.zone),
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Text(
                  log.sourceIp,
                  style: const TextStyle(
                    color: AppColors.info,
                    fontSize: 10,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(width: 12),
                if (log.statusCode != null)
                  Text(
                    '${log.statusCode}',
                    style: TextStyle(
                      color: (log.statusCode! >= 400)
                          ? const Color(0xFFEF4444)
                          : AppColors.textMuted,
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                  ),
                const SizedBox(width: 12),
                Icon(
                  log.source == 'PLATFORM'
                      ? Icons.shield_outlined
                      : Icons.dns_outlined,
                  size: 11,
                  color: AppColors.textMuted,
                ),
                const SizedBox(width: 4),
                Text(
                  log.source == 'PLATFORM' ? 'Platform' : 'External',
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                  ),
                ),
                const Spacer(),
                Text(
                  _timeAgo(log.timestamp),
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
            if (log.threatSignals.isNotEmpty) ...[
              const SizedBox(height: 6),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: log.threatSignals
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
                          style: const TextStyle(
                            color: Color(0xFFD4A017),
                            fontSize: 9,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
            if (log.confidence != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  Text(
                    'Confidence: ${(log.confidence! * 100).toStringAsFixed(1)}%',
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 9,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'by ${log.classifiedBy.replaceAll("_", " ").toLowerCase()}',
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 9,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
