import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class AssetType(models.TextChoices):
    STOCK = 'STOCK', 'หุ้น (Stock)'
    CRYPTO = 'CRYPTO', 'คริปโต (Crypto)'
    FUND = 'FUND', 'กองทุนรวม (Mutual Fund)'
    OTHER = 'OTHER', 'สินทรัพย์อื่นๆ'


class TransactionType(models.TextChoices):
    BUY = 'BUY', 'ซื้อ (Buy)'
    SELL = 'SELL', 'ขาย (Sell)'
    DIVIDEND = 'DIVIDEND', 'เงินปันผล (Dividend)'


class InvestmentPortfolio(models.Model):
    """
    พอร์ตการลงทุนแยกแต่ละตะกร้า (Multi-Portfolio Architecture เหมือน Dime)
    เช่น พอร์ต DCA หุ้นไทย, พอร์ตหุ้นสหรัฐฯ US Growth, พอร์ตคริปโต Moonshot
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investment_portfolios',
        verbose_name="เจ้าของพอร์ต"
    )
    name = models.CharField(max_length=100, verbose_name="ชื่อพอร์ต (เช่น Dime US, DCA หุ้นไทย, Crypto)")
    description = models.TextField(blank=True, default='', verbose_name="คำอธิบาย/เป้าหมายพอร์ต")
    currency = models.CharField(max_length=5, default='THB', verbose_name="สกุลเงินหลักประจำพอร์ต")
    color = models.CharField(max_length=20, default='blue', verbose_name="สีประจำพอร์ต")
    is_default = models.BooleanField(default=False, verbose_name="เป็นพอร์ตหลัก")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'investment_portfolios'
        ordering = ['-is_default', 'created_at']
        verbose_name = 'พอร์ตการลงทุน'
        verbose_name_plural = 'พอร์ตการลงทุนทั้งหมด'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class StockHolding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_holdings',
        verbose_name="เจ้าของพอร์ต"
    )
    portfolio = models.ForeignKey(
        InvestmentPortfolio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='holdings',
        verbose_name="สังกัดพอร์ตการลงทุน"
    )
    ticker = models.CharField(
        max_length=30,
        db_index=True,
        verbose_name="Ticker สัญลักษณ์ (เช่น PTT.BK, DELTA.BK, AAPL, BTC-USD)"
    )
    name = models.CharField(max_length=255, blank=True, default='', verbose_name="ชื่อเต็มสินทรัพย์")
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.STOCK,
        verbose_name="ประเภทสินทรัพย์"
    )
    currency = models.CharField(max_length=5, default='THB', verbose_name="สกุลเงิน")
    notes = models.TextField(blank=True, default='', verbose_name="บันทึกส่วนตัว")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock_holdings'
        unique_together = ('user', 'portfolio', 'ticker')
        ordering = ['ticker']
        verbose_name = 'สินทรัพย์ในพอร์ต'
        verbose_name_plural = 'สินทรัพย์ในพอร์ตทั้งหมด'

    def __str__(self):
        return f"{self.ticker} ({self.user.username})"

    def calculate_position(self):
        """คำนวณจำนวนหน่วยคงเหลือ, ต้นทุนเฉลี่ย, และเงินลงทุนสุทธิ"""
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
        verbose_name="สินทรัพย์"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_transactions',
        verbose_name="ผู้ทำรายการ"
    )
    transaction_type = models.CharField(
        max_length=15,
        choices=TransactionType.choices,
        default=TransactionType.BUY,
        verbose_name="ประเภทรายการ"
    )
    shares = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        verbose_name="จำนวนหน่วย/หุ้น (ทศนิยมสูงสุด 8 ตำแหน่ง)"
    )
    price_per_share = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        verbose_name="ราคาต่อหน่วย (ทศนิยมสูงสุด 8 ตำแหน่ง)"
    )
    fee = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name="ค่าธรรมเนียม/ภาษี"
    )
    currency = models.CharField(
        max_length=5,
        default='THB',
        verbose_name="สกุลเงินที่ทำรายการ (THB / USD)"
    )
    executed_at = models.DateTimeField(verbose_name="วันเวลาที่ทำรายการ")
    notes = models.TextField(blank=True, default='', verbose_name="บันทึก")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-executed_at']
        verbose_name = 'ประวัติรายการซื้อขายหุ้น'
        verbose_name_plural = 'ประวัติรายการซื้อขายทั้งหมด'
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
    price = models.DecimalField(max_digits=24, decimal_places=8, verbose_name="ราคาตลาดล่าสุด (ทศนิยมสูงสุด 8 ตำแหน่ง)")
    change_amount = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        default=Decimal('0.0000'),
        verbose_name="เปลี่ยนแปลงรายวัน (จำนวนเงิน)"
    )
    change_pct = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name="เปลี่ยนแปลง %"
    )
    previous_close = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="ราคาปิดวันก่อนหน้า"
    )
    currency = models.CharField(max_length=5, default='THB', verbose_name="สกุลเงิน")
    market_session = models.CharField(
        max_length=20,
        default='REGULAR',
        blank=True,
        verbose_name="ช่วงเวลาตลาดล่าสุด (REGULAR, PRE, POST)"
    )
    regular_price = models.DecimalField(
        max_digits=24,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="ราคาปิดตลาดปกติ"
    )
    fetched_at = models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุดเมื่อ")

    class Meta:
        db_table = 'stock_price_snapshots'
        verbose_name = 'ราคาตลาดสินทรัพย์'
        verbose_name_plural = 'ราคาตลาดสินทรัพย์ทั้งหมด'

    def __str__(self):
        return f"{self.ticker}: {self.price} ({self.change_pct}%)"


class StockNewsArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticker = models.CharField(max_length=30, db_index=True, verbose_name="สัญลักษณ์หุ้น")
    title = models.CharField(max_length=500, verbose_name="พาดหัวข่าว (EN)")
    title_th = models.CharField(max_length=500, blank=True, default='', verbose_name="พาดหัวข่าวแปลไทย (TH)")
    summary = models.TextField(blank=True, default='', verbose_name="สรุปข่าว (EN)")
    summary_th = models.TextField(blank=True, default='', verbose_name="บทสรุปผลกระทบต่อราคาหุ้น (TH)")
    content = models.TextField(blank=True, default='', verbose_name="เนื้อหาข่าวภาษาอังกฤษฉบับเต็ม")
    content_th = models.TextField(blank=True, default='', verbose_name="เนื้อหาข่าวแปลไทยฉบับเต็ม")
    source = models.CharField(max_length=100, default='Yahoo Finance', verbose_name="สำนักข่าว")
    url = models.URLField(max_length=1000, unique=True, db_index=True, verbose_name="ลิงก์ข่าว")
    published_at = models.DateTimeField(db_index=True, verbose_name="เวลาที่เผยแพร่")
    sentiment = models.CharField(
        max_length=20,
        choices=[('BULLISH', 'Bullish (บวก)'), ('BEARISH', 'Bearish (ลบ)'), ('NEUTRAL', 'Neutral (กลาง)')],
        default='NEUTRAL',
        verbose_name="ทิศทางข่าว (Sentiment)"
    )
    thumbnail_url = models.URLField(max_length=1000, blank=True, default='', verbose_name="รูปภาพประกอบ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_news_articles'
        ordering = ['-published_at', '-created_at']
        verbose_name = 'ข่าวสารสินทรัพย์'
        verbose_name_plural = 'ข่าวสารสินทรัพย์ทั้งหมด'
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
        verbose_name="ผู้ใช้"
    )
    ticker = models.CharField(max_length=30, db_index=True, verbose_name="Ticker")
    name = models.CharField(max_length=255, blank=True, default='', verbose_name="ชื่อสินทรัพย์")
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.STOCK,
        verbose_name="ประเภทสินทรัพย์"
    )
    currency = models.CharField(max_length=5, default='USD', verbose_name="สกุลเงิน")
    notes = models.TextField(blank=True, default='', verbose_name="บันทึก/เป้าหมายการเข้าซื้อ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_watchlist'
        unique_together = ('user', 'ticker')
        ordering = ['-created_at']
        verbose_name = 'รายการสินทรัพย์เฝ้าดู (Watchlist)'
        verbose_name_plural = 'รายการสินทรัพย์เฝ้าดูทั้งหมด'

    def __str__(self):
        return f"{self.user.username} watching {self.ticker}"

