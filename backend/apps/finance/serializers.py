from decimal import Decimal
from rest_framework import serializers
from .models import FinancialObligation, PaymentHistory, ObligationType, FlowDirection, ObligationStatus
from .strategies import ObligationStrategyFactory


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ('id', 'paid_amount', 'paid_at', 'term_number', 'note')
        read_only_fields = ('id', 'paid_at')


class FinancialObligationSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    payment_histories = PaymentHistorySerializer(many=True, read_only=True)

    class Meta:
        model = FinancialObligation
        fields = (
            'id',
            'title',
            'type',
            'direction',
            'amount',
            'currency',
            'status',
            'due_date',
            'billing_day',
            'metadata',
            'summary',
            'payment_histories',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_summary(self, obj):
        try:
            strategy = ObligationStrategyFactory.get_strategy(obj.type)
            return strategy.get_summary(obj)
        except Exception:
            return {}

    def validate(self, attrs):
        obligation_type = attrs.get('type') or (self.instance.type if self.instance else None)
        metadata = attrs.get('metadata', {})

        if obligation_type:
            try:
                strategy = ObligationStrategyFactory.get_strategy(obligation_type)
                # ตรวจสอบและ sanitize metadata ตาม strategy
                attrs['metadata'] = strategy.validate_metadata(metadata)
            except ValueError as e:
                raise serializers.ValidationError({'metadata': str(e)})

        return attrs

    def create(self, validated_data):
        # ผูกรายการเข้ากับ User ปัจจุบันที่ล็อกอินอยู่เสมอ
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PayObligationSerializer(serializers.Serializer):
    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text="ยอดเงินที่ชำระ (ถ้าไม่ระบุ จะใช้ยอดงวดตามปกติ)"
    )
    term_number = serializers.IntegerField(
        required=False,
        help_text="งวดที่จ่าย (สำหรับผ่อนชำระ)"
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text="บันทึกเพิ่มเติม เช่น สลิปโอนเงิน"
    )
