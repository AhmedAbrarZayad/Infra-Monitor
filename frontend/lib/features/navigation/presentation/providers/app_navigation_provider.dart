import 'package:flutter_riverpod/legacy.dart';

class AppNavigationState {
  const AppNavigationState({this.index = 0, this.assistantAnomalyId});
  final int index;
  final String? assistantAnomalyId;

  AppNavigationState copyWith({
    int? index,
    String? assistantAnomalyId,
    bool clearAnomaly = false,
  }) => AppNavigationState(
    index: index ?? this.index,
    assistantAnomalyId: clearAnomaly
        ? null
        : assistantAnomalyId ?? this.assistantAnomalyId,
  );
}

class AppNavigationNotifier extends StateNotifier<AppNavigationState> {
  AppNavigationNotifier() : super(const AppNavigationState());
  void select(int index) => state = state.copyWith(index: index);
  void openAssistant(String anomalyId) =>
      state = AppNavigationState(index: 3, assistantAnomalyId: anomalyId);
  void clearAssistantSelection() => state = state.copyWith(clearAnomaly: true);
}

final appNavigationProvider =
    StateNotifierProvider<AppNavigationNotifier, AppNavigationState>(
      (ref) => AppNavigationNotifier(),
    );
