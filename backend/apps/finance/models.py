import uuid
from django.db import models
from django.conf import settings


class ObligationType(models.TextChoices):
    INSTALLMENT = 'INSTALLMENT', 'Installment'
    SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription'
    FREE_TRIAL = 'FREE_TRIAL', 'Free Trial'
    DEBT = 'DEBT', 'Debt & Loan'


class ObligationSubtype(models.TextChoices):
    STANDARD = 'STANDARD', 'Standard'
    HIRE_PURCHASE = 'HIRE_PURCHASE', 'Hire Purchase / Lease'
    BNPL_ACCOUNT = 'BNPL_ACCOUNT', 'BNPL Revolving Credit'
    BNPL_ORDER = 'BNPL_ORDER', 'BNPL Sub-Order'
    FORMAL_LOAN = 'FORMAL_LOAN', 'Formal Bank Loan'
    INFORMAL_BORROW = 'INFORMAL_BORROW', 'Informal / Peer Loan'


class FlowDirection(models.TextChoices):
    OUTFLOW = 'OUTFLOW', 'Outflow'
    INFLOW = 'INFLOW', 'Inflow'


class ObligationStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class FinancialObligation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='financial_obligations',
        verbose_name="User"
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    type = models.CharField(
        max_length=30,
        choices=ObligationType.choices,
        db_index=True,
        verbose_name="Obligation Type"
    )
    subtype = models.CharField(
        max_length=30,
        choices=ObligationSubtype.choices,
        default=ObligationSubtype.STANDARD,
        db_index=True,
        verbose_name="Obligation Subtype"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_orders',
        verbose_name="Parent Obligation"
    )
    direction = models.CharField(
        max_length=10,
        choices=FlowDirection.choices,
        default=FlowDirection.OUTFLOW,
        verbose_name="Flow Direction"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Amount"
    )
    currency = models.CharField(
        max_length=3,
        default='THB',
        verbose_name="Currency"
    )
    status = models.CharField(
        max_length=20,
        choices=ObligationStatus.choices,
        default=ObligationStatus.ACTIVE,
        db_index=True,
        verbose_name="Status"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Next Due Date / Trial Expiration"
    )
    billing_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Billing Day of Month (1-31)"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadata"
    )
    project = models.ForeignKey(
        'workspace.WorkspaceProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_obligations',
        verbose_name="Linked Workspace Project"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = 'financial_obligations'
        ordering = ['due_date', '-created_at']
        verbose_name = 'Financial Obligation'
        verbose_name_plural = 'Financial Obligations'
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
        verbose_name="User"
    )
    obligation = models.ForeignKey(
        FinancialObligation,
        on_delete=models.CASCADE,
        related_name='payment_histories',
        verbose_name="Obligation"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Paid Amount"
    )
    paid_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Paid At"
    )
    term_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Term Number"
    )
    note = models.TextField(
        blank=True,
        default='',
        verbose_name="Note"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Reversal & Audit Metadata"
    )

    class Meta:
        db_table = 'payment_histories'
        ordering = ['-paid_at']
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'
        constraints = [
            models.CheckConstraint(condition=models.Q(paid_amount__gt=0), name='payment_hist_positive_amount'),
        ]

    def __str__(self):
        return f"Paid {self.paid_amount} for {self.obligation.title}"


class AttachmentType(models.TextChoices):
    CONTRACT = 'CONTRACT', 'Contract Document'
    SLIP = 'SLIP', 'Payment Slip'
    STATEMENT = 'STATEMENT', 'Billing Statement'
    SCREENSHOT = 'SCREENSHOT', 'Screenshot'
    OTHER = 'OTHER', 'Other'


class ObligationAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='obligation_attachments',
        verbose_name="User"
    )
    obligation = models.ForeignKey(
        FinancialObligation,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="Obligation"
    )
    payment_history = models.ForeignKey(
        PaymentHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attachments',
        verbose_name="Related Payment History"
    )
    file = models.FileField(
        upload_to='finance/attachments/%Y/%m/',
        verbose_name="File",
        null=True,
        blank=True
    )
    drive_file_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name="Google Drive File ID"
    )
    drive_view_link = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Google Drive View Link"
    )
    drive_download_link = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Google Drive Download Link"
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name="Original File Name"
    )
    file_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        default=AttachmentType.OTHER,
        verbose_name="Document Type"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        verbose_name="File Size (bytes)"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Uploaded At"
    )

    class Meta:
        db_table = 'obligation_attachments'
        ordering = ['-uploaded_at']
        verbose_name = 'Obligation Attachment'
        verbose_name_plural = 'Obligation Attachments'

    def __str__(self):
        return f"{self.file_name} ({self.get_file_type_display()})"
