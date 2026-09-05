from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserPreference
from accounts.serializers import UserPreferenceSerializer


class PreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get_object(user):
        preference, _ = UserPreference.objects.get_or_create(user_id=user)
        return preference

    def get(self, request):
        return Response(UserPreferenceSerializer(self.get_object(request.user)).data)

    def patch(self, request):
        serializer = UserPreferenceSerializer(
            self.get_object(request.user), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
