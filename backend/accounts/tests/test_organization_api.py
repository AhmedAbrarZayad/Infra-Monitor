from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationMembership, Users
from accounts.services.organization_service import OrganizationService


def make_user(email, *, verified=True):
    return Users.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="TestPass123!",
        is_email_verified=verified,
    )


class OrganizationModelTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.organization = Organization.objects.create(name="Operations", summary="Production")

    def test_uuids_and_optional_logo_are_generated(self):
        membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.owner, role="OWNER", approved=True
        )
        self.assertIsNotNone(self.organization.id)
        self.assertIsNone(self.organization.logo_url)
        self.assertIsNotNone(membership.id)

    def test_duplicate_membership_is_rejected(self):
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.owner, role="ENGINEER", approved=False
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationMembership.objects.create(
                organization=self.organization, user=self.owner, role="ENGINEER", approved=False
            )

    def test_only_one_owner_per_organization_and_user(self):
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.owner, role="OWNER", approved=True
        )
        another_user = make_user("another@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationMembership.objects.create(
                organization=self.organization, user=another_user, role="OWNER", approved=True
            )
        another_org = Organization.objects.create(name="Second", summary="Second")
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationMembership.objects.create(
                organization=another_org, user=self.owner, role="OWNER", approved=True
            )

    def test_privileged_memberships_must_be_approved(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationMembership.objects.create(
                organization=self.organization, user=self.owner, role="ADMIN", approved=False
            )


class OrganizationServiceTests(TestCase):
    def test_creation_builds_owner_membership(self):
        user = make_user("creator@example.com")
        organization, membership = OrganizationService.create_organization(
            user=user, validated_data={"name": "Example", "summary": "Summary"}
        )
        self.assertEqual(membership.organization, organization)
        self.assertEqual(membership.user, user)
        self.assertEqual(membership.role, "OWNER")
        self.assertTrue(membership.approved)


class OrganizationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = make_user("owner@example.com")
        self.admin = make_user("admin@example.com")
        self.engineer = make_user("engineer@example.com")
        self.applicant = make_user("applicant@example.com")
        self.organization = Organization.objects.create(name="Example Ops", summary="Production team")
        self.owner_membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.owner, role="OWNER", approved=True
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin, role="ADMIN", approved=True
        )
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.engineer, role="ENGINEER", approved=True
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_context_splits_approved_and_pending_memberships(self):
        other = Organization.objects.create(name="Pending Org", summary="Pending")
        OrganizationMembership.objects.create(organization=other, user=self.engineer)
        self.authenticate(self.engineer)
        response = self.client.get("/api/organizations/context/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["memberships"]), 1)
        self.assertEqual(len(response.data["pending_memberships"]), 1)
        self.assertTrue(response.data["can_create_organization"])

    def test_unverified_user_cannot_search_create_or_join(self):
        user = make_user("unverified@example.com", verified=False)
        self.authenticate(user)
        self.assertEqual(self.client.get("/api/organizations/search/?q=Example").status_code, 403)
        self.assertEqual(self.client.post("/api/organizations/", {"name": "N", "summary": "S"}).status_code, 403)
        self.assertEqual(
            self.client.post(f"/api/organizations/{self.organization.id}/memberships/").status_code, 403
        )

    def test_search_exposes_public_metadata_only(self):
        self.authenticate(self.applicant)
        response = self.client.get("/api/organizations/search/?q=Example")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(set(response.data["results"][0]), {"id", "name", "summary", "logo_url"})

    def test_join_approve_and_duplicate_or_stale_decisions(self):
        self.authenticate(self.applicant)
        join_url = f"/api/organizations/{self.organization.id}/memberships/"
        response = self.client.post(join_url)
        self.assertEqual(response.status_code, 201)
        membership_id = response.data["id"]
        self.assertEqual(self.client.post(join_url).status_code, 409)

        self.authenticate(self.admin)
        approve_url = f"{join_url}{membership_id}/approve/"
        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["approved"])
        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "membership_already_processed")

    def test_rejection_allows_reapplication(self):
        pending = OrganizationMembership.objects.create(
            organization=self.organization, user=self.applicant
        )
        self.authenticate(self.owner)
        response = self.client.delete(
            f"/api/organizations/{self.organization.id}/memberships/{pending.id}/reject/"
        )
        self.assertEqual(response.status_code, 204)
        self.authenticate(self.applicant)
        self.assertEqual(
            self.client.post(f"/api/organizations/{self.organization.id}/memberships/").status_code,
            201,
        )

    def test_engineer_cannot_list_pending_or_make_decisions(self):
        pending = OrganizationMembership.objects.create(
            organization=self.organization, user=self.applicant
        )
        self.authenticate(self.engineer)
        base = f"/api/organizations/{self.organization.id}/memberships/"
        self.assertEqual(self.client.get(base + "?approved=false").status_code, 403)
        self.assertEqual(self.client.post(f"{base}{pending.id}/approve/").status_code, 403)

    def test_owner_can_promote_and_admin_cannot_change_roles(self):
        role_url = f"/api/organizations/{self.organization.id}/members/{self.engineer.id}/role/"
        self.authenticate(self.owner)
        response = self.client.patch(role_url, {"role": "ADMIN"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "ADMIN")

        self.authenticate(self.admin)
        response = self.client.patch(role_url, {"role": "ENGINEER"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_remove_engineer_but_not_admin_or_owner(self):
        self.authenticate(self.admin)
        base = f"/api/organizations/{self.organization.id}/members/"
        self.assertEqual(self.client.delete(f"{base}{self.engineer.id}/").status_code, 204)
        self.assertEqual(self.client.delete(f"{base}{self.owner.id}/").status_code, 409)

    def test_cross_organization_access_is_hidden(self):
        outsider = make_user("outsider@example.com")
        other = Organization.objects.create(name="Other", summary="Other")
        OrganizationMembership.objects.create(organization=other, user=outsider, role="OWNER", approved=True)
        self.authenticate(outsider)
        self.assertEqual(self.client.get(f"/api/organizations/{self.organization.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/organizations/{self.organization.id}/members/").status_code, 404)

    def test_removed_member_immediately_loses_access(self):
        self.authenticate(self.owner)
        self.client.delete(f"/api/organizations/{self.organization.id}/members/{self.engineer.id}/")
        self.authenticate(self.engineer)
        self.assertEqual(self.client.get(f"/api/organizations/{self.organization.id}/").status_code, 404)
