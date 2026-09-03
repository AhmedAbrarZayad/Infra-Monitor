from rest_framework import serializers

from ..models.organization import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "summary", "logo_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "summary", "logo_url"]
        read_only_fields = fields
