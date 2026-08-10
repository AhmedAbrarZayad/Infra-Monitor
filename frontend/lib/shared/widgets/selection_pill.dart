import 'package:flutter/material.dart';

class SelectionPill extends StatelessWidget {
  const SelectionPill({
    required this.label,
    required this.selected,
    required this.onTap,
    super.key,
  });
  final String label;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(20),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
      decoration: BoxDecoration(
        color: selected ? const Color(0xFF142C50) : const Color(0xFF0E1420),
        border: Border.all(
          color: selected ? const Color(0xFF3A82E4) : const Color(0xFF2A3445),
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: selected ? const Color(0xFF64A4FF) : const Color(0xFFA4AEC0),
          fontSize: 11,
        ),
      ),
    ),
  );
}
