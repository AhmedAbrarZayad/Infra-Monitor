import 'package:flutter/material.dart';

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.title, {this.subtitle, super.key});
  final String title;
  final String? subtitle;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: const TextStyle(
          color: Color(0xFFA7B8DC),
          fontSize: 13,
          letterSpacing: 1.5,
          fontWeight: FontWeight.w700,
        ),
      ),
      if (subtitle != null) ...[
        const SizedBox(height: 3),
        Text(
          subtitle!,
          style: const TextStyle(
            color: Color(0xFF6880AC),
            fontSize: 9,
            fontFamily: 'monospace',
          ),
        ),
      ],
    ],
  );
}
