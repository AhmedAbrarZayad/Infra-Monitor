import '../../domain/entities/server.dart';

abstract interface class ServersDataSource {
  Future<List<Server>> getServers();
}

class DummyServersDataSource implements ServersDataSource {
  static const _redTrend = [
    .45,
    .65,
    .62,
    .72,
    .59,
    .56,
    .42,
    .58,
    .53,
    .73,
    .69,
    .84,
    .76,
    .82,
    .68,
    .72,
  ];
  static const _amberTrend = [
    .42,
    .55,
    .48,
    .64,
    .51,
    .57,
    .48,
    .63,
    .52,
    .72,
    .63,
    .78,
    .68,
    .81,
    .70,
    .73,
  ];

  @override
  Future<List<Server>> getServers() async {
    await Future<void>.delayed(const Duration(milliseconds: 200));
    return const [
      Server(
        name: 'payment-service-prod',
        environment: 'Production',
        status: ServerStatus.critical,
        alertCount: 3,
        cpu: 96,
        memory: 78,
        disk: 61,
        lastSeen: '4s ago',
        uptime: '18d 04h',
        cpuHistory: _redTrend,
      ),
      Server(
        name: 'auth-api-prod',
        environment: 'Production',
        status: ServerStatus.warning,
        alertCount: 1,
        cpu: 64,
        memory: 91,
        disk: 48,
        lastSeen: '6s ago',
        uptime: '31d 11h',
        cpuHistory: _amberTrend,
      ),
      Server(
        name: 'web-frontend-prod',
        environment: 'Production',
        status: ServerStatus.warning,
        alertCount: 1,
        cpu: 42,
        memory: 55,
        disk: 37,
        lastSeen: '3s ago',
        uptime: '9d 02h',
        cpuHistory: _amberTrend,
      ),
      Server(
        name: 'db-primary-prod',
        environment: 'Production',
        status: ServerStatus.warning,
        alertCount: 2,
        cpu: 58,
        memory: 68,
        disk: 82,
        lastSeen: '5s ago',
        uptime: '42d 16h',
        cpuHistory: _amberTrend,
      ),
      Server(
        name: 'worker-queue-prod',
        environment: 'Production',
        status: ServerStatus.offline,
        alertCount: 1,
        cpu: 0,
        memory: 0,
        disk: 44,
        lastSeen: '6m ago',
        uptime: 'offline 6m',
        cpuHistory: _redTrend,
      ),
      Server(
        name: 'analytics-staging',
        environment: 'Staging',
        status: ServerStatus.healthy,
        alertCount: 0,
        cpu: 28,
        memory: 41,
        disk: 35,
        lastSeen: '2s ago',
        uptime: '6d 08h',
        cpuHistory: _amberTrend,
      ),
    ];
  }
}
