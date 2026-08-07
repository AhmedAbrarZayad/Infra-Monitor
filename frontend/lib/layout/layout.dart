import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/data/app_bar_titles.dart';
import 'package:frontend/shared/components/appbar/app_bar.dart';
import 'package:frontend/shared/components/bottom_nav_bar/bottom_nav_bar.dart';




class LayoutScreen extends ConsumerStatefulWidget {
  const LayoutScreen({super.key});

  @override
  ConsumerState<LayoutScreen> createState() => _LayoutScreenState();
}


class _LayoutScreenState extends ConsumerState<LayoutScreen> {
  int screen = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: APP_BAR_TITLES[screen]),
      bottomNavigationBar: BottomNavBar(currentIndex: screen, onTap: (i) => setState(() => screen = i)),
    );
  }
}