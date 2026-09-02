from rest_framework import serializers


class OrganizationSerializer(serializers.Serializer):
    name = serializers.CharField()
    summary = serializers.CharField()
    logo_url = serializers.CharField()

    class Meta:
        ordering = 'name'