import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/overview/presentation/widgets/attention_section.dart';

void main() {
  testWidgets('shows only the ML anomaly contract and no resource summaries', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: AttentionSection(anomalies: [])),
      ),
    );

    expect(find.text('services flagged by ML anomaly detection'), findsOneWidget);
    expect(find.text('No resources currently need attention.'), findsOneWidget);
    expect(find.textContaining('HIGHEST CPU'), findsNothing);
    expect(find.textContaining('HIGHEST MEMORY'), findsNothing);
    expect(find.textContaining('HIGHEST DISK'), findsNothing);
  });
}
