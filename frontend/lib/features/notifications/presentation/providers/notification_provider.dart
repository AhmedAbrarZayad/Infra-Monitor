import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../data/device_registration_repository.dart';

final notificationMessengerKey = GlobalKey<ScaffoldMessengerState>();

final notificationControllerProvider = Provider<NotificationController>((ref) {
  final controller = NotificationController(
    messaging: FirebaseMessaging.instance,
    storage: ref.watch(secureStorageProvider),
    repository: DeviceRegistrationRepository(
      ref.watch(authenticatedHttpClientProvider),
    ),
  );
  controller.start();
  ref.listen<AuthState>(authProvider, (previous, next) {
    if (previous is! AuthAuthenticated && next is AuthAuthenticated) {
      controller.registerCurrentDevice();
    }
  }, fireImmediately: true);
  ref.onDispose(controller.dispose);
  return controller;
});

class NotificationController {
  NotificationController({
    required this._messaging,
    required this._storage,
    required this._repository,
  });

  static const installationIdKey = 'fcm_installation_id';
  final FirebaseMessaging _messaging;
  final FlutterSecureStorage _storage;
  final DeviceRegistrationRepository _repository;
  final List<StreamSubscription<RemoteMessage>> _subscriptions = [];
  StreamSubscription<String>? _tokenRefreshSubscription;

  void start() {
    _subscriptions.add(
      FirebaseMessaging.onMessage.listen((message) {
        final notification = message.notification;
        notificationMessengerKey.currentState?.showSnackBar(
          SnackBar(
            content: Text(
              notification?.body ?? 'New infrastructure notification',
            ),
            action: SnackBarAction(label: 'OPEN', onPressed: () {}),
          ),
        );
      }),
    );
    _subscriptions.add(
      FirebaseMessaging.onMessageOpenedApp.listen((_) {
        notificationMessengerKey.currentState?.showSnackBar(
          const SnackBar(
            content: Text('Notification opened. Refreshing data…'),
          ),
        );
      }),
    );
  }

  Future<void> registerCurrentDevice() async {
    try {
      final permission = await _messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      if (permission.authorizationStatus == AuthorizationStatus.denied) return;

      final installationId = await _installationId();
      final token = await _messaging.getToken();
      if (token != null) {
        await _repository.register(
          installationId: installationId,
          token: token,
        );
      }
      await _tokenRefreshSubscription?.cancel();
      _tokenRefreshSubscription = _messaging.onTokenRefresh.listen(
        (token) =>
            _repository.register(installationId: installationId, token: token),
      );
    } catch (_) {
      // Push registration must never block normal authenticated app usage.
    }
  }

  Future<String> _installationId() async {
    final existing = await _storage.read(key: installationIdKey);
    if (existing != null) return existing;
    final created = const Uuid().v4();
    await _storage.write(key: installationIdKey, value: created);
    return created;
  }

  void dispose() {
    for (final subscription in _subscriptions) {
      subscription.cancel();
    }
    _tokenRefreshSubscription?.cancel();
  }
}
