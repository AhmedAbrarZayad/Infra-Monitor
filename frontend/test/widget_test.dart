// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:frontend/app/app.dart';

void main() {
  testWidgets('shows the application shell', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: InfraMonitorApp()));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Overview'), findsWidgets);
    expect(find.text('Servers'), findsOneWidget);

    await tester.tap(find.text('Servers'));
    await tester.pump();
    expect(find.text('MONITORED SERVERS'), findsOneWidget);

    await tester.tap(find.text('Incidents'));
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('INCIDENT QUEUE'), findsOneWidget);

    await tester.tap(find.text('AI'));
    await tester.pump();
    expect(find.text('SUGGESTED PROMPTS'), findsOneWidget);

    await tester.tap(find.text('Analytics'));
    await tester.pump();
    expect(find.text('OPERATIONAL METRICS'), findsOneWidget);

    await tester.tap(find.text('More'));
    await tester.pump();
    expect(find.text('SECURITY & AUDIT'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
  });
}
