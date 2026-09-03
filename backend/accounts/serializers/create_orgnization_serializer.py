from rest_framework import serializers

from ..models.organization import Organization
from ..models.organization_membership import OrganizationMembership


class CreateOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "summary", "logo_url"]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "summary": {"required": True, "allow_blank": False},
            "logo_url": {"required": False, "allow_null": True, "allow_blank": True},
        }


class RoleChangeSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            OrganizationMembership.RoleEnum.ADMIN,
            OrganizationMembership.RoleEnum.ENGINEER,
        ]
    )
