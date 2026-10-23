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
    subcategories = CategorySubSerializer(many=True, read_only=True)

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
    account_type = serializers.CharField(source='account.account_type', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    splits = TransactionSplitSerializer(many=True, read_only=True)
    attachments = TransactionAttachmentSerializer(many=True, read_only=True)

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
            'account_type',
            'transaction_type',
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

        gross = attrs.get('gross_amount', getattr(self.instance, 'gross_amount', None))
        net = attrs.get('net_amount', getattr(self.instance, 'net_amount', gross))

        if gross is not None and gross <= Decimal('0.00'):
            raise serializers.ValidationError({'gross_amount': "Gross amount must be strictly greater than 0."})

        if net is not None and net < Decimal('0.00'):
            raise serializers.ValidationError({'net_amount': "Net amount cannot be negative."})

        if gross is not None and net is not None and net > gross:
            raise serializers.ValidationError({'net_amount': "Net personal amount cannot exceed gross transaction amount."})

        transfer_dest = attrs.get('transfer_destination')
        tx_type = attrs.get('transaction_type', getattr(self.instance, 'transaction_type', None))

        if not self.instance and tx_type == TransactionType.TRANSFER:
            raise serializers.ValidationError({
                'transaction_type': "Direct creation of 'TRANSFER' transactions is not permitted. Use /api/ledger/accounts/transfer/ instead."
            })

        is_split = attrs.get('is_split', getattr(self.instance, 'is_split', False))
        if not is_split and gross is not None:
            attrs['net_amount'] = gross

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

            return BillSplitService.create_split_transaction(
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

        # Normal single transaction - lock account row
        from apps.ledger.models import AccountType
        locked_acc = Account.objects.select_for_update().get(id=account.id, user=user)

        # Overdraft check for non-credit accounts
        if locked_acc.account_type != AccountType.CREDIT_CARD and validated_data.get('transaction_type') == TransactionType.OUTFLOW:
            if locked_acc.current_balance < gross_amount:
                raise serializers.ValidationError({
                    'gross_amount': f"Insufficient funds: {locked_acc.name} has balance ฿{locked_acc.current_balance:,.2f}, but payment requires ฿{gross_amount:,.2f}."
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

        # 2. For paired transfers, disallow directly mutating amount via transaction PATCH
        if instance.transfer_peer or instance.transfer_destination:
            if 'gross_amount' in validated_data and validated_data['gross_amount'] != instance.gross_amount:
                raise serializers.ValidationError({'gross_amount': "Transfer amount cannot be modified directly. Delete transfer and create a new one."})

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
                    raise serializers.ValidationError({'net_amount': f"Net personal share for a split bill is locked to gross amount minus friend splits (฿{expected_net:,.2f})."})
            return super().update(instance, validated_data)

        # 4. For non-split transactions, handle amount delta
        old_gross = instance.gross_amount
        new_gross = validated_data.get('gross_amount', old_gross)
        diff = new_gross - old_gross

        if diff != Decimal('0.00'):
            locked_acc = Account.objects.select_for_update().get(id=instance.account_id)
            if instance.transaction_type == TransactionType.INFLOW:
                Account.objects.filter(id=locked_acc.id).update(
                    current_balance=models.F('current_balance') + diff,
                    updated_at=timezone.now()
                )
            elif instance.transaction_type == TransactionType.OUTFLOW:
                from apps.ledger.models import AccountType
                if diff > Decimal('0.00') and locked_acc.account_type != AccountType.CREDIT_CARD:
                    if locked_acc.current_balance < diff:
                        raise serializers.ValidationError({
                            'gross_amount': f"Insufficient funds: {locked_acc.name} has balance ฿{locked_acc.current_balance:,.2f}, cannot increase expense by ฿{diff:,.2f}."
                        })
                Account.objects.filter(id=locked_acc.id).update(
                    current_balance=models.F('current_balance') - diff,
                    updated_at=timezone.now()
                )
            if 'net_amount' not in validated_data:
                validated_data['net_amount'] = new_gross

        return super().update(instance, validated_data)


class CategoryBudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=Decimal('0.00'))
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=Decimal('0.00'))
    usage_pct = serializers.FloatField(read_only=True, default=0.0)

    class Meta:
        model = CategoryBudget
        fields = [
            'id',
            'user',
            'category',
            'category_name',
            'category_icon',
            'period_month',
            'limit_amount',
            'spent_amount',
            'remaining_amount',
            'usage_pct',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['category'].queryset = Category.objects.filter(
                models.Q(is_system=True) | models.Q(user=request.user)
            )
