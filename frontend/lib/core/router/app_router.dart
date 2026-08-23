import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/auth_state.dart';
import '../../features/auth/presentation/pages/forgot_password_page.dart';
import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/auth/presentation/pages/reset_password_page.dart';
import '../../features/auth/presentation/pages/verify_email_page.dart';
import '../../features/auth/presentation/providers/auth_provider.dart';
import '../../features/navigation/presentation/pages/app_shell_page.dart';

/// Creates the app router with auth-aware redirect logic.
GoRouter createAppRouter(WidgetRef ref) {
  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final isAuthenticated = authState is AuthAuthenticated;
      final currentPath = state.uri.path;

      // Public routes that don't require authentication
      const publicPaths = [
        '/login',
        '/register',
        '/verify-email',
        '/forgot-password',
        '/reset-password',
      ];

      final isPublicRoute = publicPaths.any((p) => currentPath.startsWith(p));

      print("is Authenticated? ${isAuthenticated}");
      print("is Public Route? ${isPublicRoute}");

      // If not authenticated and trying to access a protected route
      if (!isAuthenticated && !isPublicRoute) {
        // Still loading/initializing — don't redirect yet
        //if (authState is AuthInitial) return null;
        return '/login';
      }

      // If authenticated and trying to access a public auth route
      if (isAuthenticated && isPublicRoute) {
        return '/';
      }

      return null; // No redirect
    },
    routes: [
      // Main app shell (protected)
      GoRoute(
        path: '/',
        builder: (context, state) => const AppShellPage(),
      ),

      // Auth routes (public)
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterPage(),
      ),
      GoRoute(
        path: '/verify-email',
        builder: (context, state) {
          final email = state.uri.queryParameters['email'] ?? '';
          return VerifyEmailPage(email: email);
        },
      ),
      GoRoute(
        path: '/forgot-password',
        builder: (context, state) => const ForgotPasswordPage(),
      ),
      GoRoute(
        path: '/reset-password',
        builder: (context, state) {
          final email = state.uri.queryParameters['email'] ?? '';
          return ResetPasswordPage(email: email);
        },
      ),
    ],
  );
}
