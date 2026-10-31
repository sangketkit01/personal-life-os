from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from rest_framework import serializers, views, permissions, response
from .models import NotificationPreference, NotificationDelivery
from .delivery import preferences, reschedule_pending
from django.db import transaction


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        exclude = ['id', 'user']

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError('Unknown timezone.')
        return value

    def validate(self, attrs):
        start = attrs.get('quiet_start', getattr(self.instance, 'quiet_start', None))
        end = attrs.get('quiet_end', getattr(self.instance, 'quiet_end', None))
        if bool(start) != bool(end) or (start and start == end):
            raise serializers.ValidationError('Set both quiet-hour times to different values, or clear both.')
        return attrs


class NotificationSettingsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return response.Response({'preferences': PreferenceSerializer(preferences(request.user)).data,
            'deliveries': list(NotificationDelivery.objects.filter(user=request.user).values('id', 'category', 'status', 'created_at', 'sent_at', 'error')[:20])})

    @transaction.atomic
    def patch(self, request):
        serializer = PreferenceSerializer(preferences(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        pref = serializer.save()
        if {'quiet_start', 'quiet_end', 'timezone'}.intersection(serializer.validated_data):
            reschedule_pending(request.user, pref)
        return response.Response(serializer.data)
