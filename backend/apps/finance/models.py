import uuid
from django.db import models
from django.conf import settings


class ObligationType(models.TextChoices):
    INSTALLMENT = 'INSTALLMENT', 'ผ่อนชำระ'
    SUBSCRIPTION = 'SUBSCRIPTION', 'รายเดือน/รายปี'
    FREE_TRIAL = 'FREE_TRIAL', 'ทดลองใช้ฟรี'
    DEBT = 'DEBT', 'หนี้สิน/ยืมคืน'


class FlowDirection(models.TextChoices):
    OUTFLOW = 'OUTFLOW', 'จ่ายออก'
    INFLOW = 'INFLOW', 'รับเข้า'


class ObligationStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'ใช้งานอยู่'
    PAUSED = 'PAUSED', 'พักไว้'
    COMPLETED = 'COMPLETED', 'เสร็จสิ้น'
    CANCELLED = 'CANCELLED', 'ยกเลิก'


class FinancialObligation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='financial_obligations',
        verbose_name="เจ้าของรายการ"
    )
    title = models.CharField(max_length=255, verbose_name="ชื่อรายการ")
    type = models.CharField(
        max_length=30,
        choices=ObligationType.choices,
        db_index=True,
        verbose_name="ประเภทภาระ"
    )
    direction = models.CharField(
        max_length=10,
        choices=FlowDirection.choices,
        default=FlowDirection.OUTFLOW,
        verbose_name="ทิศทางเงิน"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="จำนวนเงิน"
    )
    currency = models.CharField(
        max_length=3,
        default='THB',
        verbose_name="สกุลเงิน"
    )
    status = models.CharField(
        max_length=20,
        choices=ObligationStatus.choices,
        default=ObligationStatus.ACTIVE,
        db_index=True,
        verbose_name="สถานะ"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="วันครบกำหนดถัดไป / วันหมดอายุ Trial"
    )
    billing_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="วันที่ตัดรอบในแต่ละเดือน (1-31)"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="ข้อมูลเฉพาะ (JSONB)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="แก้ไขล่าสุด")

    class Meta:
        db_table = 'financial_obligations'
        ordering = ['due_date', '-created_at']
        verbose_name = 'ภาระทางการเงิน'
        verbose_name_plural = 'ภาระทางการเงินทั้งหมด'
        indexes = [
            models.Index(fields=['user', 'status', 'due_date'], name='fin_ob_user_stat_due_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name='fin_ob_non_negative_amount'),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()} - {self.amount} {self.currency})"


class PaymentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_histories',
        verbose_name="เจ้าของรายการ"
    )
    obligation = models.ForeignKey(
        FinancialObligation,
        on_delete=models.CASCADE,
        related_name='payment_histories',
        verbose_name="ภาระผูกพัน"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="ยอดที่จ่ายจริง"
    )
    paid_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="วันเวลาที่จ่าย"
    )
    term_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="งวดที่ (สำหรับ Installment)"
    )
    note = models.TextField(
        blank=True,
        default='',
        verbose_name="บันทึกเพิ่มเติม"
    )

    class Meta:
        db_table = 'payment_histories'
        ordering = ['-paid_at']
        verbose_name = 'ประวัติการชำระเงิน'
        verbose_name_plural = 'ประวัติการชำระเงินทั้งหมด'
        constraints = [
            models.CheckConstraint(condition=models.Q(paid_amount__gt=0), name='payment_hist_positive_amount'),
        ]

    def __str__(self):
        return f"Paid {self.paid_amount} for {self.obligation.title}"
