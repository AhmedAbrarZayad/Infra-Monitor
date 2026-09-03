import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/router/app_router.dart';
import '../shared/theme.dart';

class InfraMonitorApp extends ConsumerWidget {
  const InfraMonitorApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'Infra Monitor',
      theme: AppTheme.theme,
      routerConfig: router,
    );
  }
}
