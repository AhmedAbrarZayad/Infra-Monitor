import 'package:flutter/material.dart';

import '../core/router/app_router.dart';
import '../shared/theme.dart';

class InfraMonitorApp extends StatelessWidget {
  const InfraMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'Infra Monitor',
      theme: AppTheme.theme,
      routerConfig: appRouter,
    );
  }
}
