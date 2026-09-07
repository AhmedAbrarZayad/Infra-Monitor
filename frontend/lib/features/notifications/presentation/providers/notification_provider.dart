import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import '../../../../core/router/app_router.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../incidents/presentation/providers/incidents_providers.dart';
import '../../../navigation/presentation/providers/app_navigation_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../data/device_registration_repository.dart';

final notificationMessengerKey = GlobalKey<ScaffoldMessengerState>();

final notificationControllerProvider = Provider<NotificationController>((ref) {
  final controller = NotificationController(
    messaging: FirebaseMessaging.instance,
    storage: ref.watch(secureStorageProvider),
    repository: DeviceRegistrationRepository(
      ref.watch(authenticatedHttpClientProvider),
    ),
    ref: ref,
  );
  controller.start();
  ref.listen<AuthState>(authProvider, (previous, next) {
    if (previous is! AuthAuthenticated && next is AuthAuthenticated) {
      controller.registerCurrentDevice();
    }
  }, fireImmediately: true);
  ref.listen<OrganizationContextState>(organizationContextProvider, (_, next) {
    if (next is OrganizationReady) controller.openPendingMessage();
  });
  ref.onDispose(controller.dispose);
  return controller;
});

class NotificationController {
  NotificationController({
    required this._messaging,
    required this._storage,
    required this._repository,
    required this._ref,
  });

  static const installationIdKey = 'fcm_installation_id';
  final FirebaseMessaging _messaging;
  final FlutterSecureStorage _storage;
  final DeviceRegistrationRepository _repository;
  final Ref _ref;
  final List<StreamSubscription<RemoteMessage>> _subscriptions = [];
  StreamSubscription<String>? _tokenRefreshSubscription;
  RemoteMessage? _pendingMessage;

  void start() {
    _subscriptions.add(
      FirebaseMessaging.onMessage.listen((message) {
        final notification = message.notification;
        notificationMessengerKey.currentState?.showSnackBar(
          SnackBar(
            content: Text(
              notification?.body ?? 'New infrastructure notification',
            ),
            action: SnackBarAction(
              label: 'OPEN',
              onPressed: () => _openMessage(message),
            ),
          ),
        );
      }),
    );
    _subscriptions.add(
      FirebaseMessaging.onMessageOpenedApp.listen(_openMessage),
    );
    _messaging.getInitialMessage().then((message) {
      if (message != null) _openMessage(message);
    });
  }

  Future<void> _openMessage(RemoteMessage message) async {
    final organizationId = message.data['organization_id'];
    final resourceType = message.data['resource_type'];
    final resourceId = message.data['resource_id'];
    if (organizationId == null ||
        resourceId == null ||
        !const {'INCIDENT', 'ANOMALY'}.contains(resourceType)) {
      return;
    }

    final organization = _ref.read(organizationContextProvider);
    if (organization is! OrganizationReady) {
      _pendingMessage = message;
      return;
    }
    await _ref
        .read(organizationContextProvider.notifier)
        .selectOrganization(organizationId);
    final selected = _ref.read(organizationContextProvider);
    if (selected is! OrganizationReady ||
        selected.activeMembership.organization.id != organizationId) {
      notificationMessengerKey.currentState?.showSnackBar(
        const SnackBar(
          content: Text('This notification is no longer available.'),
        ),
      );
      return;
    }

    if (resourceType == 'INCIDENT') {
      _ref.invalidate(incidentsProvider);
      _ref.read(appNavigationProvider.notifier).openIncident(resourceId);
    } else {
      _ref.read(appNavigationProvider.notifier).openAssistant(resourceId);
    }
    _ref.read(routerProvider).go('/');
  }

  void openPendingMessage() {
    final message = _pendingMessage;
    if (message == null) return;
    _pendingMessage = null;
    _openMessage(message);
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
