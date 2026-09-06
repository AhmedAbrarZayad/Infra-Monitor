import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/data/app_bar_titles.dart';
import 'package:frontend/features/navigation/presentation/widgets/app_bottom_navigation.dart';

void main() {
  test('shell navigation has five aligned destinations without Analytics', () {
    final labels = AppBottomNavigation.destinations
        .map((destination) => destination.label)
        .toList();
    expect(APP_BAR_TITLES, ['Overview', 'Servers', 'Incidents', 'AI', 'More']);
    expect(labels, APP_BAR_TITLES);
    expect(labels, isNot(contains('Analytics')));
  });
}
