from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..serializers.create_orgnization_serializer import CreateOrganizationSerializer
from ..models.organization_membership import OrganizationMembership
from ..serializers.organization_membership_serializer import OrganizationMembershipSerializer
from ..models.users import Users
from ..models.organization import Organization
from rest_framework.views import APIView
from rest_framework.pagination import LimitOffsetPagination
from ..serializers.organization_serializer import OrganizationSerializer
from rest_framework.permissions import AllowAny

@api_view(["POST"])
def create_new_organization(request):
    organization_serializer = CreateOrganizationSerializer(data=request.data)
    if organization_serializer.is_valid():
        organization = organization_serializer.save()
        organization_membership_data = request.data.copy()
        organization_membership_data['organization'] = organization.id
        try:
            user = Users.objects.get(email=request.data.get("email", None))
        except Users.DoesNotExist:
            organization.delete()
            return Response("User does not exist", status=status.HTTP_400_BAD_REQUEST)
        organization_membership_data['user'] = user
        organization_membership_data['role'] = OrganizationMembership.RoleEnum.OWNER
        organization_membership_data['approved'] = True
        organization_membership_serializer = OrganizationMembershipSerializer(data=organization_membership_data)
        if organization_membership_serializer.is_valid():
            organization_membership_serializer.save()
            return Response(data=organization_membership_data, status=status.HTTP_201_CREATED)
        else:
            organization.delete()
    return Response(data="Provided data is not valid", status=status.HTTP_400_BAD_REQUEST)


class OrganizationList(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        paginator = LimitOffsetPagination()
        query = request.query_params.get("search", None)
        if query != None:
            paginated_response = paginator.paginate_queryset(Organization.objects.filter(name__icontains=query), request)
            filtered_result = OrganizationSerializer(
                paginated_response,
                many=True   
            ).data
            return paginator.get_paginated_response(filtered_result)
        paginated_response = paginator.paginate_queryset(Organization.objects.all(), request)
        return paginator.get_paginated_response(OrganizationSerializer(paginated_response, many=True).data)
            