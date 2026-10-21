from decimal import Decimal
from rest_framework import serializers
from .models import (
    StockHolding,
    StockTransaction,
    StockPriceSnapshot,
    StockNewsArticle,
    StockWatchlist,
    AssetType,
    TransactionType,
    InvestmentPortfolio
)
from .services import calculate_detailed_position, normalize_ticker
from .asset_catalog import verify_ticker_exists


class InvestmentPortfolioSerializer(serializers.ModelSerializer):
    """Serializer สำหรับจัดการพอร์ตการลงทุนแต่ละตะกร้า (เหมือน Dime)"""
    holdings_count = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentPortfolio
        fields = (
            'id',
            'name',
            'description',
            'currency',
            'color',
            'is_default',
            'holdings_count',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'is_default', 'holdings_count', 'created_at', 'updated_at')

    def get_holdings_count(self, obj):
        return obj.holdings.count()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class StockPriceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPriceSnapshot
        fields = ('ticker', 'price', 'change_pct', 'currency', 'fetched_at')


class StockTransactionSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(write_only=True, required=False)
    portfolio = serializers.UUIDField(write_only=True, required=False)
    holding_ticker = serializers.CharField(source='holding.ticker', read_only=True)
    holding_currency = serializers.CharField(source='holding.currency', read_only=True)
    portfolio_name = serializers.CharField(source='holding.portfolio.name', read_only=True)

    class Meta:
        model = StockTransaction
        fields = (
            'id',
            'holding',
            'portfolio',
            'portfolio_name',
            'ticker',
            'holding_ticker',
            'holding_currency',
            'transaction_type',
            'shares',
            'price_per_share',
            'fee',
            'currency',
            'executed_at',
            'notes',
            'created_at'
        )
        read_only_fields = ('id', 'holding_ticker', 'holding_currency', 'portfolio_name', 'created_at')
        extra_kwargs = {
            'holding': {'required': False},
            'currency': {'required': False}
        }

    def validate_holding(self, value):
        request = self.context.get('request')
        if value and request and value.user != request.user:
            raise serializers.ValidationError('You do not have permission to attach transactions to this holding.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        tx_type = attrs.get('transaction_type')
        shares = attrs.get('shares', Decimal('0'))
        holding = attrs.get('holding')

        if shares <= Decimal('0'):
            raise serializers.ValidationError({'shares': 'Shares count must be greater than zero.'})

        price = attrs.get('price_per_share', Decimal('0'))
        if price < Decimal('0'):
            raise serializers.ValidationError({'price_per_share': 'Price per share cannot be negative.'})

        fee = attrs.get('fee', Decimal('0'))
        if fee < Decimal('0'):
            raise serializers.ValidationError({'fee': 'Fee cannot be negative.'})

        # F05: ตรวจสอบความสอดคล้องระหว่าง Target Portfolio กับ Holding
        target_portfolio_id = self.initial_data.get('portfolio')
        if holding and target_portfolio_id and str(holding.portfolio_id) != str(target_portfolio_id):
            # หาก Holding ปัจจุบันไม่ได้อยู่ในพอร์ตที่เลือก ให้ค้นหา Holding ของ ticker นี้ในพอร์ตเป้าหมาย
            matched_holding = StockHolding.objects.filter(
                user=user,
                portfolio_id=target_portfolio_id,
                ticker=holding.ticker
            ).first()
            if matched_holding:
                attrs['holding'] = matched_holding
                holding = matched_holding
            else:
                raise serializers.ValidationError({
                    'portfolio': f'สินทรัพย์ที่เลือกผูกกับพอร์ต "{holding.portfolio.name}" ซึ่งไม่ตรงกับพอร์ตปลายทางที่เลือก'
                })

        # F08: Validate SELL volume against current holding (รองรับทั้งส่ง holding และส่ง ticker)
        if tx_type == TransactionType.SELL:
            if not holding and user:
                ticker_input = self.initial_data.get('ticker')
                portfolio_id = self.initial_data.get('portfolio')
                if ticker_input:
                    clean_ticker = normalize_ticker(ticker_input)
                    holding_qs = StockHolding.objects.filter(user=user)
                    if portfolio_id and str(portfolio_id).upper() != 'ALL':
                        holding_qs = holding_qs.filter(portfolio_id=portfolio_id)
                    holding = holding_qs.filter(ticker__iexact=clean_ticker).first()
                    if not holding and not clean_ticker.endswith('.BK'):
                        holding = holding_qs.filter(ticker__iexact=f"{clean_ticker}.BK").first()

            if not holding:
                raise serializers.ValidationError({
                    'shares': f'ไม่สามารถขายได้เนื่องจากคุณยังไม่มีสินทรัพย์นี้ในพอร์ตที่เลือก'
                })

            pos = calculate_detailed_position(holding)
            available_shares = pos['shares']
            # หากเป็นการแก้ไขรายการขายเดิม ให้นำจำนวนหุ้นของรายการเดิมกลับมาคำนวณด้วย
            if self.instance and self.instance.transaction_type == TransactionType.SELL and self.instance.holding_id == holding.id:
                available_shares += self.instance.shares

            if shares > available_shares:
                raise serializers.ValidationError({
                    'shares': f'Cannot sell {shares} shares; holding only has {available_shares} shares available.'
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        ticker_input = validated_data.pop('ticker', None)
        portfolio_id = validated_data.pop('portfolio', None)
        currency_input = validated_data.get('currency')
        holding = validated_data.get('holding')

        # หาเป้าหมาย InvestmentPortfolio (เหมือน Dime Multi-Portfolio)
        portfolio_obj = None
        if portfolio_id:
            portfolio_obj = InvestmentPortfolio.objects.filter(id=portfolio_id, user=user).first()
        if not portfolio_obj:
            portfolio_obj = InvestmentPortfolio.objects.filter(user=user, is_default=True).first()
            if not portfolio_obj:
                portfolio_obj, _ = InvestmentPortfolio.objects.get_or_create(
                    user=user,
                    is_default=True,
                    defaults={'name': 'Main Portfolio', 'currency': 'THB'}
                )

        # ถ้าส่ง ticker มาแทน holding ID ให้ตรวจสอบความถูกต้องและค้นหา/สร้าง holding ในพอร์ตนั้น
        if not holding and ticker_input:
            clean_ticker = normalize_ticker(ticker_input, currency=currency_input)

            # ตรวจสอบอย่างเข้มงวดว่าสินทรัพย์มีอยู่จริงในตลาด (ถ้าไม่ใช่จะเพิ่มไม่ได้)
            verified = verify_ticker_exists(clean_ticker)
            if not verified and not clean_ticker.endswith('.BK') and not clean_ticker.endswith('-USD'):
                # ลองตรวจสอบเผื่อเป็นหุ้นไทยที่ไม่ได้ใส่ .BK
                th_verified = verify_ticker_exists(f"{clean_ticker}.BK")
                if th_verified:
                    clean_ticker = f"{clean_ticker}.BK"
                    verified = th_verified

            if not verified and not StockHolding.objects.filter(user=user, ticker=clean_ticker).exists():
                raise serializers.ValidationError({
                    'ticker': f"ไม่พบสินทรัพย์ '{clean_ticker}' ในระบบ กรุณาค้นหาและเลือกจากรายชื่อสินทรัพย์ที่ถูกต้อง"
                })

            default_curr = currency_input.upper() if currency_input else (
                verified['currency'] if verified else ('THB' if clean_ticker.endswith('.BK') else 'USD')
            )
            default_name = verified['name'] if verified else clean_ticker
            default_type = verified['asset_type'] if verified else (
                AssetType.CRYPTO if '-USD' in clean_ticker else AssetType.STOCK
            )

            holding, created = StockHolding.objects.get_or_create(
                user=user,
                portfolio=portfolio_obj,
                ticker=clean_ticker,
                defaults={
                    'name': default_name,
                    'currency': default_curr,
                    'asset_type': default_type
                }
            )
            validated_data['holding'] = holding

        if not validated_data.get('holding'):
            raise serializers.ValidationError({'holding': 'จำเป็นต้องระบุ holding หรือ ticker'})

        # F03: ล็อก currency ของ transaction ให้ตรงกับ holding เสมอ เพื่อไม่ให้เปลี่ยน denomination ของข้อมูลเดิม
        target_holding = validated_data['holding']
        validated_data['currency'] = target_holding.currency or 'THB'

        validated_data['user'] = user
        tx = super().create(validated_data)

        # Requirements 2 & 3:
        # ตอนเพิ่มหุ้น ซิงค์ราคาตลาดสดทันทีเพื่อคำนวณกำไรขาดทุน และซิงค์ข่าวสารพร้อมแปลภาษาอัตโนมัติ
        holding_ticker = target_holding.ticker
        import sys
        if holding_ticker and 'test' not in sys.argv:
            import threading
            from .services import fetch_and_cache_market_prices
            from .news_service import ingest_news_for_ticker

            # 1. Sync Price ทันที (force=True) เพื่อคำนวณกำไรขาดทุนล่าสุด
            try:
                fetch_and_cache_market_prices([holding_ticker, 'USDTHB=X'], force=True)
            except Exception:
                pass

            # 2. Sync News อัตโนมัติใน Background Thread (ไม่บล็อก UI)
            try:
                threading.Thread(
                    target=ingest_news_for_ticker,
                    args=(holding_ticker, 3),
                    daemon=True
                ).start()
            except Exception:
                pass

        return tx

    def update(self, instance, validated_data):
        # F03: ล็อก currency ไม่ให้เปลี่ยน denomination ของ Holding เดิม
        if instance.holding:
            validated_data['currency'] = instance.holding.currency or 'THB'
        return super().update(instance, validated_data)


class StockHoldingSerializer(serializers.ModelSerializer):
    position = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)

    class Meta:
        model = StockHolding
        fields = (
            'id',
            'portfolio',
            'portfolio_name',
            'ticker',
            'name',
            'asset_type',
            'currency',
            'notes',
            'position',
            'recent_transactions',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'portfolio_name', 'created_at', 'updated_at')

    def get_position(self, obj):
        price_map = self.context.get('price_map', {})
        current_price = price_map.get(obj.ticker)
        usd_to_thb_rate = self.context.get('usd_to_thb_rate')
        return calculate_detailed_position(obj, current_price=current_price, usd_to_thb_rate=usd_to_thb_rate)

    def get_recent_transactions(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'transactions' in obj._prefetched_objects_cache:
            txs = sorted(obj.transactions.all(), key=lambda x: x.executed_at, reverse=True)[:5]
        else:
            txs = obj.transactions.all().order_by('-executed_at')[:5]
        return StockTransactionSerializer(txs, many=True, context=self.context).data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['ticker'] = normalize_ticker(validated_data.get('ticker', ''))
        return super().create(validated_data)


class StockNewsArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockNewsArticle
        fields = (
            'id',
            'ticker',
            'title',
            'title_th',
            'summary',
            'summary_th',
            'content',
            'content_th',
            'source',
            'url',
            'published_at',
            'sentiment',
            'thumbnail_url',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')


class StockWatchlistSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()
    change_amount = serializers.SerializerMethodField()
    change_pct = serializers.SerializerMethodField()

    class Meta:
        model = StockWatchlist
        fields = (
            'id',
            'ticker',
            'name',
            'asset_type',
            'currency',
            'notes',
            'current_price',
            'change_amount',
            'change_pct',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def get_current_price(self, obj):
        price_map = self.context.get('price_map', {})
        if obj.ticker in price_map and price_map[obj.ticker] is not None:
            return float(price_map[obj.ticker])
        snapshot = StockPriceSnapshot.objects.filter(ticker=obj.ticker).first()
        return float(snapshot.price) if snapshot and snapshot.price else None

    def get_change_amount(self, obj):
        snapshot = StockPriceSnapshot.objects.filter(ticker=obj.ticker).first()
        return float(snapshot.change_amount) if snapshot and snapshot.change_amount else 0.0

    def get_change_pct(self, obj):
        snapshot = StockPriceSnapshot.objects.filter(ticker=obj.ticker).first()
        return float(snapshot.change_pct) if snapshot and snapshot.change_pct else 0.0

