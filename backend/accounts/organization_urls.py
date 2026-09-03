from django.urls import path

from .views.organization_view import (
    MemberDetailView, MemberListView, MemberRoleView, MembershipCollectionView,
    MembershipApproveView, MembershipRejectView, OrganizationCollectionView, OrganizationContextView,
    OrganizationDetailView, OrganizationSearchView,
)
from .views import EnrollmentDetailView, EnrollmentTokenView, RotateServerCredentialView, ServerMonitoringView

app_name = "organizations"

urlpatterns = [
    path("", OrganizationCollectionView.as_view(), name="collection"),
    path("context/", OrganizationContextView.as_view(), name="context"),
    path("search/", OrganizationSearchView.as_view(), name="search"),
    path("<uuid:organization_id>/", OrganizationDetailView.as_view(), name="detail"),
    path("<uuid:organization_id>/memberships/", MembershipCollectionView.as_view(), name="memberships"),
    path("<uuid:organization_id>/memberships/<uuid:membership_id>/approve/", MembershipApproveView.as_view(), name="membership-approve"),
    path("<uuid:organization_id>/memberships/<uuid:membership_id>/reject/", MembershipRejectView.as_view(), name="membership-reject"),
    path("<uuid:organization_id>/members/", MemberListView.as_view(), name="members"),
    path("<uuid:organization_id>/members/<int:user_id>/role/", MemberRoleView.as_view(), name="member-role"),
    path("<uuid:organization_id>/members/<int:user_id>/", MemberDetailView.as_view(), name="member-detail"),
    path("<uuid:organization_id>/monitoring/enrollments/", EnrollmentTokenView.as_view(), name="organization-enrollments"),
    path("<uuid:organization_id>/monitoring/enrollments/<uuid:enrollment_id>/", EnrollmentDetailView.as_view(), name="organization-enrollment-detail"),
    path("<uuid:organization_id>/servers/<uuid:server_id>/monitoring/", ServerMonitoringView.as_view(), name="server-monitoring"),
    path("<uuid:organization_id>/servers/<uuid:server_id>/monitoring/credentials/rotate/", RotateServerCredentialView.as_view(), name="server-monitoring-credential-rotate"),
]
