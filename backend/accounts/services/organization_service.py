import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models.organization import Organization
from ..models.organization_membership import OrganizationMembership

logger = logging.getLogger(__name__)


class OrganizationConflict(Exception):
    def __init__(self, detail, code):
        self.detail = detail
        self.code = code
        super().__init__(detail)


class OrganizationService:
    @staticmethod
    @transaction.atomic
    def create_organization(*, user, validated_data):
        organization = Organization.objects.create(**validated_data)
        membership = OrganizationMembership.objects.create(
            organization=organization, user=user, role="OWNER", approved=True
        )
        logger.info("organization_created actor_user_id=%s organization_id=%s", user.pk, organization.pk)
        return organization, membership

    @staticmethod
    @transaction.atomic
    def request_membership(*, organization, user):
        try:
            membership = OrganizationMembership.objects.create(
                organization=organization, user=user, role="ENGINEER", approved=False
            )
        except IntegrityError as exc:
            raise OrganizationConflict(
                "A membership or request already exists for this organization.", "membership_already_exists"
            ) from exc
        logger.info("membership_requested actor_user_id=%s organization_id=%s", user.pk, organization.pk)
        return membership

    @staticmethod
    @transaction.atomic
    def approve_membership(*, organization, membership_id, actor):
        OrganizationService._lock_reviewer(organization, actor)
        membership = OrganizationService._get_locked_membership(organization, membership_id)
        if membership.approved or membership.role != "ENGINEER":
            raise OrganizationConflict("This membership request has already been processed.", "membership_already_processed")
        changed = OrganizationMembership.objects.filter(
            pk=membership.pk, approved=False, role="ENGINEER"
        ).update(approved=True, updated_at=timezone.now())
        if not changed:
            raise OrganizationConflict("This membership request has already been processed.", "membership_already_processed")
        membership.refresh_from_db()
        logger.info("membership_approved actor_user_id=%s membership_id=%s", actor.pk, membership.pk)
        return membership

    @staticmethod
    @transaction.atomic
    def reject_membership(*, organization, membership_id, actor):
        OrganizationService._lock_reviewer(organization, actor)
        membership = OrganizationService._get_locked_membership(organization, membership_id)
        if membership.approved or membership.role != "ENGINEER":
            raise OrganizationConflict("This membership request has already been processed.", "membership_already_processed")
        deleted, _ = OrganizationMembership.objects.filter(
            pk=membership.pk, approved=False, role="ENGINEER"
        ).delete()
        if not deleted:
            raise OrganizationConflict("This membership request has already been processed.", "membership_already_processed")
        logger.info("membership_rejected actor_user_id=%s membership_id=%s", actor.pk, membership_id)

    @staticmethod
    @transaction.atomic
    def change_role(*, organization, target_user_id, role, actor):
        OrganizationService._lock_owner(organization, actor)
        membership = OrganizationService._get_locked_user_membership(organization, target_user_id)
        if not membership.approved:
            raise OrganizationConflict("Pending memberships cannot have their role changed.", "membership_not_approved")
        if membership.role == "OWNER":
            raise OrganizationConflict("The organization owner cannot be modified.", "owner_membership_protected")
        old_role = membership.role
        membership.role = role
        membership.save(update_fields=["role", "updated_at"])
        logger.info(
            "membership_role_changed actor_user_id=%s target_user_id=%s old_role=%s new_role=%s",
            actor.pk, membership.user_id, old_role, role,
        )
        return membership

    @staticmethod
    @transaction.atomic
    def remove_member(*, organization, target_user_id, actor):
        reviewer = OrganizationService._lock_reviewer(organization, actor)
        membership = OrganizationService._get_locked_user_membership(organization, target_user_id)
        if actor.pk == membership.user_id:
            raise OrganizationConflict("Members cannot remove themselves in v1.", "self_removal_not_allowed")
        if membership.role == "OWNER":
            raise OrganizationConflict("The organization owner cannot be removed.", "owner_membership_protected")
        if reviewer.role == "ADMIN" and membership.role != "ENGINEER":
            raise PermissionError("Admins may remove engineers only.")
        target_id = membership.user_id
        membership.delete()
        logger.info("membership_removed actor_user_id=%s target_user_id=%s", actor.pk, target_id)

    @staticmethod
    def _get_locked_membership(organization, membership_id):
        try:
            return OrganizationMembership.objects.select_for_update().get(
                organization=organization, pk=membership_id
            )
        except OrganizationMembership.DoesNotExist as exc:
            raise LookupError from exc

    @staticmethod
    def _get_locked_user_membership(organization, target_user_id):
        try:
            return OrganizationMembership.objects.select_for_update().get(
                organization=organization, user_id=target_user_id
            )
        except OrganizationMembership.DoesNotExist as exc:
            raise LookupError from exc

    @staticmethod
    def _lock_reviewer(organization, actor):
        try:
            return OrganizationMembership.objects.select_for_update().get(
                organization=organization, user=actor, approved=True, role__in=["OWNER", "ADMIN"]
            )
        except OrganizationMembership.DoesNotExist as exc:
            raise PermissionError("Owner or admin access is required.") from exc

    @staticmethod
    def _lock_owner(organization, actor):
        try:
            return OrganizationMembership.objects.select_for_update().get(
                organization=organization, user=actor, approved=True, role="OWNER"
            )
        except OrganizationMembership.DoesNotExist as exc:
            raise PermissionError("Owner access is required.") from exc
