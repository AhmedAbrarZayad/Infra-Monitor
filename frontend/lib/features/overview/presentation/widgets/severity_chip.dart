import 'package:flutter/material.dart';

import '../../domain/entities/overview_dashboard.dart';

class SeverityChip extends StatelessWidget {
  const SeverityChip({required this.label, required this.severity, super.key});

  final String label;
  final Severity severity;

  Color get _color => switch (severity) {
    Severity.critical => const Color(0xFFFF4057),
    Severity.high || Severity.warning => const Color(0xFFFFB51F),
    Severity.info => const Color(0xFF3BB8FF),
  };

  @override
  Widget build(BuildContext context) {
    final color = _color;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        border: Border.all(color: color.withValues(alpha: .55)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: .4,
        ),
      ),
    );
  }
}
