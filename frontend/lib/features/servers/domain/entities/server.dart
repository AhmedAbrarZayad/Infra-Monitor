enum ServerStatus { critical, warning, healthy, offline, unknown }

class Server {
  const Server({
    required this.name,
    required this.environment,
    required this.status,
    required this.alertCount,
    required this.cpu,
    required this.memory,
    required this.disk,
    required this.lastSeen,
    required this.uptime,
    required this.cpuHistory,
  });

  final String name;
  final String environment;
  final ServerStatus status;
  final int alertCount;
  final int cpu;
  final int memory;
  final int disk;
  final String lastSeen;
  final String uptime;
  final List<double> cpuHistory;
}
