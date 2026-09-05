import 'package:flutter/material.dart';

import '../../domain/entities/server.dart';

class ServerStatusBadge extends StatelessWidget {
  const ServerStatusBadge({required this.status, super.key});

  final ServerStatus status;

  Color get color => switch (status) {
    ServerStatus.critical => const Color(0xFFFF4057),
    ServerStatus.warning => const Color(0xFFFFB51F),
    ServerStatus.healthy => const Color(0xFF35D17C),
    ServerStatus.stale => const Color(0xFFFFB51F),
    ServerStatus.offline => const Color(0xFF8993A4),
    ServerStatus.unknown => const Color(0xFF3BB8FF),
  };

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        border: Border.all(color: color.withValues(alpha: .5)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 5),
          Text(
            status.name.toUpperCase(),
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
