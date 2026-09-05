import 'dart:async';

import 'package:http/http.dart' as http;

/// HTTP client for authenticated API requests.
///
/// A 401 triggers one refresh shared by all concurrent requests, followed by
/// one retry with the new access token. The session is cleared only when the
/// refresh token itself is rejected.
class AuthenticatedClient extends http.BaseClient {
  AuthenticatedClient({
    required this.accessToken,
    required this.refreshSession,
    required this.clearSession,
    http.Client? inner,
    this.timeout = const Duration(seconds: 15),
  }) : _inner = inner ?? http.Client();

  final String? Function() accessToken;
  final Future<bool> Function() refreshSession;
  final Future<void> Function() clearSession;
  final Duration timeout;
  final http.Client _inner;

  Future<bool>? _refreshInFlight;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final response = await _sendCopy(request).timeout(timeout);
    if (response.statusCode != 401) return response;

    final refreshed = await _refreshOnce();
    if (!refreshed) {
      await clearSession();
      return response;
    }

    // The original response body must not be left open before retrying.
    await response.stream.drain<void>();
    final retried = await _sendCopy(request).timeout(timeout);
    if (retried.statusCode == 401) await clearSession();
    return retried;
  }

  Future<bool> _refreshOnce() {
    final active = _refreshInFlight;
    if (active != null) return active;
    final refresh = refreshSession();
    _refreshInFlight = refresh;
    return refresh.whenComplete(() {
      if (identical(_refreshInFlight, refresh)) _refreshInFlight = null;
    });
  }

  Future<http.StreamedResponse> _sendCopy(http.BaseRequest source) {
    final request = http.Request(source.method, source.url)
      ..followRedirects = source.followRedirects
      ..maxRedirects = source.maxRedirects
      ..persistentConnection = source.persistentConnection
      ..headers.addAll(source.headers);
    if (source is http.Request) request.bodyBytes = source.bodyBytes;

    final token = accessToken();
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    return _inner.send(request);
  }

  @override
  void close() => _inner.close();
}
