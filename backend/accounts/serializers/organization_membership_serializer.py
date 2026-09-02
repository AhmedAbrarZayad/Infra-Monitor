from rest_framework import serializers
from ..models.organization_membership import OrganizationMembership

class OrganizationMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMembership
        fields = ['organization', 'user', 'role', 'approved', 'created_at', 'updated_at']
