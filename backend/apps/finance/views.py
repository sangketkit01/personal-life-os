from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.utils import timezone
from rest_framework import viewsets, views, permissions, status, response
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import FinancialObligation, ObligationType, ObligationAttachment, PaymentHistory
from .serializers import (
    FinancialObligationSerializer,
    PayObligationSerializer,
    PaymentHistorySerializer,
    ObligationAttachmentSerializer
)
from .strategies import ObligationStrategyFactory
from .services import get_financial_overview


class FinancialOverviewView(views.APIView):
    """API สรุปภาพรวมการเงินประจำเดือน (Burn Rate, Due in 7 Days, Free Trials)"""
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
    CRUD และ Action สำหรับภาระทางการเงินทั้งหมด
    - กรองเฉพาะรายการของ User ปัจจุบัน (Strict Isolation)
    - รองรับ Action 'pay' และ 'cancel-trial'
    """
    serializer_class = FinancialObligationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q

        # ป้องกันไม่ให้ User คนอื่นมองเห็นหรือแก้ไขบิลข้ามบัญชี พร้อม Prefetch ป้องกัน N+1
        qs = FinancialObligation.objects.filter(user=self.request.user).prefetch_related(
            'payment_histories__attachments',
            'attachments',
            'sub_orders'
        )

        # รองรับการ Filter ผ่าน Query Parameters: ?type=INSTALLMENT&status=ACTIVE&subtype=BNPL_ACCOUNT&direction=INFLOW&search=...&ordering=...
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
        """Action สำหรับกดชำระเงิน / ตัดงวด / ทยอยจ่ายหนี้"""
        obligation = self.get_object()
        serializer = PayObligationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        paid_amount = serializer.validated_data.get('paid_amount')
        term_number = serializer.validated_data.get('term_number')
        note = serializer.validated_data.get('note', '')
        slip_file = serializer.validated_data.get('slip_file')

        # ตรวจสอบความถูกต้องของสลิปโอนเงิน (ถ้ามี)
        if slip_file:
            try:
                validate_uploaded_file(slip_file)
            except ValueError as ve:
                return response.Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        try:
            summary = strategy.on_paid(
                obligation=obligation,
                paid_amount=paid_amount,
                term_number=term_number,
                note=note
            )

            # แนบไฟล์สลิปเข้ากับประวัติการจ่ายเงิน (ถ้ามี)
            if slip_file and summary.get('payment_id'):
                payment_record = PaymentHistory.objects.filter(id=summary['payment_id']).first()
                if payment_record:
                    ObligationAttachment.objects.create(
                        user=request.user,
                        obligation=obligation,
                        payment_history=payment_record,
                        file=slip_file,
                        file_name=getattr(slip_file, 'name', 'payment_slip.jpg'),
                        file_type='SLIP',
                        file_size=getattr(slip_file, 'size', 0)
                    )

            # ซิงค์เข้า Cash Flow Ledger (ถ้าเลือกบัญชี)
            account_id = serializer.validated_data.get('account_id')
            if account_id:
                from apps.ledger.models import Account, Transaction, TransactionType
                try:
                    account = Account.objects.select_for_update().get(id=account_id, user=request.user)
                except Account.DoesNotExist:
                    raise ValueError("Target cash flow account not found or does not belong to user.")

                actual_paid = Decimal(str(paid_amount if paid_amount is not None else obligation.amount))

                if obligation.direction == 'INFLOW':
                    tx_type = TransactionType.INFLOW
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

                Transaction.objects.create(
                    user=request.user,
                    account=account,
                    transaction_type=tx_type,
                    gross_amount=actual_paid,
                    net_amount=actual_paid,
                    title=tx_title,
                    notes=note or f"Auto-settled from Financial Radar ({obligation.get_type_display()})",
                    transaction_date=timezone.now().date(),
                    obligation=obligation
                )

            # โหลดข้อมูล obligation ล่าสุดส่งกลับ
            obligation.refresh_from_db()
            log_activity(obligation.user, 'FINANCE', 'PAY_BILL', f'ชำระเงิน {paid_amount or obligation.amount} {obligation.currency} สำหรับ {obligation.title}', request=request)
            return response.Response({
                'message': 'บันทึกการชำระเงินเรียบร้อยแล้ว',
                'obligation': FinancialObligationSerializer(obligation, context={'request': request}).data,
                'summary': summary
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='upload-attachment')
    def upload_attachment(self, request, pk=None):
        """Action สำหรับอัปโหลดไฟล์สัญญา, ใบเสร็จ, สลิป, หรือใบแจ้งยอด"""
        obligation = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return response.Response({'detail': 'กรุณาเลือกไฟล์ที่ต้องการอัปโหลด'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_uploaded_file(file_obj)
        except ValueError as ve:
            return response.Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        file_type = request.data.get('file_type', 'OTHER')
        payment_id = request.data.get('payment_history')
        payment_history = None
        if payment_id:
            payment_history = obligation.payment_histories.filter(id=payment_id).first()

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
        """Action สำหรับกดยกเลิก Free Trial"""
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
        except Exception:
            amount = Decimal('0.00')

        obligation.type = ObligationType.SUBSCRIPTION
        obligation.status = ObligationStatus.ACTIVE
        obligation.amount = amount
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
        """ดึงประวัติการชำระเงินทั้งหมดของรายการนี้"""
        obligation = self.get_object()
        histories = obligation.payment_histories.all().order_by('-paid_at')
        return response.Response(PaymentHistorySerializer(histories, many=True).data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Action สำหรับดึงตาราง Amortization Schedule แบบละเอียด (งวดที่ 1 ถึง N)"""
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
        financed_amount = Decimal(str(metadata.get('financed_amount', metadata.get('total_principal', obligation.amount * total_terms))))
        flat_rate_pa = Decimal(str(metadata.get('flat_rate_pa', '0.00')))
        monthly_installment = obligation.amount

        # คำนวณเงินต้นและดอกเบี้ยต่องวด
        if total_terms > 0 and flat_rate_pa > Decimal('0'):
            total_years = Decimal(str(total_terms)) / Decimal('12.0')
            total_interest = financed_amount * (flat_rate_pa / Decimal('100.0')) * total_years
            monthly_interest = (total_interest / Decimal(str(total_terms))).quantize(Decimal('0.01'))
            monthly_principal = (monthly_installment - monthly_interest).quantize(Decimal('0.01'))
        else:
            monthly_interest = Decimal('0.00')
            monthly_principal = (monthly_installment / Decimal(str(max(1, total_terms)))).quantize(Decimal('0.01')) if total_terms > 0 else monthly_installment

        base_date = obligation.due_date or datetime.date.today()
        start_date = base_date - relativedelta(months=max(0, current_term - 1)) if current_term > 0 else base_date

        schedule_list = []
        running_principal = financed_amount

        for term in range(1, total_terms + 1):
            term_date = start_date + relativedelta(months=term - 1)
            is_paid = term <= current_term
            is_current = term == current_term + 1
            running_principal = max(Decimal('0.00'), running_principal - monthly_principal)

            schedule_list.append({
                'term_number': term,
                'total_terms': total_terms,
                'due_date': term_date.isoformat(),
                'installment_amount': float(monthly_installment),
                'principal': float(monthly_principal),
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
        """Action สำหรับดึงรายชื่อลูกหนี้ (Debtors Directory) พร้อมยอดหนี้รวมและประวัติการคืนเงิน"""
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
    CRUD สำหรับเอกสารแนบ (สลิป, สัญญา, ใบแจ้งยอด)
    - ผูกกับ User ปัจจุบัน (Strict Data Isolation)
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
        """ลบไฟล์จริงออกจาก Media Storage เมื่อลบ Record ในฐานข้อมูล"""
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()
