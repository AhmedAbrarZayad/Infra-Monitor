import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/features/organizations/data/organization_models.dart';

void main() {
  test('Owner has full operational capabilities', () {
    final capabilities = OperationalCapabilities.forRole('OWNER');
    expect(capabilities.canManageServiceAdmins, isTrue);
    expect(capabilities.canAssignWork, isTrue);
    expect(capabilities.canEnrollServers, isTrue);
    expect(capabilities.canViewHostMetrics, isTrue);
    expect(capabilities.canListMembers, isTrue);
  });

  test('Admin can assign work and list candidates without host control', () {
    final capabilities = OperationalCapabilities.forRole('ADMIN');
    expect(capabilities.canAssignWork, isTrue);
    expect(capabilities.canListMembers, isTrue);
    expect(capabilities.canManageServiceAdmins, isFalse);
    expect(capabilities.canEnrollServers, isFalse);
    expect(capabilities.canViewHostMetrics, isFalse);
  });

  test(
    'Engineer capabilities keep assignment and organization data read-only',
    () {
      final capabilities = OperationalCapabilities.forRole('ENGINEER');
      expect(capabilities.canAssignWork, isFalse);
      expect(capabilities.canListMembers, isFalse);
      expect(capabilities.canEnrollServers, isFalse);
      expect(capabilities.canViewHostMetrics, isFalse);
    },
  );
}
