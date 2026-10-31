import uuid
from django.db import transaction
from rest_framework import serializers, viewsets, permissions
from .models import PriceAlert
from .identity import asset_identity
from .services import normalize_ticker


class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = ['id', 'ticker', 'currency', 'condition', 'target_price', 'is_active', 'triggered_at', 'created_at']
        read_only_fields = ['id', 'triggered_at', 'created_at']

    def validate(self, attrs):
        ticker = normalize_ticker(attrs.get('ticker', getattr(self.instance, 'ticker', '')))
        identity = asset_identity(ticker)
        currency = attrs.get('currency', getattr(self.instance, 'currency', '')).upper()
        if not identity.get('currency') or identity['currency'] != currency:
            raise serializers.ValidationError({'currency': 'Choose a known asset and its native currency.'})
        price = attrs.get('target_price', getattr(self.instance, 'target_price', None))
        if price is None or not price.is_finite() or price <= 0:
            raise serializers.ValidationError({'target_price': 'Enter a finite price greater than zero.'})
        if 'ticker' in attrs or not self.instance:
            attrs['ticker'] = ticker
        if 'currency' in attrs or not self.instance:
            attrs['currency'] = currency
        return attrs

    def create(self, validated_data):
        return super().create({**validated_data, 'user': self.context['request'].user})

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = PriceAlert.objects.select_for_update().get(pk=instance.pk, user=self.context['request'].user)
        if any(getattr(instance, field) != value for field, value in validated_data.items()):
            instance.revision = uuid.uuid4()
            instance.triggered_at = None
        return super().update(instance, validated_data)


class PriceAlertViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PriceAlertSerializer
    pagination_class = None

    def get_queryset(self):
        qs = PriceAlert.objects.filter(user=self.request.user)
        ticker = self.request.query_params.get('ticker')
        return qs.filter(ticker=normalize_ticker(ticker)) if ticker else qs
