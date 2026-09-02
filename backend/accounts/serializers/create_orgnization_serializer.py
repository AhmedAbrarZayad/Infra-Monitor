from rest_framework import serializers
from datetime import datetime
from ..models.organization import Organization

class CreateOrganizationSerializer(serializers.Serializer):
    name = serializers.CharField()
    summary = serializers.CharField()
    logo_url = serializers.CharField()
    updated_at = serializers.DateTimeField(default_timezone=datetime.astimezone)

    def create(self, validated_data):
        """
        Create and return a new `Organization` instance, given the validated data.
        """
        return Organization.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Organization` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.summary = validated_data.get("summary", instance.summary)
        instance.logo_url = validated_data.get("logo_url", instance.logo_url)
        instance.updated_at = validated_data.get("language", instance.updated_at)
        instance.save()
        return instance