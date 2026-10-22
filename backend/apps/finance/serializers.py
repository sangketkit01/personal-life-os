from decimal import Decimal
from rest_framework import serializers
from .models import (
    FinancialObligation,
    PaymentHistory,
    ObligationAttachment,
    ObligationType,
    ObligationSubtype,
    FlowDirection,
    ObligationStatus,
    AttachmentType
)
from .strategies import ObligationStrategyFactory


class ObligationAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ObligationAttachment
        fields = (
            'id',
            'obligation',
            'payment_history',
            'file',
            'file_url',
            'file_name',
            'file_type',
            'file_size',
            'uploaded_at'
        )
        read_only_fields = ('id', 'uploaded_at', 'file_size', 'file_name')

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return ''

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        file_obj = validated_data.get('file')
        if file_obj:
            validated_data['file_name'] = getattr(file_obj, 'name', 'unnamed_file')
            validated_data['file_size'] = getattr(file_obj, 'size', 0)
        return super().create(validated_data)


class PaymentHistorySerializer(serializers.ModelSerializer):
    attachments = ObligationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentHistory
        fields = ('id', 'paid_amount', 'paid_at', 'term_number', 'note', 'attachments')
        read_only_fields = ('id', 'paid_at')


class FinancialObligationSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    sub_orders = serializers.SerializerMethodField()
    payment_histories = PaymentHistorySerializer(many=True, read_only=True)
    attachments = ObligationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FinancialObligation
        fields = (
            'id',
            'parent',
            'title',
            'type',
            'subtype',
            'direction',
            'amount',
            'currency',
            'status',
            'due_date',
            'billing_day',
            'metadata',
            'summary',
            'sub_orders',
            'payment_histories',
            'attachments',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # BOLA Protection: จำกัดขอบเขต parent FK ให้เลือกได้เฉพาะ Obligation ของ User ตัวเองเท่านั้น
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['parent'].queryset = FinancialObligation.objects.filter(user=request.user)

    def get_summary(self, obj):
        try:
            strategy = ObligationStrategyFactory.get_strategy(obj.type)
            return strategy.get_summary(obj)
        except Exception:
            return {}

    def get_sub_orders(self, obj):
        # ดึงรายการซื้อย่อยเฉพาะสำหรับบัญชีแม่ BNPL Account
        if obj.subtype == ObligationSubtype.BNPL_ACCOUNT:
            children = obj.sub_orders.filter(status=ObligationStatus.ACTIVE).order_by('due_date', '-created_at')
            return [
                {
                    'id': str(c.id),
                    'parent_id': str(obj.id),
                    'title': c.title,
                    'amount': c.amount,
                    'currency': c.currency,
                    'status': c.status,
                    'due_date': c.due_date.isoformat() if c.due_date else None,
                    'metadata': c.metadata,
                    'summary': c.summary if hasattr(c, 'summary') else self.get_summary(c)
                }
                for c in children
            ]
        return []

    def validate(self, attrs):
        obligation_type = attrs.get('type') or (self.instance.type if self.instance else None)

        # จัดการ metadata ป้องกันการถูกล้างหายไปเมื่ออัปเดตข้อมูลแบบบางส่วน (PATCH)
        if 'metadata' in attrs:
            raw_metadata = attrs['metadata']
            if self.instance and self.instance.metadata:
                merged_metadata = dict(self.instance.metadata)
                merged_metadata.update(raw_metadata)
                metadata = merged_metadata
            else:
                metadata = raw_metadata
        elif self.instance:
            metadata = dict(self.instance.metadata or {})
        else:
            metadata = {}

        # ซิงค์ subtype ระหว่าง root field กับ metadata
        subtype = attrs.get('subtype') or metadata.get('subtype')
        if subtype:
            attrs['subtype'] = subtype
            metadata['subtype'] = subtype

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
    slip_file = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="ไฟล์สลิปหลักฐานการโอนเงิน"
    )
