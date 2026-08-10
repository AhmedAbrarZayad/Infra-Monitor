import 'package:flutter/material.dart';

class ServerFilterChip extends StatelessWidget {
  const ServerFilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF122B50) : const Color(0xFF111722),
          border: Border.all(
            color: selected ? const Color(0xFF327CE1) : const Color(0xFF2A3445),
          ),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? const Color(0xFF62A2FF) : const Color(0xFF9BA6B9),
            fontSize: 11,
            fontFamily: 'monospace',
          ),
        ),
      ),
    );
  }
}
