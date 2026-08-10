import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/data_sources/overview_data_source.dart';
import '../../data/repositories/overview_repository_impl.dart';
import '../../domain/entities/overview_dashboard.dart';
import '../../domain/repositories/overview_repository.dart';

final overviewDataSourceProvider = Provider<OverviewDataSource>(
  (ref) => DummyOverviewDataSource(),
);

final overviewRepositoryProvider = Provider<OverviewRepository>(
  (ref) => OverviewRepositoryImpl(ref.watch(overviewDataSourceProvider)),
);

final overviewDashboardProvider = FutureProvider<OverviewDashboard>(
  (ref) => ref.watch(overviewRepositoryProvider).getDashboard(),
);
