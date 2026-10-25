from decimal import Decimal
from django.db import transaction as db_transaction
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['obligation'].queryset = FinancialObligation.objects.filter(user=request.user)
            self.fields['payment_history'].queryset = PaymentHistory.objects.filter(user=request.user)

    class Meta:
        model = ObligationAttachment
        fields = (
            'id',
            'obligation',
            'payment_history',
            'file',
            'file_url',
            'drive_file_id',
            'drive_view_link',
            'drive_download_link',
            'file_name',
            'file_type',
            'file_size',
            'uploaded_at'
        )
        read_only_fields = ('id', 'uploaded_at', 'file_size', 'file_name')

    def validate(self, attrs):
        user = self.context['request'].user
        obligation = attrs.get('obligation') or (self.instance.obligation if self.instance else None)
        payment_history = attrs.get('payment_history') or (self.instance.payment_history if self.instance else None)

        if obligation and obligation.user != user:
            raise serializers.ValidationError({'obligation': 'You do not own this financial obligation.'})

        if payment_history:
            if payment_history.user != user:
                raise serializers.ValidationError({'payment_history': 'You do not own this payment record.'})
            if obligation and payment_history.obligation != obligation:
                raise serializers.ValidationError({'payment_history': 'Payment history does not belong to the selected obligation.'})

        file_obj = attrs.get('file')
        if file_obj:
            validate_uploaded_file(file_obj)

        return attrs

    def get_file_url(self, obj):
        if obj.drive_view_link:
            return obj.drive_view_link
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return ''

    @db_transaction.atomic
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        file_obj = validated_data.get('file')
        if file_obj:
            validate_uploaded_file(file_obj)
            validated_data['file_name'] = getattr(file_obj, 'name', 'unnamed_file')
            validated_data['file_size'] = getattr(file_obj, 'size', 0)
        return super().create(validated_data)


class PaymentHistorySerializer(serializers.ModelSerializer):
    attachments = ObligationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentHistory
        fields = ('id', 'paid_amount', 'paid_at', 'term_number', 'note', 'metadata', 'attachments')
        read_only_fields = ('id', 'paid_at')


class FinancialObligationSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    sub_orders = serializers.SerializerMethodField()
    payment_histories = PaymentHistorySerializer(many=True, read_only=True)
    attachments = ObligationAttachmentSerializer(many=True, read_only=True)
    down_payment_account_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Ledger account to immediately deduct down payment"
    )

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
            'down_payment_account_id',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # BOLA Protection: scope parent FK exclusively to current user's obligations
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
        # Retrieve sub-orders specifically for parent BNPL accounts
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

        # Merge metadata on partial updates (PATCH) to prevent overwriting existing keys
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

        # Sync subtype between root field and metadata
        subtype = attrs.get('subtype') or metadata.get('subtype')
        if subtype:
            attrs['subtype'] = subtype
            metadata['subtype'] = subtype

        if obligation_type:
            try:
                strategy = ObligationStrategyFactory.get_strategy(obligation_type)
                # Validate and sanitize metadata per domain strategy
                attrs['metadata'] = strategy.validate_metadata(metadata)
            except ValueError as e:
                raise serializers.ValidationError({'metadata': str(e)})

        return attrs

    @db_transaction.atomic
    def create(self, validated_data):
        down_payment_account_id = validated_data.pop('down_payment_account_id', None)
        user = self.context['request'].user
        validated_data['user'] = user

        meta = validated_data.get('metadata') or {}
        down_payment = Decimal(str(meta.get('down_payment', '0.00')))
        parent = validated_data.get('parent')
        down_acc = None

        if down_payment > Decimal('0.00') and down_payment_account_id:
            from apps.ledger.models import Account, AccountType
            try:
                down_acc = Account.objects.select_for_update().get(id=down_payment_account_id, user=user)
            except Account.DoesNotExist:
                raise serializers.ValidationError({'down_payment_account_id': 'Selected down payment account not found.'})

            if down_acc.account_type != AccountType.CREDIT_CARD and down_acc.current_balance < down_payment:
                raise serializers.ValidationError({
                    'down_payment': f"Insufficient funds: {down_acc.name} has balance \u0e3f{down_acc.current_balance:,.2f}, but down payment requires \u0e3f{down_payment:,.2f}."
                })

        # Calculate initial due_date if this is a BNPL sub-order
        order_date = None
        if parent and parent.subtype == ObligationSubtype.BNPL_ACCOUNT:
            import datetime
            from django.utils import timezone
            from apps.finance.strategies.installment import InstallmentStrategy
            o_date_str = meta.get('order_date')
            if o_date_str:
                try:
                    order_date = datetime.date.fromisoformat(o_date_str)
                except ValueError:
                    order_date = timezone.localdate()
            else:
                order_date = timezone.localdate()

            due_day = int((parent.metadata or {}).get('due_day', parent.billing_day or 10))
            validated_data['due_date'] = InstallmentStrategy.calculate_term_due_date(order_date, term_num=1, due_day=due_day)

        obligation = super().create(validated_data)

        # Process down payment ledger transaction if applicable
        if down_payment > Decimal('0.00') and down_acc:
            from apps.ledger.models import Account, Transaction, TransactionType
            from django.db import models as db_models
            from django.utils import timezone
            Account.objects.filter(id=down_acc.id).update(
                current_balance=db_models.F('current_balance') - down_payment,
                updated_at=timezone.now()
            )
            store_name = meta.get('store') or (parent.title if parent else 'BNPL')
            Transaction.objects.create(
                user=user,
                account=down_acc,
                transaction_type=TransactionType.OUTFLOW,
                gross_amount=down_payment,
                net_amount=down_payment,
                title=f"Down Payment: {obligation.title} ({store_name})",
                notes=f"Down payment paid at purchase for order {meta.get('order_number', '')}".strip(),
                transaction_date=order_date if order_date else timezone.localdate(),
                obligation=obligation
            )

        # Sync parent due date if parent is BNPL
        if parent and parent.subtype == ObligationSubtype.BNPL_ACCOUNT:
            import datetime
            parent_strategy = ObligationStrategyFactory.get_strategy(parent.type)
            p_summary = parent_strategy.get_summary(parent)
            if p_summary.get('next_due_date'):
                try:
                    parent.due_date = datetime.date.fromisoformat(p_summary['next_due_date'])
                    parent.save(update_fields=['due_date'])
                except (ValueError, TypeError):
                    pass

        return obligation


class PayObligationSerializer(serializers.Serializer):
    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal('0.01'),
        help_text="Payment amount (defaults to regular installment amount if not specified)"
    )
    statement_month = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Target statement month to settle (e.g. '2026-11')"
    )
    term_number = serializers.IntegerField(
        required=False,
        help_text="Installment term number being paid"
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Additional notes or payment reference"
    )
    slip_file = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Payment slip proof file"
    )
    drive_file_id = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Google Drive uploaded file ID"
    )
    drive_view_link = serializers.URLField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Google Drive viewable URL"
    )
    drive_download_link = serializers.URLField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Google Drive download URL"
    )
    file_name = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Original file name"
    )
    file_size = serializers.IntegerField(
        required=False,
        default=0,
        help_text="File size in bytes"
    )
    account_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Account ID for automated ledger posting"
    )
