import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/overview/presentation/widgets/attention_section.dart';
import 'package:frontend/features/organizations/domain/organization_context_state.dart';
import 'package:frontend/features/organizations/presentation/providers/organization_provider.dart';

void main() {
  testWidgets('shows only the ML anomaly contract and no resource summaries', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          organizationContextProvider.overrideWith(
            (ref) => OrganizationContextNotifier(
              ref: ref,
              repository: null,
              storage: const FlutterSecureStorage(),
              initialState: const OrganizationLoading(),
            ),
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(body: AttentionSection(anomalies: [])),
        ),
      ),
    );

    expect(find.text('services flagged by ML anomaly detection'), findsOneWidget);
    expect(find.text('No resources currently need attention.'), findsOneWidget);
    expect(find.textContaining('HIGHEST CPU'), findsNothing);
    expect(find.textContaining('HIGHEST MEMORY'), findsNothing);
    expect(find.textContaining('HIGHEST DISK'), findsNothing);
  });
}
