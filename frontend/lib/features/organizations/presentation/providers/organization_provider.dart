import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../ai_assistant/presentation/providers/assistant_providers.dart';
import '../../../analytics/presentation/providers/analytics_providers.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../incidents/presentation/providers/incidents_providers.dart';
import '../../../more/presentation/providers/preferences_providers.dart';
import '../../../overview/presentation/providers/overview_providers.dart';
import '../../../servers/presentation/providers/servers_providers.dart';
import '../../data/organization_models.dart';
import '../../data/organization_repository.dart';
import '../../domain/organization_context_state.dart';

const activeOrganizationStorageKey = 'active_organization_id';

final organizationRepositoryProvider = Provider<OrganizationRepository?>((ref) {
  final auth = ref.watch(authProvider);
  if (auth is! AuthAuthenticated) return null;
  return OrganizationRepository(auth.accessToken);
});

final organizationContextProvider =
    StateNotifierProvider<OrganizationContextNotifier, OrganizationContextState>((ref) {
  final repository = ref.watch(organizationRepositoryProvider);
  final notifier = OrganizationContextNotifier(
    ref: ref,
    repository: repository,
    storage: ref.watch(secureStorageProvider),
  );
  if (repository != null) notifier.load();
  return notifier;
});

final organizationMembersProvider =
    FutureProvider.family<List<OrganizationMembership>, String>((ref, organizationId) async {
  final repository = ref.watch(organizationRepositoryProvider);
  if (repository == null) return const [];
  return repository.getMembers(organizationId);
});

class OrganizationContextNotifier extends StateNotifier<OrganizationContextState> {
  final Ref ref;
  final OrganizationRepository? repository;
  final FlutterSecureStorage storage;

  OrganizationContextNotifier({
    required this.ref,
    required this.repository,
    required this.storage,
    OrganizationContextState initialState = const OrganizationLoading(),
  }) : super(initialState);

  Future<void> load() async {
    final api = repository;
    if (api == null) return;
    state = const OrganizationLoading();
    try {
      final context = await api.getContext();
      await _applyContext(context);
    } on ApiException catch (error) {
      if (error.statusCode == 401) {
        await ref.read(authProvider.notifier).clearSession();
      } else {
        state = OrganizationContextError(error.message);
      }
    } catch (_) {
      state = const OrganizationContextError('Unable to load your organization access.');
    }
  }

  Future<String?> createOrganization({
    required String name,
    required String summary,
    String? logoUrl,
  }) async {
    final api = repository;
    if (api == null) return 'Your session is no longer available.';
    try {
      final membership = await api.create(name: name, summary: summary, logoUrl: logoUrl);
      await storage.write(key: activeOrganizationStorageKey, value: membership.organization.id);
      await load();
      return null;
    } on ApiException catch (error) {
      return error.message;
    } catch (_) {
      return 'Unable to create the organization. Please try again.';
    }
  }

  Future<String?> requestToJoin(String organizationId) async {
    final api = repository;
    if (api == null) return 'Your session is no longer available.';
    try {
      await api.join(organizationId);
      await load();
      return null;
    } on ApiException catch (error) {
      return error.message;
    } catch (_) {
      return 'Unable to submit the join request. Please try again.';
    }
  }

  Future<void> selectOrganization(String organizationId) async {
    final current = state;
    if (current is! OrganizationReady) return;
    final membership = current.context.memberships
        .where((item) => item.organization.id == organizationId)
        .firstOrNull;
    if (membership == null) return;
    await storage.write(key: activeOrganizationStorageKey, value: organizationId);
    state = OrganizationReady(current.context, membership);
    _invalidateOrganizationData();
  }

  Future<void> _applyContext(OrganizationContext context) async {
    if (context.memberships.isEmpty) {
      await storage.delete(key: activeOrganizationStorageKey);
      state = context.pendingMemberships.isEmpty
          ? OrganizationNeedsOnboarding(context)
          : OrganizationPendingOnly(context);
      return;
    }
    final savedId = await storage.read(key: activeOrganizationStorageKey);
    OrganizationMembership? active = context.memberships
        .where((item) => item.organization.id == savedId)
        .firstOrNull;
    active ??= context.memberships
        .where((item) => item.organization.id == context.recommendedOrganizationId)
        .firstOrNull;
    active ??= context.memberships.first;
    await storage.write(key: activeOrganizationStorageKey, value: active.organization.id);
    state = OrganizationReady(context, active);
  }

  void _invalidateOrganizationData() {
    ref.invalidate(overviewDashboardProvider);
    ref.invalidate(serversProvider);
    ref.invalidate(incidentsProvider);
    ref.invalidate(analyticsProvider);
    ref.invalidate(assistantContextProvider);
    ref.invalidate(preferencesProvider);
  }
}
