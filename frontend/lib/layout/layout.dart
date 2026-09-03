import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/data/app_bar_titles.dart';
import 'package:frontend/shared/components/appbar/app_bar.dart';
import 'package:frontend/shared/components/bottom_nav_bar/bottom_nav_bar.dart';
import 'package:frontend/features/organizations/domain/organization_context_state.dart';
import 'package:frontend/features/organizations/presentation/providers/organization_provider.dart';

class LayoutScreen extends ConsumerStatefulWidget {
  const LayoutScreen({super.key});

  @override
  ConsumerState<LayoutScreen> createState() => _LayoutScreenState();
}

class _LayoutScreenState extends ConsumerState<LayoutScreen> {
  int screen = 0;

  @override
  Widget build(BuildContext context) {
    final organizationState = ref.watch(organizationContextProvider);
    final role = organizationState is OrganizationReady
        ? organizationState.activeMembership.displayRole
        : '';
    return Scaffold(
      appBar: CustomAppBar(title: APP_BAR_TITLES[screen], role: role),
      bottomNavigationBar: BottomNavBar(
        currentIndex: screen,
        onTap: (i) => setState(() => screen = i),
      ),
    );
  }
}
