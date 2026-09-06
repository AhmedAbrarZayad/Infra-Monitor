import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/features/assignments/domain/assignment_models.dart';
import 'package:frontend/features/assignments/presentation/providers/assignment_providers.dart';
import 'package:frontend/features/assignments/presentation/widgets/assignment_sheet.dart';
import 'package:frontend/features/organizations/data/organization_models.dart';
import 'package:frontend/features/organizations/domain/organization_context_state.dart';
import 'package:frontend/features/organizations/presentation/providers/organization_provider.dart';

OrganizationMembership membership(String role, {int userId = 1}) =>
    OrganizationMembership(
      id: '10000000-0000-0000-0000-00000000000$userId',
      organization: const Organization(
        id: '20000000-0000-0000-0000-000000000001',
        name: 'Operations',
        summary: 'Operations',
      ),
      user: MembershipUser(
        id: userId,
        username: 'user$userId',
        email: 'user$userId@example.com',
        firstName: role,
        lastName: '$userId',
      ),
      role: role,
      approved: true,
      createdAt: DateTime.utc(2026),
      updatedAt: DateTime.utc(2026),
    );

Future<void> pumpSheet(
  WidgetTester tester, {
  required String role,
  required Future<List<OrganizationMembership>> Function() members,
}) async {
  final active = membership(role);
  final context = OrganizationContext(
    memberships: [active],
    pendingMemberships: const [],
    canCreateOrganization: false,
    recommendedOrganizationId: active.organization.id,
  );
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        organizationContextProvider.overrideWith(
          (ref) => OrganizationContextNotifier(
            ref: ref,
            repository: null,
            storage: const FlutterSecureStorage(),
            initialState: OrganizationReady(context, active),
          ),
        ),
        organizationMembersProvider.overrideWith((ref, _) => members()),
        workAssignmentHistoryProvider.overrideWith((ref, _) async => const []),
      ],
      child: const MaterialApp(
        home: Scaffold(
          body: WorkAssignmentSheet(
            resource: AssignmentResource.incident,
            resourceId: 'incident-1',
            currentAssignee: null,
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Admin sees editable Engineer picker', (tester) async {
    await pumpSheet(
      tester,
      role: 'ADMIN',
      members: () async => [membership('ENGINEER', userId: 2)],
    );
    expect(find.text('Save assignment'), findsOneWidget);
    await tester.tap(find.byType(DropdownButtonFormField<int?>));
    await tester.pumpAndSettle();
    expect(find.text('ENGINEER 2'), findsOneWidget);
    expect(find.textContaining('read-only'), findsNothing);
  });

  testWidgets('Engineer sees read-only history without loading members', (
    tester,
  ) async {
    var memberRequests = 0;
    await pumpSheet(
      tester,
      role: 'ENGINEER',
      members: () async {
        memberRequests++;
        throw StateError('Engineer must not load organization members');
      },
    );
    expect(find.textContaining('read-only'), findsOneWidget);
    expect(find.text('Save assignment'), findsNothing);
    expect(memberRequests, 0);
  });
}
