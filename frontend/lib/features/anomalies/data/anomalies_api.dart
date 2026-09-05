import 'package:http/http.dart' as http;

import '../../../core/api/operational_api.dart';
import '../domain/entities/anomaly_detection.dart';

class AnomaliesApi {
  AnomaliesApi(String token, String organizationId, {http.Client? client})
    : _api = OperationalApi(token, organizationId, client: client);

  final OperationalApi _api;

  Future<List<AnomalyDetection>> forServer(String serverId) async =>
      (await _api.getResults(
            'anomalies/',
            query: {'server_id': serverId, 'is_anomaly': 'true', 'limit': '20'},
          ))
          .whereType<Map<String, dynamic>>()
          .map(AnomalyDetection.fromJson)
          .toList(growable: false);
}
