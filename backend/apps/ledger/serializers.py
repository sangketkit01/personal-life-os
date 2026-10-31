from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from .models import (
    Account,
    Category,
    Transaction,
    TransactionSplit,
    TransactionAttachment,
    CategoryBudget,
    TransactionType,
    CategoryType
)
from .services import AccountBalanceService, BillSplitService


class CategorySubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'category_type', 'icon', 'color', 'is_system']


class CategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    def get_subcategories(self, obj):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') and request.user.is_authenticated else None
        if hasattr(obj, '_prefetched_objects_cache') and 'subcategories' in obj._prefetched_objects_cache:
            if user:
                subs = [s for s in obj._prefetched_objects_cache['subcategories'] if s.is_system or s.user_id == user.id]
            else:
                subs = [s for s in obj._prefetched_objects_cache['subcategories'] if s.is_system]
        else:
            if user:
                subs = obj.subcategories.filter(Q(is_system=True) | Q(user=user)).order_by('name')
            else:
                subs = obj.subcategories.filter(is_system=True).order_by('name')
        return CategorySubSerializer(subs, many=True).data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['parent'].queryset = Category.objects.filter(
                Q(is_system=True) | Q(user=request.user)
            )

    class Meta:
        model = Category
        fields = [
            'id',
            'user',
            'name',
            'category_type',
            'parent',
            'icon',
            'color',
            'is_system',
            'subcategories',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'is_system', 'created_at']


class AccountSerializer(serializers.ModelSerializer):
    transaction_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Account
        fields = [
            'id',
            'user',
            'name',
            'account_type',
            'currency',
            'initial_balance',
            'current_balance',
            'credit_limit',
            'account_number',
            'institution_name',
            'color',
            'is_default',
            'is_archived',
            'transaction_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'current_balance', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set initial current_balance = initial_balance
        initial_balance = validated_data.get('initial_balance', Decimal('0.00'))
        validated_data['current_balance'] = initial_balance
        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_initial = instance.initial_balance
        new_initial = validated_data.get('initial_balance', old_initial)
        diff = new_initial - old_initial
        if diff != Decimal('0.00'):
            instance.current_balance += diff
        return super().update(instance, validated_data)


class AccountTransferSerializer(serializers.Serializer):
    source_account_id = serializers.UUIDField()
    target_account_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    transaction_date = serializers.DateField()
    title = serializers.CharField(max_length=255, required=False, default="Transfer")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class TransactionSplitSerializer(serializers.ModelSerializer):
    debtor_status = serializers.CharField(source='debtor_obligation.status', read_only=True)
    debtor_id = serializers.UUIDField(source='debtor_obligation.id', read_only=True)
    transaction_title = serializers.CharField(source='transaction.title', read_only=True)
    transaction_date = serializers.DateField(source='transaction.transaction_date', read_only=True)
    transaction_account_name = serializers.CharField(source='transaction.account.name', read_only=True)

    class Meta:
        model = TransactionSplit
        fields = [
            'id',
            'transaction',
            'transaction_title',
            'transaction_date',
            'transaction_account_name',
            'counterparty_name',
            'counterparty_contact',
            'amount',
            'is_settled',
            'settled_at',
            'settlement_transaction',
            'debtor_obligation',
            'debtor_id',
            'debtor_status',
            'notes',
            'items_detail'
        ]
        read_only_fields = ['id', 'transaction', 'is_settled', 'settled_at', 'settlement_transaction', 'debtor_obligation']


class TransactionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionAttachment
        fields = [
            'id',
            'transaction',
            'file',
            'drive_file_id',
            'drive_view_link',
            'drive_download_link',
            'file_name',
            'file_type',
            'file_size',
            'slip_reference',
            'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_currency = serializers.CharField(source='account.currency', read_only=True)
    account_type = serializers.CharField(source='account.account_type', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    splits = TransactionSplitSerializer(many=True, read_only=True)
    attachments = TransactionAttachmentSerializer(many=True, read_only=True)
    is_amount_locked = serializers.SerializerMethodField()
    amount_lock_reason = serializers.SerializerMethodField()

    def get_is_amount_locked(self, obj):
        if obj.transfer_peer_id or obj.transfer_destination_id:
            return True
        if obj.payment_history_id or obj.obligation_id:
            return True
        if obj.settled_splits.exists():
            return True
        if obj.is_split or obj.splits.exists():
            return True
        return False

    def get_amount_lock_reason(self, obj):
        if obj.transfer_peer_id or obj.transfer_destination_id:
            return "Transfer amounts cannot be edited directly. Delete transfer and record anew."
        if obj.payment_history_id or obj.obligation_id:
            return "Amount linked to an obligation payment is locked to maintain dossier balance."
        if obj.settled_splits.exists():
            return "Amount linked to a settled split repayment is locked."
        if obj.is_split or obj.splits.exists():
            return "Split bill amount is locked to maintain split allocation shares."
        return ""

    # Write-only split creation payload
    splits_payload = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    auto_create_radar_debtors = serializers.BooleanField(write_only=True, default=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'user',
            'account',
            'account_name',
            'account_currency',
            'account_type',
            'transaction_type',
            'reporting_kind',
            'category',
            'category_name',
            'category_icon',
            'gross_amount',
            'net_amount',
            'title',
            'notes',
            'transaction_date',
            'is_split',
            'split_metadata',
            'splits',
            'splits_payload',
            'auto_create_radar_debtors',
            'attachments',
            'obligation',
            'payment_history',
            'portfolio',
            'workspace_project',
            'transfer_destination',
            'transfer_peer',
            'is_amount_locked',
            'amount_lock_reason',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'transfer_peer', 'payment_history', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # BOLA Protection: Scope all related model selections to the authenticated user
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['category'].queryset = Category.objects.filter(
                models.Q(is_system=True) | models.Q(user=user)
            )
            from apps.finance.models import FinancialObligation
            self.fields['obligation'].queryset = FinancialObligation.objects.filter(user=user)
            from apps.portfolio.models import InvestmentPortfolio
            self.fields['portfolio'].queryset = InvestmentPortfolio.objects.filter(user=user)
            from apps.workspace.models import WorkspaceProject
            self.fields['workspace_project'].queryset = WorkspaceProject.objects.filter(user=user)

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else attrs.get('user')

        is_split = attrs.get('is_split', getattr(self.instance, 'is_split', False))
        gross = attrs.get('gross_amount', getattr(self.instance, 'gross_amount', None))

        if not self.instance:
            if not is_split and gross is not None and 'net_amount' not in attrs:
                net = gross
                attrs['net_amount'] = gross
            else:
                net = attrs.get('net_amount', gross)
        else:
            # On update: compute net for validation checks without injecting stale net_amount into attrs
            if 'net_amount' in attrs:
                net = attrs['net_amount']
            elif not is_split:
                net = gross
            else:
                net = getattr(self.instance, 'net_amount', gross)

        if gross is not None and gross <= Decimal('0.00'):
            raise serializers.ValidationError({'gross_amount': "Gross amount must be strictly greater than 0."})

        if net is not None and net < Decimal('0.00'):
            raise serializers.ValidationError({'net_amount': "Net amount cannot be negative."})

        if gross is not None and net is not None and net > gross:
            raise serializers.ValidationError({'net_amount': "Net personal amount cannot exceed gross transaction amount."})

        transfer_dest = attrs.get('transfer_destination')
        tx_type = attrs.get('transaction_type', getattr(self.instance, 'transaction_type', None))
        kind = attrs.get('reporting_kind', getattr(self.instance, 'reporting_kind', 'AUTO'))
        if (kind in ('INCOME', 'REIMBURSEMENT') and tx_type != 'INFLOW') or (kind in ('EXPENSE', 'CARD_PAYMENT') and tx_type != 'OUTFLOW'):
            raise serializers.ValidationError({'reporting_kind': 'Reporting kind does not match the money direction.'})
        if (is_split or attrs.get('splits_payload') or (attrs.get('split_metadata') or {}).get('items')) and kind not in ('AUTO','EXPENSE'):
            raise serializers.ValidationError({'reporting_kind': 'Shared bills must remain personal expenses.'})
        if self.instance and (self.instance.transfer_peer_id or self.instance.transfer_destination_id or self.instance.settled_splits.exists()) and kind != 'AUTO':
            raise serializers.ValidationError({'reporting_kind': 'Linked transfers and reimbursements are classified from their source records.'})

        if not self.instance and tx_type == TransactionType.TRANSFER:
            raise serializers.ValidationError({
                'transaction_type': "Direct creation of 'TRANSFER' transactions is not permitted. Use /api/ledger/accounts/transfer/ instead."
            })

        if transfer_dest:
            if tx_type != TransactionType.TRANSFER:
                raise serializers.ValidationError({'transfer_destination': "Cannot set transfer destination on regular transactions. Use the account transfer endpoint instead."})
            if user and transfer_dest.user_id != user.id:
                raise serializers.ValidationError({'transfer_destination': "Transfer destination account must belong to you."})

        return attrs

    @db_transaction.atomic
    def create(self, validated_data):
        splits_payload = validated_data.pop('splits_payload', None)
        auto_create_debtors = validated_data.pop('auto_create_radar_debtors', True)
        split_metadata = validated_data.pop('split_metadata', None) or {}
        user = validated_data.get('user')
        account = validated_data.get('account')
        gross_amount = validated_data.get('gross_amount')
        net_amount = validated_data.get('net_amount', gross_amount)

        if (splits_payload and len(splits_payload) > 0) or (split_metadata and split_metadata.get('items')):
            category = validated_data.get('category')
            title = validated_data.get('title')
            transaction_date = validated_data.get('transaction_date')
            notes = validated_data.get('notes', '')
            workspace_project = validated_data.get('workspace_project')

            split_tx = BillSplitService.create_split_transaction(
                user=user,
                account=account,
                category=category,
                gross_amount=gross_amount,
                net_amount=net_amount,
                title=title,
                transaction_date=transaction_date,
                splits_data=splits_payload or [],
                auto_create_radar_debtors=auto_create_debtors,
                notes=notes,
                split_metadata=split_metadata,
                workspace_project=workspace_project
            )
            if validated_data.get('reporting_kind', 'AUTO') != 'AUTO':
                split_tx.reporting_kind = validated_data['reporting_kind']
                split_tx.save(update_fields=['reporting_kind'])
            return split_tx

        # Normal single transaction - lock account row
        from apps.ledger.models import AccountType
        locked_acc = Account.objects.select_for_update().get(id=account.id, user=user)

        # Overdraft check for non-credit accounts
        if locked_acc.account_type != AccountType.CREDIT_CARD and validated_data.get('transaction_type') == TransactionType.OUTFLOW:
            if locked_acc.current_balance < gross_amount:
                raise serializers.ValidationError({
                    'gross_amount': f"Insufficient funds: {locked_acc.name} has balance \u0e3f{locked_acc.current_balance:,.2f}, but payment requires \u0e3f{gross_amount:,.2f}."
                })

        validated_data['account'] = locked_acc

        tx = super().create(validated_data)

        # Update account balance atomically using DB F() expressions
        if tx.transaction_type == TransactionType.INFLOW:
            Account.objects.filter(id=locked_acc.id).update(
                current_balance=models.F('current_balance') + tx.gross_amount,
                updated_at=timezone.now()
            )
        elif tx.transaction_type == TransactionType.OUTFLOW:
            Account.objects.filter(id=locked_acc.id).update(
                current_balance=models.F('current_balance') - tx.gross_amount,
                updated_at=timezone.now()
            )

        locked_acc.refresh_from_db(fields=['current_balance', 'updated_at'])
        account.current_balance = locked_acc.current_balance
        return tx

    @db_transaction.atomic
    def update(self, instance, validated_data):
        # 1. Disallow changing core structural keys after creation
        new_account = validated_data.get('account')
        if new_account and new_account.id != instance.account_id:
            raise serializers.ValidationError({'account': "Changing transaction account is not permitted. Delete and recreate instead."})

        new_type = validated_data.get('transaction_type')
        if new_type and new_type != instance.transaction_type:
            raise serializers.ValidationError({'transaction_type': "Changing transaction type is not permitted. Delete and recreate instead."})

        # 2. For paired transfers, disallow directly mutating amount or date via transaction PATCH
        if instance.transfer_peer or instance.transfer_destination:
            if 'gross_amount' in validated_data and validated_data['gross_amount'] != instance.gross_amount:
                raise serializers.ValidationError({'gross_amount': "Transfer amount cannot be modified directly. Delete transfer and create a new one."})
            if 'transaction_date' in validated_data and validated_data['transaction_date'] != instance.transaction_date:
                raise serializers.ValidationError({'transaction_date': "Transfer date cannot be modified directly on paired transfers. Delete transfer and create a new one."})

        # Disallow directly modifying gross_amount on payment records or split settlements
        if instance.payment_history_id or instance.obligation_id or instance.settled_splits.exists():
            if 'gross_amount' in validated_data and validated_data['gross_amount'] != instance.gross_amount:
                raise serializers.ValidationError({
                    'gross_amount': "Transaction amount linked to an obligation payment or split settlement cannot be edited directly. Delete and re-record the payment instead."
                })

        # 3. For split transactions, gross and net cannot violate the split equation
        if instance.is_split or instance.splits.exists():
            split_sum = sum((s.amount for s in instance.splits.all()), Decimal('0.00'))
            if 'gross_amount' in validated_data and validated_data['gross_amount'] != instance.gross_amount:
                raise serializers.ValidationError({'gross_amount': "Split bill total cannot be modified directly. Adjust splits or recreate."})
            if 'net_amount' in validated_data:
                expected_net = instance.gross_amount - split_sum
                if validated_data['net_amount'] != expected_net:
                    raise serializers.ValidationError({'net_amount': f"Net personal share for a split bill is locked to gross amount minus friend splits (\u0e3f{expected_net:,.2f})."})
            locked_tx = Transaction.objects.select_for_update().get(id=instance.id)
            return super().update(locked_tx, validated_data)

        # 4. For non-split transactions, handle amount delta under row-level lock
        locked_tx = Transaction.objects.select_for_update().get(id=instance.id)
        old_gross = locked_tx.gross_amount
        new_gross = validated_data.get('gross_amount', old_gross)
        diff = new_gross - old_gross

        if diff != Decimal('0.00'):
            locked_acc = Account.objects.select_for_update().get(id=locked_tx.account_id)
            if locked_tx.transaction_type == TransactionType.INFLOW:
                Account.objects.filter(id=locked_acc.id).update(
                    current_balance=models.F('current_balance') + diff,
                    updated_at=timezone.now()
                )
            elif locked_tx.transaction_type == TransactionType.OUTFLOW:
                from apps.ledger.models import AccountType
                if diff > Decimal('0.00') and locked_acc.account_type != AccountType.CREDIT_CARD:
                    if locked_acc.current_balance < diff:
                        raise serializers.ValidationError({
                            'gross_amount': f"Insufficient funds: {locked_acc.name} has balance \u0e3f{locked_acc.current_balance:,.2f}, cannot increase expense by \u0e3f{diff:,.2f}."
                        })
                Account.objects.filter(id=locked_acc.id).update(
                    current_balance=models.F('current_balance') - diff,
                    updated_at=timezone.now()
                )

        if not locked_tx.is_split and not locked_tx.splits.exists():
            if 'net_amount' not in validated_data:
                validated_data['net_amount'] = new_gross
            elif validated_data['net_amount'] > new_gross:
                raise serializers.ValidationError({'net_amount': "Net personal amount cannot exceed gross transaction amount."})

        return super().update(locked_tx, validated_data)


class CategoryBudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_parent = serializers.UUIDField(source='category.parent_id', read_only=True, allow_null=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=Decimal('0.00'))
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=Decimal('0.00'))
    usage_pct = serializers.FloatField(read_only=True, default=0.0)

    class Meta:
        model = CategoryBudget
        validators = []
        fields = [
            'id',
            'user',
            'category',
            'category_name',
            'category_parent',
            'category_icon',
            'period_month',
            'currency',
            'limit_amount',
            'spent_amount',
            'remaining_amount',
            'usage_pct',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def validate_currency(self, value):
        value = value.strip().upper()
        if not value.isascii() or not value.isalpha() or not 3 <= len(value) <= 5:
            raise serializers.ValidationError('Use a currency code.')
        return value

    def validate_limit_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Budget must be greater than zero.')
        return value

    def validate_category(self, value):
        if value.category_type != 'EXPENSE':
            raise serializers.ValidationError('Choose an expense category.')
        return value

    def validate_period_month(self, value):
        from .views import parse_month_param
        parse_month_param(value)
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        category = attrs.get('category', getattr(self.instance, 'category', None))
        period = attrs.get('period_month', getattr(self.instance, 'period_month', None))
        currency = attrs.get('currency', getattr(self.instance, 'currency', 'THB'))
        duplicate = CategoryBudget.objects.filter(user=user, category=category, period_month=period, currency=currency)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError('A budget already exists for this category, month and currency.')
        return attrs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['category'].queryset = Category.objects.filter(
                models.Q(is_system=True) | models.Q(user=request.user)
            )
