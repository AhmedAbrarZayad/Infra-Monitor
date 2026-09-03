import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/auth_state.dart';
import '../../features/auth/presentation/pages/forgot_password_page.dart';
import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/auth/presentation/pages/reset_password_page.dart';
import '../../features/auth/presentation/pages/session_restore_error_page.dart';
import '../../features/auth/presentation/pages/verify_email_page.dart';
import '../../features/auth/presentation/providers/auth_provider.dart';
import '../../features/navigation/presentation/pages/app_shell_page.dart';
import '../../features/organizations/domain/organization_context_state.dart';
import '../../features/organizations/presentation/pages/create_organization_page.dart';
import '../../features/organizations/presentation/pages/join_organization_page.dart';
import '../../features/organizations/presentation/pages/organization_onboarding_page.dart';
import '../../features/organizations/presentation/pages/pending_organization_page.dart';
import '../../features/organizations/presentation/providers/organization_provider.dart';

class RouterRefreshNotifier extends ChangeNotifier {
  void refresh() => notifyListeners();
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = RouterRefreshNotifier();
  ref.onDispose(refresh.dispose);
  ref.listen<AuthState>(authProvider, (_, _) => refresh.refresh());
  ref.listen<OrganizationContextState>(organizationContextProvider, (_, _) => refresh.refresh());

  return GoRouter(
    initialLocation: '/',
    overridePlatformDefaultLocation: true,
    errorBuilder: (_, _) => const Scaffold(
      body: Center(child: Text('Page not found')),
    ),
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final organization = ref.read(organizationContextProvider);
      final path = state.uri.path;
      const publicPaths = {'/login', '/register', '/verify-email', '/forgot-password', '/reset-password'};
      final isPublic = publicPaths.contains(path);

      if (auth is! AuthAuthenticated) {
        if (auth is AuthInitial || auth is AuthLoading) return isPublic ? null : '/organization/loading';
        if (auth is AuthSessionRestoreError) {
          return path == '/session/error' ? null : '/session/error';
        }
        return isPublic ? null : '/login';
      }

      if (organization is OrganizationLoading) {
        return path == '/organization/loading' ? null : '/organization/loading';
      }
      if (organization is OrganizationContextError) {
        return path == '/organization/error' ? null : '/organization/error';
      }
      if (organization is OrganizationNeedsOnboarding) {
        if (path == '/organization/onboarding' || path == '/organization/create' || path == '/organization/join') return null;
        return '/organization/onboarding';
      }
      if (organization is OrganizationPendingOnly) {
        if (path == '/organization/pending' || path == '/organization/join') return null;
        return '/organization/pending';
      }
      if (organization is OrganizationReady) {
        const gates = {'/organization/loading', '/organization/error', '/organization/onboarding', '/organization/pending'};
        if (isPublic || gates.contains(path)) return '/';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, _) => const AppShellPage()),
      GoRoute(path: '/login', builder: (_, _) => const LoginPage()),
      GoRoute(path: '/register', builder: (_, _) => const RegisterPage()),
      GoRoute(path: '/verify-email', builder: (_, state) => VerifyEmailPage(email: state.uri.queryParameters['email'] ?? '')),
      GoRoute(path: '/forgot-password', builder: (_, _) => const ForgotPasswordPage()),
      GoRoute(path: '/reset-password', builder: (_, state) => ResetPasswordPage(email: state.uri.queryParameters['email'] ?? '')),
      GoRoute(path: '/session/error', builder: (_, _) => const SessionRestoreErrorPage()),
      GoRoute(path: '/organization/loading', builder: (_, _) => const OrganizationLoadingPage()),
      GoRoute(path: '/organization/error', builder: (_, _) => const OrganizationErrorPage()),
      GoRoute(path: '/organization/onboarding', builder: (_, _) => const OrganizationOnboardingPage()),
      GoRoute(path: '/organization/create', builder: (_, _) => const CreateOrganizationPage()),
      GoRoute(path: '/organization/join', builder: (_, _) => const JoinOrganizationPage()),
      GoRoute(path: '/organization/pending', builder: (_, _) => const PendingOrganizationPage()),
    ],
  );
});
