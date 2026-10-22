from decimal import Decimal
from django.db import models, transaction as db_transaction
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
            'notes'
        ]
        read_only_fields = ['id', 'transaction', 'is_settled', 'settled_at', 'settlement_transaction', 'debtor_obligation']


class TransactionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionAttachment
        fields = [
            'id',
            'transaction',
            'file',
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
            'splits',
            'splits_payload',
            'auto_create_radar_debtors',
            'attachments',
            'obligation',
            'portfolio',
            'workspace_project',
            'transfer_destination',
            'transfer_peer',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'transfer_peer', 'created_at', 'updated_at']

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

    @db_transaction.atomic
    def create(self, validated_data):
        splits_payload = validated_data.pop('splits_payload', None)
        auto_create_debtors = validated_data.pop('auto_create_radar_debtors', True)
        user = validated_data.get('user')
        account = validated_data.get('account')
        gross_amount = validated_data.get('gross_amount')
        net_amount = validated_data.get('net_amount', gross_amount)

        if splits_payload and len(splits_payload) > 0:
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
                splits_data=splits_payload,
                auto_create_radar_debtors=auto_create_debtors,
                notes=notes,
                workspace_project=workspace_project
            )

        # Normal single transaction - lock account row
        locked_acc = Account.objects.select_for_update().get(id=account.id, user=user)
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

        # 2. For split transactions, amount cannot be directly edited via master PUT/PATCH
        if instance.is_split:
            if 'gross_amount' in validated_data and validated_data['gross_amount'] != instance.gross_amount:
                raise serializers.ValidationError({'gross_amount': "Split bill total cannot be modified directly. Adjust splits or recreate."})
            return super().update(instance, validated_data)

        # 3. For non-split transactions, handle amount delta
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
