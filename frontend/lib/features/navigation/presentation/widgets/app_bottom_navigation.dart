import 'package:flutter/material.dart';

class AppBottomNavigation extends StatelessWidget {
  const AppBottomNavigation({
    required this.currentIndex,
    required this.onDestinationSelected,
    super.key,
  });

  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;

  static const destinations = <NavigationDestination>[
    NavigationDestination(icon: Icon(Icons.home_rounded), label: 'Overview'),
    NavigationDestination(icon: Icon(Icons.storage_rounded), label: 'Servers'),
    NavigationDestination(
      icon: Icon(Icons.warning_amber_rounded),
      label: 'Incidents',
    ),
    NavigationDestination(icon: Icon(Icons.auto_awesome), label: 'AI'),
    NavigationDestination(icon: Icon(Icons.more_horiz), label: 'More'),
  ];

  @override
  Widget build(BuildContext context) {
    return NavigationBar(
      selectedIndex: currentIndex,
      onDestinationSelected: onDestinationSelected,
      destinations: destinations,
    );
  }
}
