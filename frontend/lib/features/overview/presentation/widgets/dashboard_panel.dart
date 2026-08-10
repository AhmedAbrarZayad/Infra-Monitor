import 'package:flutter/material.dart';

class DashboardPanel extends StatelessWidget {
  const DashboardPanel({
    required this.child,
    this.borderColor,
    this.padding = const EdgeInsets.all(14),
    super.key,
  });

  final Widget child;
  final Color? borderColor;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: const Color(0xFF111722),
        border: Border.all(color: borderColor ?? const Color(0xFF2A3445)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: child,
    );
  }
}
