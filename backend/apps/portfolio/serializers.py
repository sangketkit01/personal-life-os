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
from .services import calculate_detailed_position, normalize_ticker, validate_holding_transaction_timeline
from .asset_catalog import verify_ticker_exists


class InvestmentPortfolioSerializer(serializers.ModelSerializer):
    """Serializer for investment portfolio buckets (multi-portfolio support)."""
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
        if hasattr(obj, 'annotated_holdings_count'):
            return obj.annotated_holdings_count
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
    portfolio_id = serializers.UUIDField(source='holding.portfolio_id', read_only=True)
    holding_ticker = serializers.CharField(source='holding.ticker', read_only=True)
    holding_currency = serializers.CharField(source='holding.currency', read_only=True)
    portfolio_name = serializers.CharField(source='holding.portfolio.name', read_only=True)

    class Meta:
        model = StockTransaction
        fields = (
            'id',
            'holding',
            'portfolio',
            'portfolio_id',
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
        read_only_fields = ('id', 'portfolio_id', 'holding_ticker', 'holding_currency', 'portfolio_name', 'created_at')
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
        tx_type = attrs.get('transaction_type', getattr(self.instance, 'transaction_type', None))
        shares = attrs.get('shares', getattr(self.instance, 'shares', Decimal('0')))
        holding = attrs.get('holding', getattr(self.instance, 'holding', None))

        if shares <= Decimal('0'):
            raise serializers.ValidationError({'shares': 'Shares count must be greater than zero.'})

        price = attrs.get('price_per_share', getattr(self.instance, 'price_per_share', Decimal('0')))
        if price < Decimal('0'):
            raise serializers.ValidationError({'price_per_share': 'Price per share cannot be negative.'})

        fee = attrs.get('fee', getattr(self.instance, 'fee', Decimal('0')))
        if fee < Decimal('0'):
            raise serializers.ValidationError({'fee': 'Fee cannot be negative.'})

        # F05: Validate consistency between target portfolio and selected holding
        target_portfolio_id = self.initial_data.get('portfolio')
        if holding and target_portfolio_id and str(holding.portfolio_id) != str(target_portfolio_id):
            # If holding does not belong to target portfolio, locate matching holding in target portfolio
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
                    'portfolio': f'Selected asset belongs to portfolio "{holding.portfolio.name}", which does not match target.'
                })

        # F08: Validate SELL volume against current holding (supports both holding id and ticker)
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
                    'shares': 'Cannot sell; asset does not exist in selected portfolio.'
                })

            pos = calculate_detailed_position(holding)
            available_shares = pos['shares']
            # If updating an existing sell transaction, credit back existing shares before validating
            if self.instance and self.instance.transaction_type == TransactionType.SELL and self.instance.holding_id == holding.id:
                available_shares += self.instance.shares

            if shares > available_shares:
                raise serializers.ValidationError({
                    'shares': f'Cannot sell {shares} shares; holding only has {available_shares} shares available.'
                })

        # Chronological timeline replay validation across all trades
        target_holding = holding or (self.instance.holding if self.instance else None)
        if self.instance and holding and self.instance.holding_id != holding.id:
            # Moving between holdings: validate source holding removal first
            validate_holding_transaction_timeline(self.instance.holding, pending_tx=self.instance, is_delete=True)

        if target_holding:
            from django.utils import timezone
            sim_tx = StockTransaction(
                id=self.instance.id if self.instance else None,
                holding=target_holding,
                transaction_type=tx_type,
                shares=shares,
                price_per_share=price,
                fee=fee,
                executed_at=attrs.get('executed_at', getattr(self.instance, 'executed_at', None)) or timezone.now()
            )
            validate_holding_transaction_timeline(target_holding, pending_tx=sim_tx, is_delete=False)

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        ticker_input = validated_data.pop('ticker', None)
        portfolio_id = validated_data.pop('portfolio', None)
        currency_input = validated_data.get('currency')
        holding = validated_data.get('holding')

        # Resolve target InvestmentPortfolio
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

        # If ticker is provided instead of holding ID, validate and locate or create holding in portfolio
        if not holding and ticker_input:
            clean_ticker = normalize_ticker(ticker_input, currency=currency_input)

            # Verify asset existence in market catalog or live exchange
            verified = verify_ticker_exists(clean_ticker)
            if not verified and not clean_ticker.endswith('.BK') and not clean_ticker.endswith('-USD'):
                # Check if Thai stock without .BK suffix
                th_verified = verify_ticker_exists(f"{clean_ticker}.BK")
                if th_verified:
                    clean_ticker = f"{clean_ticker}.BK"
                    verified = th_verified

            if not verified and not StockHolding.objects.filter(user=user, ticker=clean_ticker).exists():
                raise serializers.ValidationError({
                    'ticker': f"Asset symbol '{clean_ticker}' not found. Please verify ticker from search catalog."
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
            raise serializers.ValidationError({'holding': 'Holding or ticker is required.'})

        # F03: Lock currency of transaction to match holding
        target_holding = validated_data['holding']
        validated_data['currency'] = target_holding.currency or 'THB'

        validated_data['user'] = user
        tx = super().create(validated_data)

        # Requirements 2 & 3:
        # On adding trades, sync market price and news in background (skip if bulk import to prevent server overload)
        is_bulk = self.context.get('is_bulk_import', False)
        holding_ticker = target_holding.ticker
        import sys
        if holding_ticker and 'test' not in sys.argv and not is_bulk:
            import threading
            from .services import fetch_and_cache_market_prices
            from .news_service import ingest_news_for_ticker

            # 1. Sync Price immediately (force=True) to compute latest PnL
            try:
                fetch_and_cache_market_prices([holding_ticker, 'USDTHB=X'], force=True)
            except Exception:
                pass

            # 2. Sync News in background thread
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
        from django.db import transaction as db_transaction
        new_holding = validated_data.get('holding', instance.holding)
        # F03: Lock currency to prevent altering denomination of existing holding
        if new_holding:
            validated_data['currency'] = new_holding.currency or 'THB'

        with db_transaction.atomic():
            if instance.holding_id and new_holding and instance.holding_id != new_holding.id:
                locked_source = StockHolding.objects.select_for_update().get(id=instance.holding_id)
                validate_holding_transaction_timeline(locked_source, pending_tx=instance, is_delete=True)

                locked_dest = StockHolding.objects.select_for_update().get(id=new_holding.id)
                sim_tx = StockTransaction(
                    id=instance.id,
                    holding=locked_dest,
                    transaction_type=validated_data.get('transaction_type', instance.transaction_type),
                    shares=validated_data.get('shares', instance.shares),
                    price_per_share=validated_data.get('price_per_share', instance.price_per_share),
                    fee=validated_data.get('fee', instance.fee),
                    executed_at=validated_data.get('executed_at', instance.executed_at)
                )
                validate_holding_transaction_timeline(locked_dest, pending_tx=sim_tx, is_delete=False)
            elif new_holding:
                locked_holding = StockHolding.objects.select_for_update().get(id=new_holding.id)
                sim_tx = StockTransaction(
                    id=instance.id,
                    holding=locked_holding,
                    transaction_type=validated_data.get('transaction_type', instance.transaction_type),
                    shares=validated_data.get('shares', instance.shares),
                    price_per_share=validated_data.get('price_per_share', instance.price_per_share),
                    fee=validated_data.get('fee', instance.fee),
                    executed_at=validated_data.get('executed_at', instance.executed_at)
                )
                validate_holding_transaction_timeline(locked_holding, pending_tx=sim_tx, is_delete=False)
            return super().update(instance, validated_data)


class StockHoldingSerializer(serializers.ModelSerializer):
    position = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['portfolio'].queryset = InvestmentPortfolio.objects.filter(user=request.user)

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

    def validate(self, attrs):
        user = self.context['request'].user
        portfolio = attrs.get('portfolio') or (self.instance.portfolio if self.instance else None)
        if portfolio and portfolio.user != user:
            raise serializers.ValidationError({'portfolio': 'Selected portfolio does not belong to user.'})

        # Lock currency changes if the holding has existing trades
        if self.instance and 'currency' in attrs:
            new_curr = attrs['currency']
            if new_curr != self.instance.currency:
                if self.instance.transactions.exists():
                    raise serializers.ValidationError({'currency': 'Cannot change currency on a holding with existing trade history.'})

        # Lock currency mismatch when moving holding to a portfolio where ticker already exists
        if self.instance and portfolio and portfolio.id != self.instance.portfolio_id:
            existing = StockHolding.objects.filter(
                user=user,
                portfolio=portfolio,
                ticker=self.instance.ticker
            ).exclude(id=self.instance.id).first()
            if existing and existing.currency != self.instance.currency:
                if existing.transactions.exists() or self.instance.transactions.exists():
                    raise serializers.ValidationError({
                        'currency': f"Cannot merge holding with currency {self.instance.currency} into existing holding with currency {existing.currency} when trade history exists."
                    })

        return attrs

    def get_position(self, obj):
        price_map = self.context.get('price_map', {})
        current_price = price_map.get(obj.ticker)
        usd_to_thb_rate = self.context.get('usd_to_thb_rate')
        snapshot_map = self.context.get('snapshot_map', {})
        snapshot = snapshot_map.get(obj.ticker)
        return calculate_detailed_position(obj, current_price=current_price, usd_to_thb_rate=usd_to_thb_rate, snapshot=snapshot)

    def get_recent_transactions(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'transactions' in obj._prefetched_objects_cache:
            txs = sorted(obj.transactions.all(), key=lambda x: x.executed_at, reverse=True)[:5]
        else:
            txs = obj.transactions.all().order_by('-executed_at')[:5]
        return StockTransactionSerializer(txs, many=True, context=self.context).data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['ticker'] = normalize_ticker(validated_data.get('ticker', ''))
        if not validated_data.get('portfolio'):
            default_pf = InvestmentPortfolio.objects.filter(user=user, is_default=True).first()
            if not default_pf:
                default_pf = InvestmentPortfolio.objects.create(
                    user=user,
                    name='Main Portfolio',
                    currency='THB',
                    is_default=True
                )
            validated_data['portfolio'] = default_pf
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
    quote = serializers.SerializerMethodField()
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
            'quote',
            'change_amount',
            'change_pct',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def _snapshot(self, obj):
        cache = self.context.setdefault('_watchlist_snapshots', {})
        if obj.ticker not in cache:
            cache[obj.ticker] = StockPriceSnapshot.objects.filter(ticker=obj.ticker).first()
        return cache[obj.ticker]

    def get_current_price(self, obj):
        price_map = self.context.get('price_map', {})
        if obj.ticker in price_map and price_map[obj.ticker] is not None:
            return float(price_map[obj.ticker])
        snapshot = self._snapshot(obj)
        return float(snapshot.price) if snapshot and snapshot.price else None

    def get_quote(self, obj):
        from .quotes import quote_metadata
        return quote_metadata(self._snapshot(obj))

    def get_change_amount(self, obj):
        snapshot = self._snapshot(obj)
        return float(snapshot.change_amount) if snapshot and snapshot.change_amount is not None else None

    def get_change_pct(self, obj):
        snapshot = self._snapshot(obj)
        return float(snapshot.change_pct) if snapshot and snapshot.change_pct is not None else None

