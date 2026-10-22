import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class AccountType(models.TextChoices):
    BANK = 'BANK', 'Bank Account'
    CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
    BROKERAGE_CASH = 'BROKERAGE_CASH', 'Brokerage Cash Balance'
    E_WALLET = 'E_WALLET', 'E-Wallet'
    CASH = 'CASH', 'Physical Cash'


class Account(models.Model):
    """
    Represents an actual financial repository: Bank checking/savings, credit card,
    brokerage cash basket (e.g. Dime! THB balance), or physical cash wallet.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ledger_accounts',
        verbose_name="Account Owner"
    )
    name = models.CharField(max_length=100, verbose_name="Account Name")
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.BANK,
        verbose_name="Account Type"
    )
    currency = models.CharField(max_length=5, default='THB', verbose_name="Currency")
    initial_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Initial Opening Balance"
    )
    current_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Real-time Calculated Balance"
    )
    credit_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Credit Limit (for credit cards)"
    )
    account_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name="Masked Account Number (e.g. xxx-x-x1234)"
    )
    institution_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Financial Institution (e.g. Kasikornbank, SCB, KKP)"
    )
    color = models.CharField(max_length=30, default='zinc', verbose_name="Monochromatic Tag")
    is_default = models.BooleanField(default=False, verbose_name="Is Default Primary Account")
    is_archived = models.BooleanField(default=False, verbose_name="Is Archived / Inactive")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ledger_accounts'
        ordering = ['-is_default', 'name']
        verbose_name = 'Financial Account'
        verbose_name_plural = 'Financial Accounts'

    def __str__(self):
        return f"{self.name} ({self.currency} {self.current_balance})"


class CategoryType(models.TextChoices):
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'


class Category(models.Model):
    """
    Two-tier hierarchical category taxonomy for classifying cash movements.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ledger_categories',
        verbose_name="Custom Owner (Null for Global Defaults)"
    )
    name = models.CharField(max_length=100, verbose_name="Category Name")
    category_type = models.CharField(
        max_length=10,
        choices=CategoryType.choices,
        verbose_name="Category Type"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name="Parent Category"
    )
    icon = models.CharField(max_length=50, default='CircleDot', verbose_name="Lucide Icon Name")
    color = models.CharField(max_length=30, default='zinc', verbose_name="Display Color")
    is_system = models.BooleanField(default=False, verbose_name="Is System Pre-seeded Category")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_categories'
        ordering = ['name']
        verbose_name = 'Cash Flow Category'
        verbose_name_plural = 'Cash Flow Categories'

    def __str__(self):
        prefix = f"{self.parent.name} > " if self.parent else ""
        return f"{prefix}{self.name} ({self.category_type})"


class TransactionType(models.TextChoices):
    INFLOW = 'INFLOW', 'Income / Deposit'
    OUTFLOW = 'OUTFLOW', 'Expense / Withdrawal'
    TRANSFER = 'TRANSFER', 'Transfer Between Accounts'


class Transaction(models.Model):
    """
    Core double-entry or single-entry cash flow ledger record.
    Tracks both gross amount (charged to account) and net amount (user's real share for splits).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ledger_transactions',
        verbose_name="Owner"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name="Source / Target Account"
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        db_index=True,
        verbose_name="Transaction Type"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Classification Category"
    )
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Gross Amount (Total Charged/Deposited)"
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Net Personal Share (Excluding friend advances)"
    )
    title = models.CharField(max_length=255, verbose_name="Description / Merchant")
    notes = models.TextField(blank=True, default='', verbose_name="Notes / Audit Detail")
    transaction_date = models.DateField(db_index=True, verbose_name="Transaction Date")

    # Split state
    is_split = models.BooleanField(default=False, verbose_name="Is Split with Others")

    # Cross-domain links
    obligation = models.ForeignKey(
        'finance.FinancialObligation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_transactions',
        verbose_name="Linked Obligation / Debt (Financial Radar)"
    )
    portfolio = models.ForeignKey(
        'portfolio.InvestmentPortfolio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_transactions',
        verbose_name="Linked Portfolio (Wealth & Trading)"
    )
    workspace_project = models.ForeignKey(
        'workspace.WorkspaceProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_transactions',
        verbose_name="Linked Project (Dev / Freelance / MA)"
    )

    # For TRANSFER transactions
    transfer_destination = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_transfers',
        verbose_name="Destination Account (for Transfers)"
    )
    transfer_peer = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paired_transfer',
        verbose_name="Paired Deposit/Withdrawal Transfer Record"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ledger_transactions'
        ordering = ['-transaction_date', '-created_at']
        verbose_name = 'Ledger Transaction'
        verbose_name_plural = 'Ledger Transactions'
        indexes = [
            models.Index(fields=['user', '-transaction_date', '-created_at']),
            models.Index(fields=['account', '-transaction_date']),
            models.Index(fields=['category', '-transaction_date']),
        ]

    def __str__(self):
        return f"{self.transaction_date} [{self.transaction_type}] {self.title} ({self.gross_amount})"


class TransactionSplit(models.Model):
    """
    Sub-item for shared group expenses. Records counterparty shares and links
    to Debtor records in Financial Radar.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='splits',
        verbose_name="Parent Master Transaction"
    )
    counterparty_name = models.CharField(max_length=150, verbose_name="Friend / Counterparty Name")
    counterparty_contact = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Phone / PromptPay"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Owed Share Amount"
    )
    is_settled = models.BooleanField(default=False, verbose_name="Is Settled / Repaid")
    settled_at = models.DateTimeField(null=True, blank=True, verbose_name="Settlement Timestamp")

    # Inflow transaction when friend pays back
    settlement_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settled_splits',
        verbose_name="Linked Repayment Inflow Transaction"
    )

    # Debtor obligation in Financial Radar
    debtor_obligation = models.ForeignKey(
        'finance.FinancialObligation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='origin_split',
        verbose_name="Linked Debtor in Financial Radar"
    )
    notes = models.CharField(max_length=255, blank=True, default='', verbose_name="Split Note")

    class Meta:
        db_table = 'ledger_transaction_splits'
        ordering = ['counterparty_name']
        verbose_name = 'Transaction Split'
        verbose_name_plural = 'Transaction Splits'

    def __str__(self):
        return f"{self.counterparty_name} - {self.amount} ({'Settled' if self.is_settled else 'Pending'})"


class TransactionAttachment(models.Model):
    """
    Slip and receipt attachments linked to a cashflow transaction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="Parent Transaction"
    )
    file = models.FileField(upload_to='ledger/slips/%Y/%m/', verbose_name="Slip / Receipt File")
    file_name = models.CharField(max_length=255, verbose_name="Original Filename")
    file_type = models.CharField(max_length=50, verbose_name="MIME Type")
    file_size = models.PositiveIntegerField(verbose_name="File Size in Bytes")
    slip_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Bank Transfer Slip Ref ID"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_transaction_attachments'
        ordering = ['-uploaded_at']
        verbose_name = 'Transaction Attachment'
        verbose_name_plural = 'Transaction Attachments'

    def __str__(self):
        return f"{self.file_name} ({self.slip_reference or 'No Ref'})"


class CategoryBudget(models.Model):
    """
    Monthly category ceiling and burn-rate tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ledger_budgets',
        verbose_name="Owner"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name="Budgeted Category"
    )
    period_month = models.CharField(
        max_length=7,
        db_index=True,
        verbose_name="Budget Period (YYYY-MM)"
    )
    limit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monthly Budget Cap"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_category_budgets'
        unique_together = ('user', 'category', 'period_month')
        ordering = ['period_month', 'category__name']
        verbose_name = 'Category Budget'
        verbose_name_plural = 'Category Budgets'

    def __str__(self):
        return f"{self.period_month}: {self.category.name} <= {self.limit_amount}"
