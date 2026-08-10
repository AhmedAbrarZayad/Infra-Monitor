class UserPreferences {
  const UserPreferences({
    required this.name,
    required this.email,
    required this.role,
    required this.environment,
    required this.streamState,
    required this.notifications,
    required this.theme,
    required this.refreshInterval,
    required this.timezone,
  });
  final String name,
      email,
      role,
      environment,
      streamState,
      notifications,
      theme,
      refreshInterval,
      timezone;
}
