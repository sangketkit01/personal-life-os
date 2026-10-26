import re
from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.db.models import Sum, Q, Count, ProtectedError, Prefetch
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import viewsets, permissions, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.finance.models import ObligationType, ObligationStatus, PaymentHistory
from .models import (
    Account,
    AccountType,
    Category,
    Transaction,
    TransactionSplit,
    TransactionAttachment,
    CategoryBudget,
    TransactionType,
    CategoryType
)
from .serializers import (
    AccountSerializer,
    AccountTransferSerializer,
    CategorySerializer,
    TransactionSerializer,
    TransactionSplitSerializer,
    TransactionAttachmentSerializer,
    CategoryBudgetSerializer
)
from .services import AccountBalanceService, BillSplitService, CategorySeedService

MONTH_REGEX = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


def parse_month_param(month_str: str | None) -> tuple[int, int, str]:
    if not month_str:
        now = timezone.localtime()
        return now.year, now.month, now.strftime('%Y-%m')
    if not MONTH_REGEX.match(month_str):
        raise exceptions.ValidationError({'month': 'Month must be in format YYYY-MM (e.g. 2026-10).'})
    year, month = map(int, month_str.split('-'))
    return year, month, month_str


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AccountSerializer
    pagination_class = None

    def get_queryset(self):
        return Account.objects.filter(
            user=self.request.user
        ).annotate(
            transaction_count=Count('transactions')
        ).order_by('-is_default', 'name')

    def perform_create(self, serializer):
        if serializer.validated_data.get('is_default'):
            Account.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get('is_default'):
            Account.objects.filter(user=self.request.user, is_default=True).exclude(id=serializer.instance.id).update(is_default=False)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'error': 'Cannot delete an account that has transaction records. Please archive it instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def recalculate_balance(self, request, pk=None):
        account = self.get_object()
        new_balance = AccountBalanceService.recalculate_account_balance(account)
        return Response({
            'status': 'success',
            'account_id': str(account.id),
            'new_balance': str(new_balance)
        })

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        serializer = AccountTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            source_acc = Account.objects.get(id=data['source_account_id'], user=request.user)
            target_acc = Account.objects.get(id=data['target_account_id'], user=request.user)
        except Account.DoesNotExist:
            return Response(
                {'error': 'Source or target account not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            out_tx, in_tx = AccountBalanceService.execute_transfer(
                user=request.user,
                source_account=source_acc,
                target_account=target_acc,
                amount=data['amount'],
                transaction_date=data['transaction_date'],
                title=data.get('title', 'Transfer'),
                notes=data.get('notes', '')
            )
            return Response({
                'status': 'success',
                'outflow_transaction': TransactionSerializer(out_tx, context={'request': request}).data,
                'inflow_transaction': TransactionSerializer(in_tx, context={'request': request}).data,
                'source_new_balance': str(source_acc.current_balance),
                'target_new_balance': str(target_acc.current_balance)
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        # Automatically seed system categories if none exist in the database
        if not Category.objects.filter(is_system=True).exists():
            CategorySeedService.seed_defaults()

        cat_type = self.request.query_params.get('type')
        user_or_system = Q(is_system=True) | Q(user=self.request.user)
        sub_qs = Category.objects.filter(user_or_system).order_by('name')
        qs = Category.objects.filter(user_or_system).prefetch_related(
            Prefetch('subcategories', queryset=sub_qs)
        )
        if self.action == 'list':
            qs = qs.filter(parent__isnull=True)
        else:
            qs = qs.select_related('parent')

        if cat_type:
            qs = qs.filter(category_type=cat_type.upper())
        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_system=False)

    def perform_update(self, serializer):
        if serializer.instance.is_system:
            raise exceptions.PermissionDenied("System default categories cannot be modified.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_system:
            raise exceptions.PermissionDenied("System default categories cannot be deleted.")
        instance.delete()


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Transaction.objects.filter(user=user).select_related(
            'account', 'category', 'obligation', 'portfolio', 'workspace_project'
        ).prefetch_related('splits', 'attachments')

        # Filters
        account_id = self.request.query_params.get('account')
        category_id = self.request.query_params.get('category')
        tx_type = self.request.query_params.get('type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        is_split = self.request.query_params.get('is_split')
        search = self.request.query_params.get('search')

        if account_id:
            qs = qs.filter(account_id=account_id)
        if category_id:
            # Query category and any child subcategories
            qs = qs.filter(Q(category_id=category_id) | Q(category__parent_id=category_id))
        if tx_type:
            qs = qs.filter(transaction_type=tx_type.upper())
        if start_date:
            qs = qs.filter(transaction_date__gte=start_date)
        if end_date:
            qs = qs.filter(transaction_date__lte=end_date)
        if is_split is not None:
            qs = qs.filter(is_split=(is_split.lower() in ['true', '1']))
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(notes__icontains=search)
            )

        return qs.order_by('-transaction_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @db_transaction.atomic
    def perform_destroy(self, instance):
        self._cascade_delete_tx(instance)

    def _cascade_delete_tx(self, tx):
        # 1. If paired transfer, delete peer transaction atomically
        peer = tx.transfer_peer
        if peer:
            tx.transfer_peer = None
            tx.save(update_fields=['transfer_peer'])
            peer.transfer_peer = None
            peer.save(update_fields=['transfer_peer'])
            self._cascade_delete_tx(peer)

        # 2. If this transaction was a settlement for split(s), revert split state
        settled_splits = list(tx.settled_splits.select_for_update().all())
        for s in settled_splits:
            s.is_settled = False
            s.settled_at = None
            s.settlement_transaction = None
            s.save(update_fields=['is_settled', 'settled_at', 'settlement_transaction'])
            if s.debtor_obligation:
                ob = s.debtor_obligation
                ob.status = ObligationStatus.ACTIVE
                ob_meta = ob.metadata or {}
                cur_rem = Decimal(str(ob_meta.get('remaining_balance', 0)))
                new_rem = min(ob.amount, cur_rem + tx.gross_amount)
                ob_meta['remaining_balance'] = float(round(new_rem, 2))
                ob.metadata = ob_meta
                ob.save(update_fields=['status', 'metadata'])
                if tx.payment_history_id:
                    PaymentHistory.objects.filter(id=tx.payment_history_id).delete()
                    tx.payment_history_id = None
                    tx.payment_history = None

        # 3. If this transaction was a master split transaction, clean up child splits' auto-generated radar debtors
        if tx.is_split or tx.splits.exists():
            if tx.splits.filter(is_settled=True).exists():
                raise exceptions.ValidationError(
                    "Cannot delete split transaction because one or more splits have already been settled. Revert or delete the settlement transactions first."
                )
            for s in tx.splits.all():
                if s.debtor_obligation:
                    debtor_ob = s.debtor_obligation
                    s.debtor_obligation = None
                    s.save(update_fields=['debtor_obligation'])
                    debtor_ob.delete()

        # 4. If this transaction was linked to an obligation payment, cascade reverse obligation status/term
        hist = tx.payment_history
        if hist:
            ob = hist.obligation or tx.obligation
            if ob:
                h_meta = hist.metadata or {}
                import datetime

                # BNPL Account Reversal (revert sub-orders using recorded advances)
                if getattr(ob, 'subtype', None) == 'BNPL_ACCOUNT' or ob.metadata.get('subtype') == 'BNPL_ACCOUNT':
                    advances = h_meta.get('sub_order_advances', [])
                    from apps.finance.models import FinancialObligation
                    for item in advances:
                        try:
                            sub_order = FinancialObligation.objects.get(id=item['sub_order_id'])
                            s_meta = sub_order.metadata or {}
                            s_meta['current_term'] = item['prev_term']
                            sub_order.metadata = s_meta
                            sub_order.status = item.get('prev_status', ObligationStatus.ACTIVE)
                            if item.get('prev_due_date'):
                                sub_order.due_date = datetime.date.fromisoformat(item['prev_due_date'])
                            else:
                                sub_order.due_date = None
                            sub_order.save()
                        except FinancialObligation.DoesNotExist:
                            pass

                    # Refresh parent BNPL next due date
                    from apps.finance.strategies import ObligationStrategyFactory
                    parent_strategy = ObligationStrategyFactory.get_strategy(ob.type)
                    p_summary = parent_strategy.get_summary(ob)
                    if p_summary.get('next_due_date'):
                        try:
                            ob.due_date = datetime.date.fromisoformat(p_summary['next_due_date'])
                        except Exception:
                            pass
                    ob.save()

                elif ob.type == ObligationType.INSTALLMENT:
                    cur_t = int(ob.metadata.get('current_term', 1))
                    new_t = max(0, cur_t - 1)
                    ob.metadata['current_term'] = new_t
                    if new_t < int(ob.metadata.get('total_terms', 1)):
                        ob.status = ObligationStatus.ACTIVE
                    if h_meta.get('prev_due_date'):
                        ob.due_date = datetime.date.fromisoformat(h_meta['prev_due_date'])
                    ob.save(update_fields=['metadata', 'status', 'due_date'])

                elif ob.type == ObligationType.DEBT:
                    cur_rem = Decimal(str(ob.metadata.get('remaining_balance', 0)))
                    new_rem = min(ob.amount, cur_rem + tx.gross_amount)
                    ob.metadata['remaining_balance'] = float(round(new_rem, 2))
                    if new_rem > Decimal('0.00'):
                        ob.status = ObligationStatus.ACTIVE
                    ob.save(update_fields=['metadata', 'status'])

                elif ob.type == ObligationType.SUBSCRIPTION:
                    if h_meta.get('prev_due_date'):
                        ob.due_date = datetime.date.fromisoformat(h_meta['prev_due_date'])
                        ob.save(update_fields=['due_date'])

            if hist:
                hist.delete()

        # 5. Revert account balance atomically with row lock
        locked_acc = Account.objects.select_for_update().get(id=tx.account_id)
        if tx.transaction_type == TransactionType.INFLOW:
            Account.objects.filter(id=locked_acc.id).update(
                current_balance=models.F('current_balance') - tx.gross_amount,
                updated_at=timezone.now()
            )
        elif tx.transaction_type == TransactionType.OUTFLOW:
            Account.objects.filter(id=locked_acc.id).update(
                current_balance=models.F('current_balance') + tx.gross_amount,
                updated_at=timezone.now()
            )

        # 6. Delete transaction
        tx.delete()

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Calculates executive monthly cashflow metrics:
        - Total Inflow
        - Total Gross Outflow vs Net Outflow
        - Net Cash Flow (Pure pocket cashflow: Total Inflow - Total Gross Outflow)
        - Total Liquid Balance across accounts
        - Pending Shared Split Receivables
        """
        user = request.user
        year, month, period_month = parse_month_param(request.query_params.get('month'))
        currency = request.query_params.get('currency')
        if not currency:
            currency = (
                Account.objects.filter(user=user, is_default=True).values_list('currency', flat=True).first()
                or Account.objects.filter(user=user).values_list('currency', flat=True).first()
                or 'THB'
            )
        currency = currency.strip().upper()

        tx_qs = Transaction.objects.filter(
            user=user,
            account__currency=currency,
            transaction_date__year=year,
            transaction_date__month=month
        )

        # Inflows (excluding internal transfers)
        total_inflow = tx_qs.filter(
            transaction_type=TransactionType.INFLOW,
            transfer_destination__isnull=True,
            transfer_peer__isnull=True
        ).aggregate(total=Coalesce(Sum('gross_amount'), Decimal('0.00')))['total']

        # Outflows (excluding internal transfers)
        outflow_agg = tx_qs.filter(
            transaction_type=TransactionType.OUTFLOW,
            transfer_destination__isnull=True,
            transfer_peer__isnull=True
        ).aggregate(
            gross=Coalesce(Sum('gross_amount'), Decimal('0.00')),
            net=Coalesce(Sum('net_amount'), Decimal('0.00'))
        )
        total_gross_outflow = outflow_agg['gross']
        total_net_outflow = outflow_agg['net']

        # Pure pocket cash flow: Inflow minus Gross Outflow
        net_cash_flow = total_inflow - total_gross_outflow

        # Total balances across active accounts
        acc_qs = Account.objects.filter(user=user, is_archived=False, currency=currency)

        total_liquid = acc_qs.filter(
            account_type__in=[AccountType.BANK, AccountType.E_WALLET, AccountType.CASH, AccountType.BROKERAGE_CASH]
        ).aggregate(total=Coalesce(Sum('current_balance'), Decimal('0.00')))['total']

        # Credit debt reflects only negative card balances (positive balance is not debt)
        total_credit_debt = acc_qs.filter(
            account_type=AccountType.CREDIT_CARD,
            current_balance__lt=Decimal('0.00')
        ).aggregate(total=Coalesce(Sum('current_balance'), Decimal('0.00')))['total']
        total_credit_debt = abs(total_credit_debt)

        # Pending receivables from splits
        splits_qs = TransactionSplit.objects.filter(
            transaction__user=user,
            transaction__account__currency=currency,
            is_settled=False
        )

        pending_splits = splits_qs.aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00')),
            count=Count('id')
        )

        return Response({
            'period_month': period_month,
            'currency': currency,
            'total_inflow': str(total_inflow),
            'total_gross_outflow': str(total_gross_outflow),
            'total_net_outflow': str(total_net_outflow),
            'net_cash_flow': str(net_cash_flow),
            'total_liquid_balance': str(total_liquid),
            'total_credit_debt': str(total_credit_debt),
            'pending_splits_amount': str(pending_splits['total']),
            'pending_splits_count': pending_splits['count']
        })


class TransactionSplitViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSplitSerializer

    def get_queryset(self):
        qs = TransactionSplit.objects.filter(
            transaction__user=self.request.user
        ).select_related('transaction', 'debtor_obligation')

        status_param = self.request.query_params.get('status')
        if status_param == 'PENDING':
            qs = qs.filter(is_settled=False)
        elif status_param == 'SETTLED':
            qs = qs.filter(is_settled=True)

        return qs.order_by('is_settled', 'counterparty_name')

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        split = self.get_object()
        account_id = request.data.get('deposit_account_id')
        if not account_id:
            return Response(
                {'error': 'deposit_account_id is required to deposit repayment.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            deposit_acc = Account.objects.get(id=account_id, user=request.user)
        except Account.DoesNotExist:
            return Response(
                {'error': 'Deposit account not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            inflow_tx = BillSplitService.settle_split(
                split=split,
                deposit_account=deposit_acc,
                settlement_date=request.data.get('settlement_date'),
                settlement_title=request.data.get('settlement_title', '')
            )
            return Response({
                'status': 'success',
                'split_id': str(split.id),
                'inflow_transaction_id': str(inflow_tx.id),
                'account_new_balance': str(deposit_acc.current_balance)
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CategoryBudgetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CategoryBudgetSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return CategoryBudget.objects.filter(user=user).select_related('category')

    def list(self, request, *args, **kwargs):
        user = request.user
        year, month, period_month = parse_month_param(request.query_params.get('month'))

        budgets = list(self.get_queryset().filter(period_month=period_month))
        if not budgets:
            return Response([])

        # Batch resolution: map budget categories and their subcategories to avoid N+1 queries
        budget_cat_map = {}
        all_relevant_cat_ids = set()
        for b in budgets:
            sub_ids = list(b.category.subcategories.values_list('id', flat=True))
            cat_family = [b.category_id] + sub_ids
            budget_cat_map[b.id] = cat_family
            all_relevant_cat_ids.update(cat_family)

        # Single batch aggregation query for all budget categories
        spent_records = Transaction.objects.filter(
            user=user,
            category_id__in=all_relevant_cat_ids,
            transaction_type=TransactionType.OUTFLOW,
            transaction_date__year=year,
            transaction_date__month=month
        ).values('category_id').annotate(total=Coalesce(Sum('net_amount'), Decimal('0.00')))

        spent_by_cat = {r['category_id']: r['total'] for r in spent_records}

        results = []
        for b in budgets:
            cat_family = budget_cat_map[b.id]
            spent = sum((spent_by_cat.get(cid, Decimal('0.00')) for cid in cat_family), Decimal('0.00'))

            b.spent_amount = spent
            b.remaining_amount = b.limit_amount - spent
            b.usage_pct = float(round((spent / b.limit_amount) * 100, 2)) if b.limit_amount > 0 else 0.0
            results.append(b)

        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
