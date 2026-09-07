import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';

import '../core/router/app_router.dart';
import '../shared/theme.dart';
import '../features/notifications/presentation/providers/notification_provider.dart';

class InfraMonitorApp extends ConsumerWidget {
  const InfraMonitorApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    if (Firebase.apps.isNotEmpty) {
      ref.watch(notificationControllerProvider);
    }

    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'Infra Monitor',
      theme: AppTheme.theme,
      scaffoldMessengerKey: notificationMessengerKey,
      routerConfig: router,
    );
  }
}
