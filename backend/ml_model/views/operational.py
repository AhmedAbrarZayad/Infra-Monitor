from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import apply_time_range, get_organization_membership, paginated_response
from ml_model.models import AnomalyDetection
from ml_model.presenters import present_anomaly


class AnomalyListView(APIView):
    def get(self, request, organization_id):
        organization, _ = get_organization_membership(request, organization_id)
        queryset = AnomalyDetection.objects.filter(organization=organization).select_related(
            "server_id", "service_id"
        )
        for parameter in ["server_id", "service_id", "is_anomaly"]:
            value = request.query_params.get(parameter)
            if value is not None:
                if parameter == "is_anomaly":
                    value = value.lower() == "true"
                queryset = queryset.filter(**{parameter: value})
        queryset = apply_time_range(queryset, request, "detected_at")
        return paginated_response(request, queryset, present_anomaly)


class AnomalyDetailView(APIView):
    def get(self, request, organization_id, detection_id):
        organization, _ = get_organization_membership(request, organization_id)
        anomaly = get_object_or_404(
            AnomalyDetection.objects.select_related("server_id", "service_id"),
            organization=organization,
            pk=detection_id,
        )
        return Response(present_anomaly(anomaly))
