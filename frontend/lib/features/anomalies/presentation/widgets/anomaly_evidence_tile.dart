import 'package:flutter/material.dart';

import '../../../../core/api/operational_api.dart';
import '../../domain/entities/anomaly_detection.dart';

const _warning = Color(0xFFFFB51F);
const _muted = Color(0xFF8993A4);

class AnomalyEvidenceTile extends StatelessWidget {
  const AnomalyEvidenceTile({required this.anomaly, super.key});

  final AnomalyDetection anomaly;

  @override
  Widget build(BuildContext context) => ExpansionTile(
    tilePadding: const EdgeInsets.symmetric(horizontal: 14),
    childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
    leading: const Icon(Icons.warning_amber_rounded, color: _warning),
    title: Text(
      anomaly.displayService,
      style: const TextStyle(fontWeight: FontWeight.w700),
    ),
    subtitle: Text(
      '${anomaly.displayServer}\nUnusual service behaviour; crash not confirmed.',
      style: const TextStyle(color: _muted, fontSize: 11),
    ),
    trailing: Text(
      '${(anomaly.confidenceScore * 100).clamp(0, 100).round()}%',
      style: const TextStyle(
        color: _warning,
        fontWeight: FontWeight.w700,
        fontFamily: 'monospace',
      ),
    ),
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: Wrap(
          spacing: 20,
          runSpacing: 12,
          children: [
            _Detail('DETECTED', relativeTime(anomaly.detectedAt)),
            _Detail('WINDOW START', _timestamp(anomaly.windowStartedAt)),
            _Detail('WINDOW END', _timestamp(anomaly.windowEndedAt)),
            _Detail('ANOMALY SCORE', anomaly.anomalyScore.toStringAsFixed(4)),
            _Detail('MODEL', anomaly.modelVersion),
            ..._features.entries.map(
              (entry) => _Detail(
                entry.value.$1,
                _feature(anomaly.featureValues[entry.key], entry.value.$2),
              ),
            ),
          ],
        ),
      ),
    ],
  );
}

const _features = <String, (String, String)>{
  'cpu_r': ('CPU', '%'),
  'mem_u': ('MEMORY', '%'),
  'disk_r': ('DISK READ', 'B/s'),
  'disk_w': ('DISK WRITE', 'B/s'),
  'eth1_fi': ('NETWORK IN', 'B/s'),
  'eth1_fo': ('NETWORK OUT', 'B/s'),
};

class _Detail extends StatelessWidget {
  const _Detail(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(color: _muted, fontSize: 9)),
      const SizedBox(height: 3),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
    ],
  );
}

String _feature(double? value, String unit) =>
    value == null ? 'No data' : '${value.toStringAsFixed(2)} $unit';

String _timestamp(DateTime? value) =>
    value == null ? 'Unknown' : value.toLocal().toIso8601String();
