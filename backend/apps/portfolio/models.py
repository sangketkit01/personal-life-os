import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class AssetType(models.TextChoices):
    STOCK = 'STOCK', 'Stock'
    CRYPTO = 'CRYPTO', 'Crypto'
    FUND = 'FUND', 'Mutual Fund'
    OTHER = 'OTHER', 'Other'


class TransactionType(models.TextChoices):
    BUY = 'BUY', 'Buy'
    SELL = 'SELL', 'Sell'
    DIVIDEND = 'DIVIDEND', 'Dividend'


class InvestmentPortfolio(models.Model):
    """
    Investment portfolio basket (Multi-Portfolio Architecture).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investment_portfolios',
        verbose_name="User"
    )
    name = models.CharField(max_length=100, verbose_name="Portfolio Name")
    description = models.TextField(blank=True, default='', verbose_name="Description / Strategy")
    currency = models.CharField(max_length=5, default='THB', verbose_name="Base Currency")
    color = models.CharField(max_length=20, default='blue', verbose_name="Color")
    is_default = models.BooleanField(default=False, verbose_name="Is Default")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'investment_portfolios'
        ordering = ['-is_default', 'created_at']
        verbose_name = 'Investment Portfolio'
        verbose_name_plural = 'Investment Portfolios'
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True),
                name='unique_default_portfolio_per_user'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class StockHolding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_holdings',
        verbose_name="User"
    )
    portfolio = models.ForeignKey(
        InvestmentPortfolio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='holdings',
        verbose_name="Portfolio"
    )
    ticker = models.CharField(
        max_length=30,
        db_index=True,
        verbose_name="Ticker Symbol"
    )
    name = models.CharField(max_length=255, blank=True, default='', verbose_name="Asset Name")
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.STOCK,
        verbose_name="Asset Type"
    )
    currency = models.CharField(max_length=5, default='THB', verbose_name="Currency")
    notes = models.TextField(blank=True, default='', verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock_holdings'
        unique_together = ('user', 'portfolio', 'ticker')
        ordering = ['ticker']
        verbose_name = 'Stock Holding'
        verbose_name_plural = 'Stock Holdings'

    def __str__(self):
        return f"{self.ticker} ({self.user.username})"

    def calculate_position(self):
        """Calculate remaining units, average cost, and net invested capital."""
        transactions = self.transactions.all().order_by('executed_at')
        total_shares = Decimal('0')
        total_cost = Decimal('0')
        realized_pnl = Decimal('0')

        for tx in transactions:
            if tx.transaction_type == TransactionType.BUY:
                tx_cost = (tx.shares * tx.price_per_share) + tx.fee
                total_cost += tx_cost
                total_shares += tx.shares
            elif tx.transaction_type == TransactionType.SELL:
                if total_shares > Decimal('0'):
                    shares_to_sell = min(tx.shares, total_shares)
                    avg_cost_before_sell = total_cost / total_shares
                    cost_of_shares_sold = avg_cost_before_sell * shares_to_sell
                    proceeds = (shares_to_sell * tx.price_per_share) - tx.fee
                    realized_pnl += (proceeds - cost_of_shares_sold)
                    total_shares -= shares_to_sell
                    total_cost -= cost_of_shares_sold
                    if total_shares <= Decimal('0'):
                        total_shares = Decimal('0')
                        total_cost = Decimal('0')
            elif tx.transaction_type == TransactionType.DIVIDEND:
                realized_pnl += (tx.shares * tx.price_per_share) - tx.fee

        avg_price = (total_cost / total_shares) if total_shares > Decimal('0') else Decimal('0')
        return {
            'shares': total_shares,
            'avg_cost': avg_price,
            'total_invested': total_cost,
            'realized_pnl': realized_pnl
        }


class StockTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    holding = models.ForeignKey(
        StockHolding,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Holding"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_transactions',
        verbose_name="User"
    )
    transaction_type = models.CharField(
        max_length=15,
        choices=TransactionType.choices,
        default=TransactionType.BUY,
        verbose_name="Transaction Type"
    )
    shares = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        verbose_name="Shares / Units"
    )
    price_per_share = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        verbose_name="Price per Share"
    )
    fee = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name="Fee / Tax"
    )
    currency = models.CharField(
        max_length=5,
        default='THB',
        verbose_name="Transaction Currency"
    )
    executed_at = models.DateTimeField(verbose_name="Executed At")
    notes = models.TextField(blank=True, default='', verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-executed_at']
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'
        indexes = [
            models.Index(fields=['user', '-executed_at'], name='stock_tx_user_exec_idx'),
            models.Index(fields=['holding', '-executed_at'], name='stock_tx_hold_exec_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(shares__gt=0), name='stock_tx_positive_shares'),
            models.CheckConstraint(condition=models.Q(price_per_share__gte=0), name='stock_tx_non_negative_price'),
            models.CheckConstraint(condition=models.Q(fee__gte=0), name='stock_tx_non_negative_fee'),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.shares} {self.holding.ticker} @ {self.price_per_share}"


class StockPriceSnapshot(models.Model):
    ticker = models.CharField(max_length=30, primary_key=True, verbose_name="Ticker")
    price = models.DecimalField(max_digits=24, decimal_places=8, verbose_name="Latest Market Price")
    change_amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        default=Decimal('0.0000'),
        verbose_name="Daily Change Amount"
    )
    change_pct = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name="Daily Change %"
    )
    previous_close = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Previous Close Price"
    )
    currency = models.CharField(max_length=5, default='THB', verbose_name="Currency")
    market_session = models.CharField(
        max_length=20,
        default='REGULAR',
        blank=True,
        verbose_name="Market Session"
    )
    regular_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Regular Market Price"
    )
    extended_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Extended Market Price"
    )
    extended_change = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Extended Change Amount"
    )
    extended_change_pct = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Extended Change %"
    )
    fetched_at = models.DateTimeField(auto_now=True, verbose_name="Last Fetched At")

    class Meta:
        db_table = 'stock_price_snapshots'
        verbose_name = 'Stock Price Snapshot'
        verbose_name_plural = 'Stock Price Snapshots'

    def __str__(self):
        return f"{self.ticker}: {self.price} ({self.change_pct}%)"


class StockNewsArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticker = models.CharField(max_length=30, db_index=True, verbose_name="Ticker")
    title = models.CharField(max_length=500, verbose_name="News Headline (EN)")
    title_th = models.CharField(max_length=500, blank=True, default='', verbose_name="Translated Headline (TH)")
    summary = models.TextField(blank=True, default='', verbose_name="News Summary (EN)")
    summary_th = models.TextField(blank=True, default='', verbose_name="Translated Summary (TH)")
    content = models.TextField(blank=True, default='', verbose_name="Full Content (EN)")
    content_th = models.TextField(blank=True, default='', verbose_name="Translated Full Content (TH)")
    source = models.CharField(max_length=100, default='Yahoo Finance', verbose_name="News Source")
    url = models.URLField(max_length=1000, db_index=True, verbose_name="Article URL")
    published_at = models.DateTimeField(db_index=True, verbose_name="Published At")
    sentiment = models.CharField(
        max_length=20,
        choices=[('BULLISH', 'Bullish'), ('BEARISH', 'Bearish'), ('NEUTRAL', 'Neutral')],
        default='NEUTRAL',
        verbose_name="Sentiment"
    )
    thumbnail_url = models.URLField(max_length=1000, blank=True, default='', verbose_name="Thumbnail URL")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_news_articles'
        ordering = ['-published_at', '-created_at']
        unique_together = ('ticker', 'url')
        verbose_name = 'Stock News Article'
        verbose_name_plural = 'Stock News Articles'
        indexes = [
            models.Index(fields=['ticker', '-published_at'], name='stock_news_tick_pub_idx'),
        ]

    def __str__(self):
        return f"[{self.ticker}] {self.title[:50]}"


class StockWatchlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_watchlist',
        verbose_name="User"
    )
    ticker = models.CharField(max_length=30, db_index=True, verbose_name="Ticker")
    name = models.CharField(max_length=255, blank=True, default='', verbose_name="Asset Name")
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.STOCK,
        verbose_name="Asset Type"
    )
    currency = models.CharField(max_length=5, default='USD', verbose_name="Currency")
    notes = models.TextField(blank=True, default='', verbose_name="Notes / Price Target")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_watchlist'
        unique_together = ('user', 'ticker')
        ordering = ['-created_at']
        verbose_name = 'Stock Watchlist'
        verbose_name_plural = 'Stock Watchlists'

    def __str__(self):
        return f"{self.user.username} watching {self.ticker}"

