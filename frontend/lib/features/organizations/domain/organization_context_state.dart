import '../data/organization_models.dart';

sealed class OrganizationContextState {
  const OrganizationContextState();
}

class OrganizationLoading extends OrganizationContextState {
  const OrganizationLoading();
}

class OrganizationNeedsOnboarding extends OrganizationContextState {
  final OrganizationContext context;
  const OrganizationNeedsOnboarding(this.context);
}

class OrganizationPendingOnly extends OrganizationContextState {
  final OrganizationContext context;
  const OrganizationPendingOnly(this.context);
}

class OrganizationReady extends OrganizationContextState {
  final OrganizationContext context;
  final OrganizationMembership activeMembership;
  const OrganizationReady(this.context, this.activeMembership);
}

class OrganizationContextError extends OrganizationContextState {
  final String message;
  const OrganizationContextError(this.message);
}
