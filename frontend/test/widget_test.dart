import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:frontend/app/app.dart';
import 'package:frontend/features/auth/data/models/user_model.dart';
import 'package:frontend/features/auth/data/auth_repository.dart';
import 'package:frontend/features/auth/domain/auth_state.dart';
import 'package:frontend/features/auth/presentation/providers/auth_provider.dart';
import 'package:frontend/features/organizations/data/organization_models.dart';
import 'package:frontend/features/organizations/domain/organization_context_state.dart';
import 'package:frontend/features/organizations/presentation/providers/organization_provider.dart';

const user = UserModel(
  id: 1,
  username: 'alex',
  email: 'alex@example.com',
  firstName: 'Alex',
  lastName: 'Perera',
  role: 'viewer',
  isEmailVerified: true,
  createdAt: '2026-01-01T00:00:00Z',
);

OrganizationMembership membership() => OrganizationMembership(
      id: '10000000-0000-0000-0000-000000000001',
      organization: const Organization(
        id: '20000000-0000-0000-0000-000000000001',
        name: 'Example Operations',
        summary: 'Production team',
      ),
      user: const MembershipUser(
        id: 1,
        username: 'alex',
        email: 'alex@example.com',
        firstName: 'Alex',
        lastName: 'Perera',
      ),
      role: 'OWNER',
      approved: true,
      createdAt: DateTime.utc(2026),
      updatedAt: DateTime.utc(2026),
    );

void main() {
  testWidgets('authenticated user without memberships sees onboarding', (tester) async {
    tester.binding.platformDispatcher.defaultRouteNameTestValue = '/';
    addTearDown(tester.binding.platformDispatcher.clearDefaultRouteNameTestValue);
    const context = OrganizationContext(
      memberships: [],
      pendingMemberships: [],
      canCreateOrganization: true,
      recommendedOrganizationId: null,
    );
    await tester.pumpWidget(ProviderScope(
      overrides: [
        authProvider.overrideWith((ref) => AuthNotifier(
          repository: AuthRepository(baseUrl: 'http://test/api/auth'),
          storage: const FlutterSecureStorage(),
          initialState: const AuthAuthenticated(user: user, accessToken: 'access', refreshToken: 'refresh'),
          autoLogin: false,
        )),
        organizationContextProvider.overrideWith(
          (ref) => OrganizationContextNotifier(
            ref: ref, repository: null, storage: const FlutterSecureStorage(),
            initialState: const OrganizationNeedsOnboarding(context),
          )),
      ],
      child: const InfraMonitorApp(),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Choose your organization'), findsOneWidget);
    expect(find.text('Create organization'), findsOneWidget);
    expect(find.text('Join organization'), findsOneWidget);
  });

  testWidgets('approved member sees the application shell', (tester) async {
    tester.binding.platformDispatcher.defaultRouteNameTestValue = '/';
    addTearDown(tester.binding.platformDispatcher.clearDefaultRouteNameTestValue);
    final approved = membership();
    final context = OrganizationContext(
      memberships: [approved],
      pendingMemberships: const [],
      canCreateOrganization: false,
      recommendedOrganizationId: approved.organization.id,
    );
    await tester.pumpWidget(ProviderScope(
      overrides: [
        authProvider.overrideWith((ref) => AuthNotifier(
          repository: AuthRepository(baseUrl: 'http://test/api/auth'),
          storage: const FlutterSecureStorage(),
          initialState: const AuthAuthenticated(user: user, accessToken: 'access', refreshToken: 'refresh'),
          autoLogin: false,
        )),
        organizationContextProvider.overrideWith(
          (ref) => OrganizationContextNotifier(
            ref: ref, repository: null, storage: const FlutterSecureStorage(),
            initialState: OrganizationReady(context, approved),
          )),
      ],
      child: const InfraMonitorApp(),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Overview'), findsWidgets);
    expect(find.text('Servers'), findsOneWidget);
  });
}
