from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.utils import timezone
from rest_framework import viewsets, views, permissions, status, response
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import FinancialObligation, ObligationType, ObligationStatus, ObligationAttachment, PaymentHistory
from .serializers import (
    FinancialObligationSerializer,
    PayObligationSerializer,
    PaymentHistorySerializer,
    ObligationAttachmentSerializer
)
from .strategies import ObligationStrategyFactory
from .services import get_financial_overview


class FinancialOverviewView(views.APIView):
    """Monthly Financial Overview API (Burn Rate, Due in 7 Days, Free Trials)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = get_financial_overview(request.user)
        return response.Response(data)


ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.docx', '.xlsx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_uploaded_file(file_obj):
    import os
    if not file_obj:
        return
    if getattr(file_obj, 'size', 0) > MAX_FILE_SIZE:
        raise ValueError("File size cannot exceed 10MB.")
    ext = os.path.splitext(getattr(file_obj, 'name', ''))[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '{ext}' is not allowed. (Allowed: PDF, DOCX, XLSX, Images)")


class FinancialObligationViewSet(viewsets.ModelViewSet):
    """
    CRUD and Actions for all financial obligations:
    - Scoped strictly to current authenticated user.
    - Supports 'pay', 'cancel-trial', 'schedule', and 'debtors' actions.
    """
    serializer_class = FinancialObligationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q

        # Scoped strictly to user with prefetching to avoid N+1 queries
        qs = FinancialObligation.objects.filter(user=self.request.user).prefetch_related(
            'payment_histories__attachments',
            'attachments',
            'sub_orders'
        )

        # Query parameter filtering: ?type=INSTALLMENT&status=ACTIVE&subtype=BNPL_ACCOUNT&direction=INFLOW&search=...&ordering=...
        type_param = self.request.query_params.get('type')
        status_param = self.request.query_params.get('status')
        subtype_param = self.request.query_params.get('subtype')
        direction_param = self.request.query_params.get('direction')
        parent_param = self.request.query_params.get('parent')
        search_param = self.request.query_params.get('search') or self.request.query_params.get('q')
        ordering_param = self.request.query_params.get('ordering')

        if type_param:
            qs = qs.filter(type=type_param.upper())
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if subtype_param:
            qs = qs.filter(subtype=subtype_param.upper())
        if direction_param:
            qs = qs.filter(direction=direction_param.upper())
        if parent_param == 'none':
            qs = qs.filter(parent__isnull=True)
        elif parent_param:
            qs = qs.filter(parent_id=parent_param)
        if search_param:
            s = search_param.strip()
            qs = qs.filter(
                Q(title__icontains=s) |
                Q(metadata__lender__icontains=s) |
                Q(metadata__counterparty__icontains=s) |
                Q(metadata__provider__icontains=s) |
                Q(metadata__vehicle_model__icontains=s)
            )
        if ordering_param:
            allowed_orderings = {
                'due_date', '-due_date',
                'created_at', '-created_at',
                'amount', '-amount',
                'title', '-title'
            }
            if ordering_param in allowed_orderings:
                qs = qs.order_by(ordering_param)

        return qs

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def pay(self, request, pk=None):
        """Record settlement, pay installment term, or settle debt balance."""
        obligation = self.get_object()
        serializer = PayObligationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        paid_amount = serializer.validated_data.get('paid_amount')
        term_number = serializer.validated_data.get('term_number')
        note = serializer.validated_data.get('note', '')
        slip_file = serializer.validated_data.get('slip_file')
        drive_file_id = serializer.validated_data.get('drive_file_id', '')
        drive_view_link = serializer.validated_data.get('drive_view_link', '')
        drive_download_link = serializer.validated_data.get('drive_download_link', '')

        # Validate legacy file upload if present
        if slip_file:
            try:
                validate_uploaded_file(slip_file)
            except ValueError as ve:
                return response.Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve exact payment amount based on obligation type and domain strategy
        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        statement_month = serializer.validated_data.get('statement_month')

        if obligation.subtype == 'BNPL_ACCOUNT':
            summary_before = strategy.get_summary(obligation)
            timeline = summary_before.get('statement_timeline', [])
            current_statement = summary_before.get('current_statement')

            target_statement = None
            if statement_month:
                target_statement = next((s for s in timeline if s.get('statement_month') == statement_month), None)
                if not target_statement:
                    return response.Response({
                        'detail': f"No billing statement found for month {statement_month}."
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                target_statement = current_statement

            if not target_statement:
                return response.Response({
                    'detail': 'There is no outstanding statement bill to pay.'
                }, status=status.HTTP_400_BAD_REQUEST)

            statement_due = Decimal(str(target_statement.get('total_due', '0.00')))
            target_month_key = target_statement.get('statement_month')

            if statement_due <= Decimal('0.00'):
                return response.Response({'detail': 'There is no outstanding statement bill to pay.'}, status=status.HTTP_400_BAD_REQUEST)

            if paid_amount is None:
                actual_paid = statement_due
            else:
                actual_paid = Decimal(str(paid_amount))
                if actual_paid != statement_due:
                    return response.Response({
                        'detail': f"Partial payment is not supported. Full statement amount of ฿{statement_due:,.2f} is required for {target_month_key}."
                    }, status=status.HTTP_400_BAD_REQUEST)

            statement_month = target_month_key

        elif obligation.type == ObligationType.INSTALLMENT:
            if obligation.status == ObligationStatus.COMPLETED:
                return response.Response({'detail': 'This installment contract is already fully completed.'}, status=status.HTTP_400_BAD_REQUEST)
            scheduled_amount = obligation.amount
            if paid_amount is None:
                actual_paid = scheduled_amount
            else:
                actual_paid = Decimal(str(paid_amount))
                if actual_paid != scheduled_amount:
                    return response.Response({
                        'detail': f"Partial payment is not supported. Scheduled installment amount of ฿{scheduled_amount:,.2f} is required."
                    }, status=status.HTTP_400_BAD_REQUEST)

        elif obligation.type == ObligationType.SUBSCRIPTION:
            scheduled_amount = obligation.amount
            if paid_amount is None:
                actual_paid = scheduled_amount
            else:
                actual_paid = Decimal(str(paid_amount))
                if actual_paid != scheduled_amount:
                    return response.Response({
                        'detail': f"Full subscription payment of ฿{scheduled_amount:,.2f} is required."
                    }, status=status.HTTP_400_BAD_REQUEST)

        elif obligation.type == ObligationType.DEBT:
            meta = obligation.metadata or {}
            remaining_balance_raw = meta.get('remaining_balance')
            cur_rem = Decimal(str(remaining_balance_raw)) if remaining_balance_raw is not None else obligation.amount
            if cur_rem <= Decimal('0.00') or obligation.status == ObligationStatus.COMPLETED:
                return response.Response({'detail': 'This debt obligation is already fully settled.'}, status=status.HTTP_400_BAD_REQUEST)
            if paid_amount is None:
                actual_paid = cur_rem
            else:
                actual_paid = Decimal(str(paid_amount))
                if actual_paid <= Decimal('0.00'):
                    return response.Response({'detail': 'Payment amount must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
                if actual_paid > cur_rem:
                    return response.Response({
                        'detail': f"Payment amount of ฿{actual_paid:,.2f} exceeds remaining debt balance of ฿{cur_rem:,.2f}."
                    }, status=status.HTTP_400_BAD_REQUEST)
        else:
            actual_paid = Decimal(str(paid_amount if paid_amount is not None else obligation.amount))

        # Pre-flight check on Ledger account balance
        account_id = serializer.validated_data.get('account_id')
        account = None

        if account_id:
            from apps.ledger.models import Account, AccountType
            try:
                account = Account.objects.select_for_update().get(id=account_id, user=request.user)
            except Account.DoesNotExist:
                return response.Response({'detail': 'Target cash flow account not found.'}, status=status.HTTP_404_NOT_FOUND)

            if account.currency != obligation.currency:
                return response.Response({
                    'detail': f"Currency mismatch: Account currency ({account.currency}) does not match obligation currency ({obligation.currency})."
                }, status=status.HTTP_400_BAD_REQUEST)

            if obligation.direction != 'INFLOW':
                if account.account_type != AccountType.CREDIT_CARD:
                    if account.current_balance < actual_paid:
                        return response.Response({
                            'detail': f"Insufficient funds: {account.name} has balance ฿{account.current_balance:,.2f}, but payment requires ฿{actual_paid:,.2f}."
                        }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with db_transaction.atomic():
                obligation = FinancialObligation.objects.select_for_update().get(id=obligation.id, user=request.user)
                summary = strategy.on_paid(
                    obligation=obligation,
                    paid_amount=actual_paid,
                    term_number=term_number,
                    note=note,
                    statement_month=statement_month
                )

                payment_record = None
                if summary.get('payment_id'):
                    payment_record = PaymentHistory.objects.filter(id=summary['payment_id']).first()

                # Link Google Drive or legacy slip attachment to payment record
                if payment_record and (drive_file_id or slip_file):
                    ObligationAttachment.objects.create(
                        user=request.user,
                        obligation=obligation,
                        payment_history=payment_record,
                        file=slip_file if slip_file else None,
                        drive_file_id=drive_file_id,
                        drive_view_link=drive_view_link,
                        drive_download_link=drive_download_link,
                        file_name=serializer.validated_data.get('file_name') or getattr(slip_file, 'name', 'payment_slip.jpg'),
                        file_type='SLIP',
                        file_size=serializer.validated_data.get('file_size') or getattr(slip_file, 'size', 0)
                    )

                # Sync to Cash Flow Ledger if account was selected
                ledger_tx = None
                if account:
                    from apps.ledger.models import Transaction, TransactionType

                    if obligation.direction == 'INFLOW':
                        tx_type = TransactionType.INFLOW
                        if obligation.project_id or (obligation.metadata or {}).get('source_type') == 'MA_CONTRACT':
                            tx_title = f"MA / Project Income: {obligation.title}"
                        else:
                            tx_title = f"Debt Repayment: {obligation.title}"
                        Account.objects.filter(id=account.id).update(
                            current_balance=models.F('current_balance') + actual_paid,
                            updated_at=timezone.now()
                        )
                    else:
                        tx_type = TransactionType.OUTFLOW
                        tx_title = f"Settlement: {obligation.title}"
                        Account.objects.filter(id=account.id).update(
                            current_balance=models.F('current_balance') - actual_paid,
                            updated_at=timezone.now()
                        )

                    account.refresh_from_db(fields=['current_balance', 'updated_at'])

                    ledger_tx = Transaction.objects.create(
                        user=request.user,
                        account=account,
                        transaction_type=tx_type,
                        gross_amount=actual_paid,
                        net_amount=actual_paid,
                        title=tx_title,
                        notes=note or f"Auto-settled from Financial Radar ({obligation.get_type_display()})",
                        transaction_date=timezone.now().date(),
                        obligation=obligation,
                        payment_history=payment_record
                    )

                # Sync with linked Split Bill ONLY if obligation is COMPLETED
                obligation.refresh_from_db()

                # Keep workspace billing mirrors (MA contract / infra asset) in
                # step with the freshly advanced obligation due date.
                from apps.workspace.services import sync_billing_dates_from_obligation
                sync_billing_dates_from_obligation(obligation)

                if obligation.status == ObligationStatus.COMPLETED:
                    unsettled_splits = obligation.origin_split.filter(is_settled=False)
                    for s in unsettled_splits:
                        s.is_settled = True
                        s.settled_at = timezone.now()
                        s.settlement_transaction = ledger_tx
                        s.save(update_fields=['is_settled', 'settled_at', 'settlement_transaction'])

        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Refresh obligation data to return
        obligation.refresh_from_db()
        try:
            log_activity(obligation.user, 'FINANCE', 'PAY_BILL', f'Payment of {actual_paid} {obligation.currency} recorded for {obligation.title}', request=request)
        except Exception:
            pass

        return response.Response({
            'message': 'Payment recorded successfully.',
            'obligation': FinancialObligationSerializer(obligation, context={'request': request}).data,
            'summary': summary
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='upload-attachment')
    def upload_attachment(self, request, pk=None):
        """Upload contract, receipt, slip, or billing statement attachment."""
        obligation = self.get_object()
        drive_file_id = request.data.get('drive_file_id')
        file_obj = request.FILES.get('file')

        if not drive_file_id and not file_obj:
            return response.Response({'detail': 'Please select a file or Google Drive document.'}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj:
            try:
                validate_uploaded_file(file_obj)
            except ValueError as ve:
                return response.Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        file_type = request.data.get('file_type', 'OTHER')
        payment_id = request.data.get('payment_history')
        payment_history = None
        if payment_id:
            payment_history = obligation.payment_histories.filter(id=payment_id).first()

        if drive_file_id:
            drive_view_link = request.data.get('drive_view_link', '')
            drive_download_link = request.data.get('drive_download_link', '')
            file_name = request.data.get('file_name', 'google_drive_document')
            file_size = int(request.data.get('file_size', 0))
            attachment = ObligationAttachment.objects.create(
                user=request.user,
                obligation=obligation,
                payment_history=payment_history,
                file=None,
                drive_file_id=drive_file_id,
                drive_view_link=drive_view_link,
                drive_download_link=drive_download_link,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size
            )
            return response.Response(
                ObligationAttachmentSerializer(attachment, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        attachment = ObligationAttachment.objects.create(
            user=request.user,
            obligation=obligation,
            payment_history=payment_history,
            file=file_obj,
            file_name=getattr(file_obj, 'name', 'unnamed_file'),
            file_type=file_type,
            file_size=getattr(file_obj, 'size', 0)
        )
        return response.Response(
            ObligationAttachmentSerializer(attachment, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='cancel-trial')
    def cancel_trial(self, request, pk=None):
        """Action to cancel a free trial obligation"""
        obligation = self.get_object()
        if obligation.type != ObligationType.FREE_TRIAL:
            return response.Response(
                {'detail': 'This action is only applicable to free trials.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        summary = strategy.cancel(obligation)
        obligation.refresh_from_db()
        log_activity(obligation.user, 'FINANCE', 'CANCEL_TRIAL', f'Cancelled free trial: {obligation.title}', request=request)

        return response.Response({
            'message': 'Free trial cancelled successfully (status changed to CANCELLED).',
            'obligation': FinancialObligationSerializer(obligation).data,
            'summary': summary
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='convert-to-subscription')
    def convert_to_subscription(self, request, pk=None):
        """Action to convert a free trial into an active recurring subscription"""
        from decimal import Decimal
        from .models import ObligationType, ObligationStatus
        obligation = self.get_object()
        if obligation.type != ObligationType.FREE_TRIAL:
            return response.Response(
                {'detail': 'Only free trials can be converted to recurring subscriptions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        meta = obligation.metadata or {}
        billing_cycle = request.data.get('billing_cycle') or meta.get('billing_cycle') or 'MONTHLY'
        raw_amount = request.data.get('amount') or meta.get('auto_renew_cost') or obligation.amount
        try:
            amount = Decimal(str(raw_amount))
            if amount < Decimal('0.00'):
                return response.Response({'detail': 'Subscription amount cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return response.Response({'detail': 'Invalid amount value.'}, status=status.HTTP_400_BAD_REQUEST)

        obligation.type = ObligationType.SUBSCRIPTION
        obligation.status = ObligationStatus.ACTIVE
        obligation.amount = amount
        if obligation.due_date and not obligation.billing_day:
            obligation.billing_day = obligation.due_date.day
        meta['billing_cycle'] = billing_cycle
        obligation.metadata = meta
        obligation.save()

        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        summary = strategy.get_summary(obligation)
        log_activity(obligation.user, 'FINANCE', 'CONVERT_SUBSCRIPTION', f'Converted free trial {obligation.title} to subscription', request=request)

        return response.Response({
            'message': 'Successfully converted trial to recurring subscription',
            'obligation': FinancialObligationSerializer(obligation, context={'request': request}).data,
            'summary': summary
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Retrieve full payment history for this obligation."""
        obligation = self.get_object()
        histories = obligation.payment_histories.all().order_by('-paid_at')
        return response.Response(PaymentHistorySerializer(histories, many=True).data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Generate detailed amortization schedule (terms 1 to N)."""
        from decimal import Decimal
        import datetime
        from dateutil.relativedelta import relativedelta

        obligation = self.get_object()
        if obligation.type != ObligationType.INSTALLMENT:
            return response.Response(
                {'detail': 'Schedule is only available for installment obligations.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        metadata = obligation.metadata or {}
        total_terms = int(metadata.get('total_terms', 1))
        current_term = int(metadata.get('current_term', 0))

        raw_fa = metadata.get('financed_amount') or metadata.get('total_principal')
        if raw_fa:
            financed_amount = Decimal(str(raw_fa))
        else:
            financed_amount = obligation.amount * Decimal(str(max(1, total_terms)))

        if financed_amount <= Decimal('0.00'):
            financed_amount = obligation.amount * Decimal(str(max(1, total_terms)))

        flat_rate_pa = Decimal(str(metadata.get('flat_rate_pa', '0.00')))
        monthly_installment = obligation.amount
        if monthly_installment <= Decimal('0.00') and total_terms > 0:
            monthly_installment = (financed_amount / Decimal(str(total_terms))).quantize(Decimal('0.01'))

        # Calculate monthly principal and interest component
        if total_terms > 0 and flat_rate_pa > Decimal('0'):
            total_years = Decimal(str(total_terms)) / Decimal('12.0')
            total_interest = financed_amount * (flat_rate_pa / Decimal('100.0')) * total_years
            monthly_interest = (total_interest / Decimal(str(total_terms))).quantize(Decimal('0.01'))
            monthly_principal = (monthly_installment - monthly_interest).quantize(Decimal('0.01'))
        else:
            monthly_interest = Decimal('0.00')
            monthly_principal = (financed_amount / Decimal(str(max(1, total_terms)))).quantize(Decimal('0.01')) if total_terms > 0 else monthly_installment

        base_date = obligation.due_date or datetime.date.today()
        start_date = base_date - relativedelta(months=current_term)

        schedule_list = []
        running_principal = financed_amount

        for term in range(1, total_terms + 1):
            term_date = start_date + relativedelta(months=term - 1)
            is_paid = term <= current_term
            is_current = term == current_term + 1
            if term == total_terms:
                term_p = running_principal
                running_principal = Decimal('0.00')
            else:
                term_p = min(running_principal, monthly_principal)
                running_principal = max(Decimal('0.00'), running_principal - term_p)

            term_inst = (term_p + monthly_interest) if (term_p + monthly_interest) > Decimal('0.00') else monthly_installment
            schedule_list.append({
                'term_number': term,
                'total_terms': total_terms,
                'due_date': term_date.isoformat(),
                'installment_amount': float(term_inst),
                'principal': float(term_p),
                'interest': float(monthly_interest),
                'remaining_principal': float(running_principal),
                'status': 'PAID' if is_paid else ('DUE' if is_current else 'UPCOMING')
            })

        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        summary = strategy.get_summary(obligation)

        return response.Response({
            'obligation_id': str(obligation.id),
            'title': obligation.title,
            'total_terms': total_terms,
            'current_term': current_term,
            'monthly_installment': float(monthly_installment),
            'summary': summary,
            'schedule': schedule_list
        })

    @action(detail=False, methods=['get'])
    def debtors(self, request):
        """Debtors Directory endpoint returning outstanding balance and repayment history."""
        from decimal import Decimal
        from .models import ObligationStatus

        debts = FinancialObligation.objects.filter(
            user=request.user,
            type=ObligationType.DEBT
        ).prefetch_related('payment_histories')

        debtor_map = {}
        for debt in debts:
            meta = debt.metadata or {}
            name = meta.get('counterparty') or meta.get('debtor_name') or debt.title
            name = name.strip()
            direction = debt.direction or 'OUTFLOW'

            key = f"{direction}_{name.lower()}"
            if key not in debtor_map:
                debtor_map[key] = {
                    'debtor_name': name,
                    'direction': direction,
                    'total_principal': Decimal('0.00'),
                    'total_repaid': Decimal('0.00'),
                    'outstanding_balance': Decimal('0.00'),
                    'active_count': 0,
                    'obligations': []
                }

            entry = debtor_map[key]
            entry['total_principal'] += debt.amount
            if debt.status == ObligationStatus.ACTIVE:
                entry['active_count'] += 1

            strategy = ObligationStrategyFactory.get_strategy(debt.type)
            summary = strategy.get_summary(debt)
            remaining = Decimal(str(summary.get('remaining_balance', debt.amount)))
            entry['outstanding_balance'] += remaining

            repaid = sum((h.paid_amount for h in debt.payment_histories.all()), Decimal('0.00'))
            entry['total_repaid'] += repaid

            entry['obligations'].append({
                'id': str(debt.id),
                'title': debt.title,
                'amount': float(debt.amount),
                'status': debt.status,
                'due_date': debt.due_date.isoformat() if debt.due_date else None,
                'remaining_balance': float(remaining),
                'repaid_amount': float(repaid)
            })

        debtors_list = []
        for d in debtor_map.values():
            debtors_list.append({
                'debtor_name': d['debtor_name'],
                'direction': d['direction'],
                'total_principal': float(d['total_principal']),
                'total_repaid': float(d['total_repaid']),
                'outstanding_balance': float(d['outstanding_balance']),
                'active_count': d['active_count'],
                'obligations': d['obligations']
            })

        debtors_list.sort(key=lambda x: x['outstanding_balance'], reverse=True)
        return response.Response(debtors_list)


class ObligationAttachmentViewSet(viewsets.ModelViewSet):
    """
    CRUD for obligation attachments (slips, contracts, statements):
    - Scoped strictly to current user.
    """
    serializer_class = ObligationAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ObligationAttachment.objects.filter(user=self.request.user)
        ob_id = self.request.query_params.get('obligation')
        if ob_id:
            qs = qs.filter(obligation_id=ob_id)
        return qs

    def perform_destroy(self, instance):
        """Remove file attachment record and corresponding storage metadata."""
        if instance.file:
            instance.file.delete(save=False)
        if instance.drive_file_id:
            try:
                from apps.storage.models import DriveFile
                from apps.storage.services import delete_file_from_drive
                df = DriveFile.objects.filter(drive_file_id=instance.drive_file_id, user=self.request.user).first()
                if df:
                    delete_file_from_drive(self.request.user, df)
            except Exception:
                pass
        instance.delete()
