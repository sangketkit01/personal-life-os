from rest_framework import viewsets, views, permissions, status, response
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import FinancialObligation, ObligationType
from .serializers import (
    FinancialObligationSerializer,
    PayObligationSerializer,
    PaymentHistorySerializer
)
from .strategies import ObligationStrategyFactory
from .services import get_financial_overview


class FinancialOverviewView(views.APIView):
    """API สรุปภาพรวมการเงินประจำเดือน (Burn Rate, Due in 7 Days, Free Trials)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = get_financial_overview(request.user)
        return response.Response(data)


class FinancialObligationViewSet(viewsets.ModelViewSet):
    """
    CRUD และ Action สำหรับภาระทางการเงินทั้งหมด
    - กรองเฉพาะรายการของ User ปัจจุบัน (Strict Isolation)
    - รองรับ Action 'pay' และ 'cancel-trial'
    """
    serializer_class = FinancialObligationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ป้องกันไม่ให้ User คนอื่นมองเห็นหรือแก้ไขบิลข้ามบัญชี พร้อม Prefetch Payment Histories ป้องกัน N+1
        qs = FinancialObligation.objects.filter(user=self.request.user).prefetch_related('payment_histories')

        # รองรับการ Filter ผ่าน Query Parameters: ?type=INSTALLMENT&status=ACTIVE
        type_param = self.request.query_params.get('type')
        status_param = self.request.query_params.get('status')

        if type_param:
            qs = qs.filter(type=type_param.upper())
        if status_param:
            qs = qs.filter(status=status_param.upper())

        return qs

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Action สำหรับกดชำระเงิน / ตัดงวด / ทยอยจ่ายหนี้"""
        obligation = self.get_object()
        serializer = PayObligationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        paid_amount = serializer.validated_data.get('paid_amount')
        term_number = serializer.validated_data.get('term_number')
        note = serializer.validated_data.get('note', '')

        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        try:
            summary = strategy.on_paid(
                obligation=obligation,
                paid_amount=paid_amount,
                term_number=term_number,
                note=note
            )
            # โหลดข้อมูล obligation ล่าสุดส่งกลับ
            obligation.refresh_from_db()
            log_activity(obligation.user, 'FINANCE', 'PAY_BILL', f'ชำระเงิน {paid_amount or obligation.amount} {obligation.currency} สำหรับ {obligation.title}', request=request)
            return response.Response({
                'message': 'บันทึกการชำระเงินเรียบร้อยแล้ว',
                'obligation': FinancialObligationSerializer(obligation).data,
                'summary': summary
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return response.Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='cancel-trial')
    def cancel_trial(self, request, pk=None):
        """Action สำหรับกดยกเลิก Free Trial"""
        obligation = self.get_object()
        if obligation.type != ObligationType.FREE_TRIAL:
            return response.Response(
                {'detail': 'คำสั่งนี้ใช้ได้เฉพาะกับรายการ Free Trial เท่านั้น'},
                status=status.HTTP_400_BAD_REQUEST
            )

        strategy = ObligationStrategyFactory.get_strategy(obligation.type)
        summary = strategy.cancel(obligation)
        obligation.refresh_from_db()
        log_activity(obligation.user, 'FINANCE', 'CANCEL_TRIAL', f'กดยกเลิก Free Trial: {obligation.title}', request=request)

        return response.Response({
            'message': 'ยกเลิก Free Trial เรียบร้อยแล้ว (สถานะเปลี่ยนเป็น CANCELLED)',
            'obligation': FinancialObligationSerializer(obligation).data,
            'summary': summary
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """ดึงประวัติการชำระเงินทั้งหมดของรายการนี้"""
        obligation = self.get_object()
        histories = obligation.payment_histories.all().order_by('-paid_at')
        return response.Response(PaymentHistorySerializer(histories, many=True).data)
