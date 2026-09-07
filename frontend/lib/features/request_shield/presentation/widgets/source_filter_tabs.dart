import 'package:flutter/material.dart';

import '../../../../shared/colors/colors.dart';

/// Segmented tab bar for switching between External / Platform / All sources.
class SourceFilterTabs extends StatelessWidget {
  const SourceFilterTabs({
    required this.selected,
    required this.onChanged,
    super.key,
  });

  final String? selected;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _Tab(
          label: 'All',
          isActive: selected == null,
          icon: Icons.layers_outlined,
          onTap: () => onChanged(null),
        ),
        const SizedBox(width: 6),
        _Tab(
          label: 'External',
          isActive: selected == 'EXTERNAL',
          icon: Icons.dns_outlined,
          onTap: () => onChanged('EXTERNAL'),
        ),
        const SizedBox(width: 6),
        _Tab(
          label: 'Platform',
          isActive: selected == 'PLATFORM',
          icon: Icons.shield_outlined,
          onTap: () => onChanged('PLATFORM'),
        ),
      ],
    );
  }
}

class _Tab extends StatelessWidget {
  const _Tab({
    required this.label,
    required this.isActive,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final bool isActive;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.primary.withValues(alpha: 0.15)
              : const Color(0xFF111722),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isActive
                ? AppColors.primary.withValues(alpha: 0.5)
                : const Color(0xFF2A3445),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 13,
              color:
                  isActive ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color:
                    isActive ? AppColors.primary : AppColors.textSecondary,
                fontSize: 11,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
