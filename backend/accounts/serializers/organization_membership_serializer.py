from rest_framework import serializers

from ..models.organization_membership import OrganizationMembership
from .organization_serializer import OrganizationPublicSerializer


class MembershipUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    organization = OrganizationPublicSerializer(read_only=True)
    user = MembershipUserSerializer(read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "organization",
            "user",
            "role",
            "approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
