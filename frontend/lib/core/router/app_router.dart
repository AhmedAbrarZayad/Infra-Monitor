import 'package:go_router/go_router.dart';

import '../../features/navigation/presentation/pages/app_shell_page.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const AppShellPage()),
  ],
);
