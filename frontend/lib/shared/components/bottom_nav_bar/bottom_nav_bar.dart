import 'package:flutter/material.dart';
import 'package:frontend/data/app_bar_titles.dart';
import 'package:frontend/shared/colors/colors.dart';

typedef OnNavTap = void Function(int index);

class BottomNavBar extends StatelessWidget {
  final int currentIndex;
  final OnNavTap onTap;
  const BottomNavBar({super.key, required this.currentIndex, required this.onTap});

  static const List<IconData> _icons = [
    Icons.home,
    Icons.storage,
    Icons.warning_amber_rounded,
    Icons.auto_awesome,
    Icons.bar_chart,
    Icons.more_horiz,
  ];

  @override
  Widget build(BuildContext context) {
    final items = List<BottomNavigationBarItem>.generate(APP_BAR_TITLES.length, (i) {
      return BottomNavigationBarItem(icon: Icon(_icons[i], size: 20), label: APP_BAR_TITLES[i]);
    });

    return BottomNavigationBar(
      type: BottomNavigationBarType.fixed,
      items: items,
      currentIndex: currentIndex,
      onTap: onTap,
      backgroundColor: AppColors.surface,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.textSecondary,
    );
  }
}
