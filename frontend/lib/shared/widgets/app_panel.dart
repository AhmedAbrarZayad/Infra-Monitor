import 'package:flutter/material.dart';

class AppPanel extends StatelessWidget {
  const AppPanel({
    required this.child,
    this.padding = const EdgeInsets.all(14),
    this.borderColor,
    super.key,
  });
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;
  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    decoration: BoxDecoration(
      color: const Color(0xFF111722),
      border: Border.all(color: borderColor ?? const Color(0xFF2A3445)),
      borderRadius: BorderRadius.circular(12),
    ),
    child: child,
  );
}
