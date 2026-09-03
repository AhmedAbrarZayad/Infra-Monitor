from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.organization import Organization
from ..models.organization_membership import OrganizationMembership
from ..permissions import IsEmailVerified
from ..serializers.create_orgnization_serializer import CreateOrganizationSerializer, RoleChangeSerializer
from ..serializers.organization_membership_serializer import OrganizationMembershipSerializer
from ..serializers.organization_serializer import OrganizationPublicSerializer, OrganizationSerializer
from ..services.organization_service import OrganizationConflict, OrganizationService
from ..throttles import MembershipRequestThrottle, OrganizationSearchThrottle


def conflict_response(exc):
    return Response({"detail": exc.detail, "code": exc.code}, status=status.HTTP_409_CONFLICT)


def approved_membership_or_404(organization, user):
    return get_object_or_404(
        OrganizationMembership, organization=organization, user=user, approved=True
    )


class OrganizationContextView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = list(
            OrganizationMembership.objects.filter(user=request.user)
            .select_related("organization", "user")
            .order_by("-updated_at")
        )
        approved = [item for item in memberships if item.approved]
        pending = [item for item in memberships if not item.approved]
        return Response({
            "memberships": OrganizationMembershipSerializer(approved, many=True).data,
            "pending_memberships": OrganizationMembershipSerializer(pending, many=True).data,
            "can_create_organization": True,
            "recommended_organization_id": str(approved[0].organization_id) if approved else None,
        })


class OrganizationSearchView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]
    throttle_classes = [OrganizationSearchThrottle]
    serializer_class = OrganizationPublicSerializer

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        queryset = Organization.objects.all()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(summary__icontains=query))
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class OrganizationCollectionView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def post(self, request):
        serializer = CreateOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            organization, membership = OrganizationService.create_organization(
                user=request.user, validated_data=serializer.validated_data
            )
        except OrganizationConflict as exc:
            return conflict_response(exc)
        return Response({
            "organization": OrganizationSerializer(organization).data,
            "membership": OrganizationMembershipSerializer(membership).data,
        }, status=status.HTTP_201_CREATED)


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        approved_membership_or_404(organization, request.user)
        return Response(OrganizationSerializer(organization).data)


class MembershipCollectionView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationMembershipSerializer

    def get_throttles(self):
        return [MembershipRequestThrottle()] if self.request.method == "POST" else super().get_throttles()

    def post(self, request, organization_id):
        if not request.user.is_email_verified:
            return Response({"detail": "A verified email address is required."}, status=403)
        organization = get_object_or_404(Organization, pk=organization_id)
        try:
            membership = OrganizationService.request_membership(organization=organization, user=request.user)
        except OrganizationConflict as exc:
            return conflict_response(exc)
        return Response(self.get_serializer(membership).data, status=status.HTTP_201_CREATED)

    def get(self, request, organization_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        reviewer = approved_membership_or_404(organization, request.user)
        if reviewer.role not in {"OWNER", "ADMIN"}:
            return Response({"detail": "Owner or admin access is required."}, status=403)
        if request.query_params.get("approved") != "false":
            return Response({"approved": ["This endpoint requires approved=false."]}, status=400)
        queryset = OrganizationMembership.objects.filter(
            organization=organization, approved=False
        ).select_related("organization", "user")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class MembershipApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id, membership_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        try:
            membership = OrganizationService.approve_membership(
                organization=organization, membership_id=membership_id, actor=request.user
            )
        except LookupError:
            return Response(status=404)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except OrganizationConflict as exc:
            return conflict_response(exc)
        return Response(OrganizationMembershipSerializer(membership).data)


class MembershipRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, organization_id, membership_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        try:
            OrganizationService.reject_membership(
                organization=organization, membership_id=membership_id, actor=request.user
            )
        except LookupError:
            return Response(status=404)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except OrganizationConflict as exc:
            return conflict_response(exc)
        return Response(status=204)


class MemberListView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationMembershipSerializer

    def get(self, request, organization_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        approved_membership_or_404(organization, request.user)
        queryset = OrganizationMembership.objects.filter(
            organization=organization, approved=True
        ).select_related("organization", "user")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class MemberRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, organization_id, user_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        serializer = RoleChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership = OrganizationService.change_role(
                organization=organization, target_user_id=user_id,
                role=serializer.validated_data["role"], actor=request.user,
            )
        except LookupError:
            return Response(status=404)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except OrganizationConflict as exc:
            return conflict_response(exc)
        return Response(OrganizationMembershipSerializer(membership).data)


class MemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, organization_id, user_id):
        organization = get_object_or_404(Organization, pk=organization_id)
        try:
            OrganizationService.remove_member(
                organization=organization, target_user_id=user_id, actor=request.user
            )
        except LookupError:
            return Response(status=404)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except OrganizationConflict as exc:
            return conflict_response(exc)
        return Response(status=204)
