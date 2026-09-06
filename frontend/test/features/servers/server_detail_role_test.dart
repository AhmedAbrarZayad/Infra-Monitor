import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/features/anomalies/presentation/providers/anomaly_providers.dart';
import 'package:frontend/features/organizations/data/organization_models.dart';
import 'package:frontend/features/organizations/domain/organization_context_state.dart';
import 'package:frontend/features/organizations/presentation/providers/organization_provider.dart';
import 'package:frontend/features/servers/domain/entities/server.dart';
import 'package:frontend/features/servers/presentation/pages/server_detail_page.dart';
import 'package:frontend/features/servers/presentation/providers/servers_providers.dart';

void main() {
  testWidgets('Admin server detail never loads host health or metric history', (
    tester,
  ) async {
    final membership = OrganizationMembership(
      id: '10000000-0000-0000-0000-000000000001',
      organization: const Organization(
        id: '20000000-0000-0000-0000-000000000001',
        name: 'Operations',
        summary: 'Operations',
      ),
      user: const MembershipUser(
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        firstName: 'Admin',
        lastName: 'One',
      ),
      role: 'ADMIN',
      approved: true,
      createdAt: DateTime.utc(2026),
      updatedAt: DateTime.utc(2026),
    );
    final context = OrganizationContext(
      memberships: [membership],
      pendingMemberships: const [],
      canCreateOrganization: false,
      recommendedOrganizationId: membership.organization.id,
    );
    var hostHealthRequests = 0;
    var hostMetricRequests = 0;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          organizationContextProvider.overrideWith(
            (ref) => OrganizationContextNotifier(
              ref: ref,
              repository: null,
              storage: const FlutterSecureStorage(),
              initialState: OrganizationReady(context, membership),
            ),
          ),
          serverProvider.overrideWith(
            (ref, _) async => const ServerSummary(
              id: 'server-1',
              name: 'Server one',
              hostName: 'host-one',
              environment: 'prod',
              status: ServerStatus.healthy,
              alertCount: 0,
              cpu: null,
              memory: null,
              disk: null,
              lastSeenAt: null,
              serviceCount: 0,
              cpuHistory: [],
            ),
          ),
          serverServicesProvider.overrideWith((ref, _) async => const []),
          serverAnomaliesProvider.overrideWith((ref, _) async => const []),
          serverHealthProvider.overrideWith((ref, _) async {
            hostHealthRequests++;
            throw StateError('Restricted role requested host health');
          }),
          serverMetricProvider.overrideWith((ref, _) async {
            hostMetricRequests++;
            throw StateError('Restricted role requested host metrics');
          }),
        ],
        child: const MaterialApp(home: ServerDetailPage(serverId: 'server-1')),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Server one'), findsOneWidget);
    expect(find.textContaining('DISCOVERED SERVICES'), findsOneWidget);
    expect(find.text('METRIC HISTORY'), findsNothing);
    expect(hostHealthRequests, 0);
    expect(hostMetricRequests, 0);
  });
}
