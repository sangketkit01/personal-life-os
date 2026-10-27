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
from apps.workspace.models import WorkspaceProject
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

    project = serializers.PrimaryKeyRelatedField(
        queryset=WorkspaceProject.objects.none(),
        required=False,
        allow_null=True
    )
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)
    project_color = serializers.CharField(source='project.color', read_only=True, default=None)
    is_split_debt = serializers.SerializerMethodField()

    class Meta:
        model = FinancialObligation
        fields = (
            'id',
            'parent',
            'project',
            'project_name',
            'project_color',
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
            'is_split_debt',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'is_split_debt', 'created_at', 'updated_at')

    def get_is_split_debt(self, obj):
        if obj.type != ObligationType.DEBT:
            return False
        meta = obj.metadata or {}
        return bool(
            meta.get('origin_transaction_id') or
            meta.get('origin_bill') or
            meta.get('split_bill_id') or
            meta.get('origin_split_id') or
            (hasattr(obj, 'origin_split') and obj.origin_split.exists())
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # BOLA Protection: scope parent FK exclusively to current user's obligations
        request = self.context.get('request')
        if request is not None and getattr(request, 'user', None) is not None:
            self.fields['project'].queryset = WorkspaceProject.objects.filter(
                user=request.user
            )
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['parent'].queryset = FinancialObligation.objects.filter(user=request.user)

    def to_internal_value(self, data):
        # HTML forms submit an unset project select as an empty string.
        if isinstance(data, dict) and data.get('project') == '':
            data = {**data, 'project': None}
        return super().to_internal_value(data)

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
                if 'linked_card' in raw_metadata and 'payment_method' not in raw_metadata:
                    raw_metadata['payment_method'] = raw_metadata['linked_card']
                elif 'payment_method' in raw_metadata and 'linked_card' not in raw_metadata:
                    raw_metadata['linked_card'] = raw_metadata['payment_method']
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

        if self.instance:
            inst_meta = self.instance.metadata or {}
            inst_current_term = int(inst_meta.get('current_term', 0))
            metadata['current_term'] = inst_current_term

            # Workspace SSOT validation for mirrored MA and Infrastructure obligations
            orig_source_type = inst_meta.get('source_type')
            if orig_source_type:
                metadata['source_type'] = orig_source_type

            is_ma = (orig_source_type == 'MA_CONTRACT') or (hasattr(self.instance, 'ma_projects') and self.instance.ma_projects.exists())
            is_infra = (orig_source_type == 'INFRA_ASSET') or (hasattr(self.instance, 'linked_infra_assets') and self.instance.linked_infra_assets.exists())

            if is_ma or is_infra:
                if is_ma and metadata.get('source_type') != 'MA_CONTRACT':
                    metadata['source_type'] = 'MA_CONTRACT'
                elif is_infra and metadata.get('source_type') != 'INFRA_ASSET':
                    metadata['source_type'] = 'INFRA_ASSET'

                source_label = "Maintenance Agreement" if is_ma else "Infrastructure Asset"
                if 'amount' in attrs and Decimal(str(attrs['amount'])) != Decimal(str(self.instance.amount)):
                    raise serializers.ValidationError({'amount': f"This obligation is managed by Workspace ({source_label}). Edit amount from the corresponding Workspace project or asset."})
                if 'title' in attrs and str(attrs['title']).strip() != str(self.instance.title).strip():
                    raise serializers.ValidationError({'title': f"This obligation is managed by Workspace ({source_label}). Edit title from the corresponding Workspace project or asset."})
                if 'currency' in attrs and attrs['currency'] != self.instance.currency:
                    raise serializers.ValidationError({'currency': f"This obligation is managed by Workspace ({source_label}). Edit currency from the corresponding Workspace project or asset."})
                if 'due_date' in attrs and attrs['due_date'] != self.instance.due_date:
                    raise serializers.ValidationError({'due_date': f"This obligation is managed by Workspace ({source_label}). Edit billing schedule from the corresponding Workspace project or asset."})
                if 'billing_day' in attrs and attrs['billing_day'] != self.instance.billing_day:
                    raise serializers.ValidationError({'billing_day': f"This obligation is managed by Workspace ({source_label}). Edit billing day from the corresponding Workspace project or asset."})
                if 'billing_cycle' in metadata and str(metadata.get('billing_cycle')).upper() != str(inst_meta.get('billing_cycle', '')).upper():
                    raise serializers.ValidationError({'billing_cycle': f"This obligation is managed by Workspace ({source_label}). Edit billing cycle from the corresponding Workspace project or asset."})

            has_payment_history = inst_current_term > 0 or self.instance.payment_histories.exists()

            is_bnpl_suborder = (
                self.instance.subtype == ObligationSubtype.BNPL_ORDER or
                (self.instance.parent_id and self.instance.parent.subtype == ObligationSubtype.BNPL_ACCOUNT)
            )

            if is_bnpl_suborder:
                # 1. Financial terms on BNPL sub-orders are locked
                if 'amount' in attrs and Decimal(str(attrs['amount'])) != Decimal(str(self.instance.amount)):
                    raise serializers.ValidationError({'amount': 'BNPL sub-order monthly amount is locked.'})

                for field in ('total_terms', 'down_payment', 'financed_amount'):
                    if field in inst_meta and field in metadata:
                        if str(metadata[field]).strip() != str(inst_meta[field]).strip():
                            raise serializers.ValidationError({field: f'BNPL sub-order {field} is locked to prevent schedule desynchronization.'})

                # Validate order_date format strictly (YYYY-MM-DD)
                new_order_date_raw = metadata.get('order_date')
                new_order_date_str = None
                if new_order_date_raw is not None and str(new_order_date_raw).strip() != '':
                    candidate = str(new_order_date_raw).strip()
                    import re
                    if not re.match(r'^\d{4}-\d{2}-\d{2}$', candidate):
                        raise serializers.ValidationError({'order_date': 'Order date must be in YYYY-MM-DD format.'})
                    import datetime
                    try:
                        datetime.date.fromisoformat(candidate)
                    except ValueError:
                        raise serializers.ValidationError({'order_date': 'Invalid calendar date for order_date.'})
                    new_order_date_str = candidate
                    metadata['order_date'] = candidate
                else:
                    new_order_date_str = None
                    if 'order_date' in metadata:
                        metadata['order_date'] = None

                # 2. Lock purchase / order date and due date if payment history already exists
                if has_payment_history:
                    old_order_date_str = (str(inst_meta.get('order_date') or '').strip()) or None
                    if old_order_date_str != new_order_date_str:
                        raise serializers.ValidationError({'order_date': 'Cannot change order date after payment history has been recorded.'})
                    if 'due_date' in attrs and attrs['due_date'] != self.instance.due_date:
                        raise serializers.ValidationError({'due_date': 'Cannot change due date after payment history has been recorded.'})
                else:
                    old_order_date_str = (str(inst_meta.get('order_date') or '').strip()) or None
                    if new_order_date_str and new_order_date_str != old_order_date_str:
                        import datetime
                        from apps.finance.strategies.installment import InstallmentStrategy
                        try:
                            new_od = datetime.date.fromisoformat(new_order_date_str)
                            parent = self.instance.parent
                            due_day = int((parent.metadata or {}).get('due_day', parent.billing_day or 10)) if parent else 10
                            attrs['due_date'] = InstallmentStrategy.calculate_term_due_date(new_od, term_num=1, due_day=due_day)
                        except (ValueError, TypeError):
                            pass

            elif self.instance.type == ObligationType.INSTALLMENT and has_payment_history:
                if 'total_terms' in inst_meta and 'total_terms' in metadata:
                    if int(metadata['total_terms']) < inst_current_term:
                        raise serializers.ValidationError({'total_terms': f'Total terms cannot be less than already paid terms ({inst_current_term}).'})

            elif self.instance.type == ObligationType.DEBT:
                raw_rem = inst_meta.get('remaining_balance')
                if raw_rem is not None and str(raw_rem).strip() not in ('', 'None', 'null'):
                    try:
                        fresh_rem = Decimal(str(raw_rem))
                    except Exception:
                        fresh_rem = Decimal(str(self.instance.amount))
                else:
                    fresh_rem = Decimal(str(self.instance.amount))

                has_payments = self.instance.payment_histories.exists() or fresh_rem < self.instance.amount
                is_split = (
                    (hasattr(self.instance, 'origin_split') and self.instance.origin_split.exists()) or
                    bool(inst_meta.get('origin_split_id')) or
                    bool(inst_meta.get('origin_transaction_id')) or
                    bool(inst_meta.get('origin_bill')) or
                    bool(inst_meta.get('split_bill_id'))
                )

                if 'amount' in attrs and Decimal(str(attrs['amount'])) != Decimal(str(self.instance.amount)):
                    if has_payments:
                        raise serializers.ValidationError({'amount': 'Cannot change debt principal after payment history has been recorded.'})
                    if is_split:
                        raise serializers.ValidationError({'amount': 'Cannot change debt principal for obligations generated from a Split Bill.'})
                    metadata['remaining_balance'] = float(Decimal(str(attrs['amount'])))
                else:
                    metadata['remaining_balance'] = float(fresh_rem)

                for calc_key in ('total_paid', 'paid_total', 'progress_pct', 'progress_percentage', 'is_settled'):
                    metadata.pop(calc_key, None)

        elif not self.instance and obligation_type == ObligationType.DEBT:
            if 'amount' in attrs:
                metadata['remaining_balance'] = float(Decimal(str(attrs['amount'])))

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

    @db_transaction.atomic
    def update(self, instance, validated_data):
        from apps.finance.models import FinancialObligation
        locked_ob = FinancialObligation.objects.select_for_update().get(id=instance.id)

        if locked_ob.type == ObligationType.DEBT:
            locked_meta = locked_ob.metadata or {}
            raw_rem = locked_meta.get('remaining_balance')
            if raw_rem is not None and str(raw_rem).strip() not in ('', 'None', 'null'):
                try:
                    fresh_rem = Decimal(str(raw_rem))
                except Exception:
                    fresh_rem = Decimal(str(locked_ob.amount))
            else:
                fresh_rem = Decimal(str(locked_ob.amount))

            has_payments = locked_ob.payment_histories.exists() or fresh_rem < locked_ob.amount
            is_split = (
                (hasattr(locked_ob, 'origin_split') and locked_ob.origin_split.exists()) or
                bool(locked_meta.get('origin_split_id')) or
                bool(locked_meta.get('origin_transaction_id')) or
                bool(locked_meta.get('origin_bill')) or
                bool(locked_meta.get('split_bill_id'))
            )

            meta = validated_data.setdefault('metadata', dict(locked_meta))
            if 'amount' in validated_data and Decimal(str(validated_data['amount'])) != Decimal(str(locked_ob.amount)):
                if has_payments:
                    raise serializers.ValidationError({'amount': 'Cannot change debt principal after payment history has been recorded.'})
                if is_split:
                    raise serializers.ValidationError({'amount': 'Cannot change debt principal for obligations generated from a Split Bill.'})
                meta['remaining_balance'] = float(Decimal(str(validated_data['amount'])))
            else:
                meta['remaining_balance'] = float(fresh_rem)

            for calc_key in ('total_paid', 'paid_total', 'progress_pct', 'progress_percentage', 'is_settled'):
                meta.pop(calc_key, None)

        obligation = super().update(locked_ob, validated_data)
        parent = obligation.parent
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
