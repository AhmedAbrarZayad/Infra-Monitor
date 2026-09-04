import 'package:http/http.dart' as http;

import '../../../core/api/operational_api.dart';
import '../domain/entities/server.dart';

class ServerEnrollment {
  const ServerEnrollment({
    required this.id,
    required this.serverName,
    required this.environment,
    required this.expiresAt,
    required this.installCommand,
  });

  final String id;
  final String serverName;
  final String environment;
  final DateTime expiresAt;
  final String installCommand;

  factory ServerEnrollment.fromJson(Map<String, dynamic> json) =>
      ServerEnrollment(
        id: json['enrollment_id'] as String,
        serverName: json['server_name'] as String,
        environment: json['environment'] as String,
        expiresAt: DateTime.parse(json['expires_at'] as String),
        installCommand: json['install_command'] as String,
      );
}

class MonitoringApi {
  MonitoringApi(String token, String organizationId, {http.Client? client})
    : _api = OperationalApi(token, organizationId, client: client);
  final OperationalApi _api;

  Future<List<ServerSummary>> servers() async =>
      (await _api.getResults('servers/', query: {'limit': '100'}))
          .whereType<Map<String, dynamic>>()
          .map(ServerSummary.fromJson)
          .toList(growable: false);
  Future<ServerSummary> server(String id) async =>
      ServerSummary.fromJson(await _api.getMap('servers/$id/'));
  Future<ServerHealth> serverHealth(String id) async =>
      ServerHealth.fromJson(await _api.getMap('servers/$id/health/'));
  Future<List<MonitoredService>> services(String serverId) async =>
      (await _api.getResults(
            'servers/$serverId/services/',
            query: {'limit': '100'},
          ))
          .whereType<Map<String, dynamic>>()
          .map(MonitoredService.fromJson)
          .toList(growable: false);
  Future<MonitoredService> serviceHealth(String id) async =>
      MonitoredService.fromJson(await _api.getMap('services/$id/health/'));

  Future<ServerEnrollment> createEnrollment({
    required String serverName,
    required String environment,
  }) async => ServerEnrollment.fromJson(
    await _api.post('monitoring/enrollments/', {
      'server_name': serverName,
      'environment': environment,
    }),
  );

  Future<MetricSeries> serverMetrics(
    String id, {
    required String metric,
    required DateTime from,
    required DateTime to,
    required int step,
  }) async => MetricSeries.fromJson(
    await _api.getMap(
      'servers/$id/metrics/',
      query: _range(metric, from, to, step),
    ),
  );
  Future<MetricSeries> serviceMetrics(
    String id, {
    required String metric,
    required DateTime from,
    required DateTime to,
    required int step,
  }) async => MetricSeries.fromJson(
    await _api.getMap(
      'services/$id/metrics/',
      query: _range(metric, from, to, step),
    ),
  );

  Map<String, String> _range(
    String metric,
    DateTime from,
    DateTime to,
    int step,
  ) => {
    'metric': metric,
    'from': from.toUtc().toIso8601String(),
    'to': to.toUtc().toIso8601String(),
    'step': '$step',
  };
}
