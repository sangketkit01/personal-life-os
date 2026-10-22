from django.db.models import Prefetch
from rest_framework import viewsets, views, permissions, status, response
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import (
    StockHolding,
    StockTransaction,
    StockPriceSnapshot,
    StockNewsArticle,
    StockWatchlist,
    InvestmentPortfolio
)
from .serializers import (
    StockHoldingSerializer,
    StockTransactionSerializer,
    StockNewsArticleSerializer,
    StockWatchlistSerializer,
    InvestmentPortfolioSerializer
)
from .services import (
    get_portfolio_overview,
    fetch_and_cache_market_prices,
    normalize_ticker,
    search_market_assets,
    get_usd_to_thb_rate
)
from .asset_catalog import verify_ticker_exists


class InvestmentPortfolioViewSet(viewsets.ModelViewSet):
    """
    CRUD พอร์ตการลงทุนแยกแต่ละตะกร้า (เหมือน Dime Multi-Portfolio)
    เช่น พอร์ต DCA หุ้นไทย, พอร์ตหุ้นสหรัฐฯ US Growth, พอร์ตคริปโต Moonshot
    """
    serializer_class = InvestmentPortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ตรวจสอบและสร้าง Main Portfolio เริ่มต้นถ้ายังไม่มี
        InvestmentPortfolio.objects.get_or_create(
            user=self.request.user,
            is_default=True,
            defaults={'name': 'Main Portfolio', 'currency': 'THB'}
        )
        return InvestmentPortfolio.objects.filter(user=self.request.user).order_by('-is_default', 'created_at')

    def perform_destroy(self, instance):
        if instance.is_default:
            raise serializers.ValidationError({'detail': 'ไม่สามารถลบพอร์ตหลัก (Default Portfolio) ได้'})
        super().perform_destroy(instance)


class MarketAssetSearchView(views.APIView):
    """
    API ค้นหาสินทรัพย์สำหรับช่องกรอก Autocomplete ป้องกันการกรอกผิด
    รองรับการค้นหาทั้งหุ้นไทย (SET), หุ้นสหรัฐฯ (US), คริปโต (Crypto), กองทุนรวม (Fund)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        q = request.query_params.get('q', '')
        asset_type = request.query_params.get('asset_type')
        results = search_market_assets(query=q, asset_type=asset_type)
        return response.Response(results)


class PortfolioOverviewView(views.APIView):
    """API สรุปภาพรวมมูลค่าพอร์ต และผลตอบแทน PnL รวมทั้งหมด (รองรับสลับมุมมอง THB / USD, กรองพอร์ต, กรองประเภทสินทรัพย์)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        currency = request.query_params.get('currency', 'THB')
        portfolio_id = request.query_params.get('portfolio_id')
        asset_type = request.query_params.get('asset_type')
        data = get_portfolio_overview(
            request.user,
            currency=currency,
            portfolio_id=portfolio_id,
            asset_type=asset_type
        )
        return response.Response(data)


class PortfolioRefreshView(views.APIView):
    """API สั่งดึงราคาตลาดล่าสุดของหุ้นในพอร์ตผ่าน yfinance พร้อมอัตราแลกเปลี่ยน USD/THB (รองรับตรวจสอบเวลาเปิด-ปิดตลาด)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        holdings = StockHolding.objects.filter(user=request.user)
        tickers = [h.ticker for h in holdings]
        if 'USDTHB=X' not in tickers:
            tickers.append('USDTHB=X')

        force = request.data.get('force', False)
        if isinstance(force, str):
            force = force.lower() in ('true', '1')

        # ดึงราคาตลาดสดผ่าน yfinance โดยเคารพเวลาเปิด-ปิดตลาด (ถ้าไม่ได้ force)
        prices = fetch_and_cache_market_prices(tickers, force=force, respect_market_hours=not force)

        # ส่งข้อมูลภาพรวมพอร์ตที่อัปเดตราคาใหม่กลับไป
        currency = request.data.get('currency') or request.query_params.get('currency', 'THB')
        portfolio_id = request.data.get('portfolio_id') or request.query_params.get('portfolio_id')
        asset_type = request.data.get('asset_type') or request.query_params.get('asset_type')
        data = get_portfolio_overview(
            request.user,
            currency=currency,
            portfolio_id=portfolio_id,
            asset_type=asset_type
        )
        data['updated_prices'] = {t: float(p) for t, p in prices.items()}
        return response.Response(data)


class MarketStatusView(views.APIView):
    """API ตรวจสอบสถานะเวลาทำการตลาด (SET, US, CRYPTO) และความเหมาะสมในการดึงราคา 1 นาทีแบบ Real-Time"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .market_hours import get_all_market_statuses, is_market_open_for_ticker
        status_data = get_all_market_statuses()

        holdings = StockHolding.objects.filter(user=request.user)
        user_tickers_status = []
        open_holdings_count = 0

        for h in holdings:
            is_open = is_market_open_for_ticker(h.ticker, h.asset_type)
            if is_open:
                open_holdings_count += 1
            user_tickers_status.append({
                'ticker': h.ticker,
                'name': h.name,
                'asset_type': h.asset_type,
                'is_open': is_open
            })

        status_data['user_open_holdings_count'] = open_holdings_count
        status_data['user_total_holdings_count'] = len(user_tickers_status)
        status_data['should_poll_realtime'] = (open_holdings_count > 0)
        status_data['holdings_status'] = user_tickers_status

        return response.Response(status_data)


class StockHoldingViewSet(viewsets.ModelViewSet):
    """CRUD สินทรัพย์ในพอร์ต (Stock Holdings)"""
    serializer_class = StockHoldingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StockHolding.objects.filter(user=self.request.user)
        portfolio_id = self.request.query_params.get('portfolio_id')
        asset_type = self.request.query_params.get('asset_type')

        if portfolio_id and portfolio_id.upper() != 'ALL':
            qs = qs.filter(portfolio_id=portfolio_id)
        if asset_type and asset_type.upper() != 'ALL':
            qs = qs.filter(asset_type=asset_type.upper())

        return qs.prefetch_related(
            Prefetch('transactions', queryset=StockTransaction.objects.order_by('executed_at'))
        ).order_by('ticker')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        tickers = [h.ticker for h in queryset]
        price_map = {s.ticker: s.price for s in StockPriceSnapshot.objects.filter(ticker__in=tickers)}
        rate = get_usd_to_thb_rate()

        context = {'request': request, 'price_map': price_map, 'usd_to_thb_rate': rate}
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context=context)
        return response.Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        snapshot = StockPriceSnapshot.objects.filter(ticker=instance.ticker).first()
        context = {
            'request': request,
            'price_map': {instance.ticker: snapshot.price if snapshot else None},
            'usd_to_thb_rate': get_usd_to_thb_rate()
        }
        serializer = self.get_serializer(instance, context=context)
        return response.Response(serializer.data)

    @action(detail=False, methods=['get'], url_path=r'by-ticker/(?P<ticker>[^/]+)')
    def by_ticker(self, request, ticker=None):
        """
        Universal Asset Profile:
        รองรับทั้งสินทรัพย์ที่มีในพอร์ต (is_held=True) และสินทรัพย์ใหม่ที่ยังไม่ได้ซื้อ (is_held=False)
        F04: รองรับ holding_id หรือ portfolio_id ใน query params เพื่อให้เจาะจง holding ในพอร์ตที่ถูกต้อง
        """
        clean_ticker = normalize_ticker(ticker)
        holding_id = request.query_params.get('holding_id')
        portfolio_id = request.query_params.get('portfolio_id')

        holding_qs = StockHolding.objects.filter(user=request.user, ticker__iexact=clean_ticker).select_related('portfolio')
        holding = None
        if holding_id:
            holding = holding_qs.filter(id=holding_id).first()
        elif portfolio_id and str(portfolio_id).upper() != 'ALL':
            holding = holding_qs.filter(portfolio_id=portfolio_id).first()

        if not holding:
            holding = holding_qs.first()

        is_watchlisted = StockWatchlist.objects.filter(user=request.user, ticker__iexact=clean_ticker).exists()

        if holding:
            snapshot = StockPriceSnapshot.objects.filter(ticker=holding.ticker).first()
            context = {
                'request': request,
                'price_map': {holding.ticker: snapshot.price if snapshot else None},
                'usd_to_thb_rate': get_usd_to_thb_rate()
            }
            data = self.get_serializer(holding, context=context).data
            data['is_held'] = True
            data['is_watchlisted'] = is_watchlisted
            # รายการพอร์ตทั้งหมดที่ถือหุ้นตัวนี้ (สำหรับสลับพอร์ตในหน้ารายละเอียด)
            data['all_holdings'] = [
                {
                    'id': str(h.id),
                    'portfolio_id': str(h.portfolio_id),
                    'portfolio_name': h.portfolio.name,
                }
                for h in holding_qs
            ]
            return response.Response(data)

        # Universal Mode: ตรวจสอบและดึงข้อมูลตลาดของสินทรัพย์ใหม่
        verified = verify_ticker_exists(clean_ticker)
        if not verified and not clean_ticker.endswith('.BK') and not clean_ticker.endswith('-USD'):
            th_v = verify_ticker_exists(f"{clean_ticker}.BK")
            if th_v:
                clean_ticker = f"{clean_ticker}.BK"
                verified = th_v

        if not verified:
            return response.Response({'detail': f"ไม่พบข้อมูลสินทรัพย์ '{clean_ticker}' ในตลาดการเงิน"}, status=status.HTTP_404_NOT_FOUND)

        fetch_and_cache_market_prices([clean_ticker])
        snapshot = StockPriceSnapshot.objects.filter(ticker=clean_ticker).first()
        current_price = float(snapshot.price) if snapshot and snapshot.price else 0.0
        change_amount = float(snapshot.change_amount) if snapshot and snapshot.change_amount else 0.0
        change_pct = float(snapshot.change_pct) if snapshot and snapshot.change_pct else 0.0
        currency = verified.get('currency', snapshot.currency if snapshot else 'USD')

        return response.Response({
            'id': None,
            'ticker': clean_ticker,
            'name': verified.get('name', clean_ticker),
            'currency': currency,
            'asset_type': verified.get('asset_type', 'STOCK'),
            'is_held': False,
            'is_watchlisted': is_watchlisted,
            'position': {
                'shares': 0,
                'avg_cost': 0,
                'total_invested': 0,
                'current_price': current_price,
                'market_value': 0,
                'unrealized_pnl': 0,
                'unrealized_pnl_pct': 0,
                'change_amount': change_amount,
                'change_pct': change_pct,
                'market_session': getattr(snapshot, 'market_session', 'REGULAR'),
                'regular_price': float(snapshot.regular_price) if snapshot and snapshot.regular_price else current_price,
                'is_active': False
            },
            'recent_transactions': []
        })

    @action(detail=False, methods=['get'], url_path=r'by-ticker/(?P<ticker>[^/]+)/chart')
    def chart(self, request, ticker=None):
        """
        ดึงข้อมูลกราฟราคาย้อนหลังสไตล์ Dime:
        Period options: 1D, 5D, 1M, 6M, 1Y, ALL
        """
        clean_ticker = normalize_ticker(ticker)
        period_param = request.query_params.get('period', '1D').upper()

        period_map = {
            '1D': ('1d', '2m', 60),      # period, interval, cache_ttl_seconds
            '5D': ('5d', '15m', 900),
            '1M': ('1mo', '1d', 3600),
            '6M': ('6mo', '1d', 3600 * 4),
            '1Y': ('1y', '1d', 3600 * 12),
            'ALL': ('max', '1wk', 3600 * 24),
        }

        period, interval, cache_ttl = period_map.get(period_param, ('1d', '2m', 60))
        cache_key = f"chart_{clean_ticker}_{period_param}"

        from django.core.cache import cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return response.Response(cached_data)

        snapshot = StockPriceSnapshot.objects.filter(ticker=clean_ticker).first()

        import yfinance as yf
        try:
            stock = yf.Ticker(clean_ticker)
            hist = stock.history(period=period, interval=interval)

            points = []
            if not hist.empty:
                for idx, row in hist.iterrows():
                    close_val = row['Close']
                    if close_val is not None and not (isinstance(close_val, float) and (close_val != close_val)):
                        t_str = idx.isoformat() if hasattr(idx, 'isoformat') else str(idx)
                        points.append({
                            'time': t_str,
                            'price': round(float(close_val), 4),
                            'volume': int(row.get('Volume', 0)) if 'Volume' in row else 0
                        })

            current_price = float(snapshot.price) if snapshot else (points[-1]['price'] if points else 0.0)
            prev_close = float(snapshot.previous_close) if (snapshot and snapshot.previous_close) else (points[0]['price'] if points else current_price)

            if points and period_param != '1D':
                base_price = points[0]['price']
            else:
                base_price = prev_close

            change_amount = current_price - base_price
            change_pct = ((change_amount / base_price) * 100) if base_price > 0 else 0.0

            result = {
                'ticker': clean_ticker,
                'period': period_param,
                'currency': snapshot.currency if snapshot else ('THB' if clean_ticker.endswith('.BK') else 'USD'),
                'current_price': round(current_price, 4),
                'previous_close': round(prev_close, 4),
                'base_price': round(base_price, 4),
                'change_amount': round(change_amount, 4),
                'change_pct': round(change_pct, 2),
                'points': points
            }

            cache.set(cache_key, result, timeout=cache_ttl)
            return response.Response(result)

        except Exception:
            current_price = float(snapshot.price) if snapshot else 0.0
            prev_close = float(snapshot.previous_close) if (snapshot and snapshot.previous_close) else current_price
            change_amt = float(snapshot.change_amount) if (snapshot and snapshot.change_amount) else 0.0
            change_pct = float(snapshot.change_pct) if snapshot else 0.0

            return response.Response({
                'ticker': clean_ticker,
                'period': period_param,
                'currency': snapshot.currency if snapshot else ('THB' if clean_ticker.endswith('.BK') else 'USD'),
                'current_price': round(current_price, 4),
                'previous_close': round(prev_close, 4),
                'base_price': round(prev_close, 4),
                'change_amount': round(change_amt, 4),
                'change_pct': round(change_pct, 2),
                'points': []
            })

    def perform_update(self, serializer):
        target_portfolio = serializer.validated_data.get('portfolio')
        instance = serializer.instance
        if target_portfolio and instance.portfolio_id != target_portfolio.id:
            existing = StockHolding.objects.filter(
                user=self.request.user,
                portfolio=target_portfolio,
                ticker=instance.ticker
            ).exclude(id=instance.id).first()
            if existing:
                instance.transactions.all().update(holding=existing)
                for field in ('name', 'asset_type', 'currency', 'notes'):
                    if field in serializer.validated_data:
                        setattr(existing, field, serializer.validated_data[field])
                existing.save()
                instance.delete()
                serializer.instance = existing
                return
        serializer.save()

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """
        ย้ายหุ้นและประวัติการเทรดทั้งหมดไปยังพอร์ตการลงทุนอื่น (Dime Multi-Portfolio)
        - ถ้าพอร์ตเป้าหมายยังไม่มีหุ้นตัวนี้: อัปเดต holding.portfolio ไปยังพอร์ตใหม่
        - ถ้าพอร์ตเป้าหมายมีหุ้นตัวนี้อยู่แล้ว: ผนวกประวัติการเทรด (Merge transactions) ทั้งหมดเข้ากับ holding ปลายทางอัตโนมัติ แล้วลบ holding เดิม
        """
        holding = self.get_object()
        target_portfolio_id = request.data.get('target_portfolio_id') or request.data.get('portfolio')

        if not target_portfolio_id:
            return response.Response(
                {'detail': 'target_portfolio_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_portfolio = InvestmentPortfolio.objects.filter(
            id=target_portfolio_id,
            user=request.user
        ).first()

        if not target_portfolio:
            return response.Response(
                {'detail': 'Target portfolio not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        context = {
            'request': request,
            'price_map': {holding.ticker: getattr(StockPriceSnapshot.objects.filter(ticker=holding.ticker).first(), 'price', None)},
            'usd_to_thb_rate': get_usd_to_thb_rate()
        }

        if holding.portfolio_id == target_portfolio.id:
            serializer = self.get_serializer(holding, context=context)
            return response.Response({
                'detail': f'Holding {holding.ticker} is already in {target_portfolio.name}.',
                'holding': serializer.data,
                'merged': False
            })

        # ตรวจสอบว่าพอร์ตเป้าหมายมีหุ้น Ticker นี้อยู่แล้วหรือไม่
        existing_target_holding = StockHolding.objects.filter(
            user=request.user,
            portfolio=target_portfolio,
            ticker=holding.ticker
        ).first()

        if existing_target_holding:
            holding.transactions.all().update(holding=existing_target_holding)
            if holding.notes and not existing_target_holding.notes:
                existing_target_holding.notes = holding.notes
                existing_target_holding.save(update_fields=['notes'])
            holding.delete()

            serializer = self.get_serializer(existing_target_holding, context=context)
            return response.Response({
                'detail': f'Merged {existing_target_holding.ticker} trades into {target_portfolio.name}.',
                'holding': serializer.data,
                'merged': True,
                'target_portfolio_id': str(target_portfolio.id),
                'target_portfolio_name': target_portfolio.name
            })
        else:
            holding.portfolio = target_portfolio
            holding.save(update_fields=['portfolio'])

            serializer = self.get_serializer(holding, context=context)
            return response.Response({
                'detail': f'Moved {holding.ticker} to {target_portfolio.name}.',
                'holding': serializer.data,
                'merged': False,
                'target_portfolio_id': str(target_portfolio.id),
                'target_portfolio_name': target_portfolio.name
            })


class StockTransactionViewSet(viewsets.ModelViewSet):
    """CRUD ประวัติรายการซื้อขายหุ้น (Transactions)"""
    serializer_class = StockTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StockTransaction.objects.filter(user=self.request.user).select_related('holding', 'holding__portfolio')
        holding_id = self.request.query_params.get('holding_id')
        portfolio_id = self.request.query_params.get('portfolio_id')
        ticker = self.request.query_params.get('ticker')

        if holding_id:
            qs = qs.filter(holding_id=holding_id)
        if portfolio_id and portfolio_id.upper() != 'ALL':
            qs = qs.filter(holding__portfolio_id=portfolio_id)
        if ticker:
            qs = qs.filter(holding__ticker__iexact=ticker)

        return qs.order_by('-executed_at')

    def perform_create(self, serializer):
        tx = serializer.save()
        log_activity(
            self.request.user,
            'PORTFOLIO',
            f'{tx.transaction_type}_STOCK',
            f'บันทึกรายการ {tx.transaction_type} {tx.shares} หน่วย {tx.holding.ticker} ที่ราคา {tx.price_per_share} ({tx.currency})',
            request=self.request
        )

    def perform_update(self, serializer):
        tx = serializer.save()
        log_activity(
            self.request.user,
            'PORTFOLIO',
            f'UPDATE_{tx.transaction_type}_STOCK',
            f'แก้ไขรายการ {tx.transaction_type} {tx.shares} หน่วย {tx.holding.ticker} ที่ราคา {tx.price_per_share} ({tx.currency})',
            request=self.request
        )


class StockNewsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API แสดงข่าวสารสินทรัพย์และการแปลภาษาไทย
    - กรองตาม Ticker: ?ticker=NVDA
    - เฉพาะข่าววันนี้: ?today_only=true
    - เรียงตาม published_at ล่าสุด
    """
    serializer_class = StockNewsArticleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StockNewsArticle.objects.all()

        ticker = self.request.query_params.get('ticker')
        today_only = self.request.query_params.get('today_only')
        held_only = self.request.query_params.get('held_only')
        watchlist_only = self.request.query_params.get('watchlist_only')

        if ticker:
            clean_ticker = normalize_ticker(ticker)
            qs = qs.filter(ticker__iexact=clean_ticker)
            # On-demand News Ingestion: หากยังไม่มีข่าวของหุ้นตัวนี้ในระบบ ให้ดึงและแปลสดทันที
            if not qs.exists():
                from .news_service import ingest_news_for_ticker
                ingest_news_for_ticker(clean_ticker, limit_per_source=3)
                qs = StockNewsArticle.objects.filter(ticker__iexact=clean_ticker)
            else:
                # ตรวจสอบและซ่อมแซมข่าวที่ยังไม่ได้แปลภาษาไทยแบบ On-the-fly
                import re
                from .news_service import enrich_article_if_empty
                untranslated = [a for a in qs[:3] if not bool(re.search(r'[\u0e00-\u0e7f]', a.title_th or ''))]
                for art in untranslated:
                    try:
                        enrich_article_if_empty(art, force=True)
                    except Exception:
                        pass
                if untranslated:
                    qs = StockNewsArticle.objects.filter(ticker__iexact=clean_ticker)
        elif watchlist_only and watchlist_only.lower() == 'true':
            watch_tickers = StockWatchlist.objects.filter(user=self.request.user).values_list('ticker', flat=True)
            qs = qs.filter(ticker__in=watch_tickers)
        elif held_only and held_only.lower() == 'true':
            held_tickers = StockHolding.objects.filter(user=self.request.user).values_list('ticker', flat=True)
            qs = qs.filter(ticker__in=held_tickers)

        if today_only and today_only.lower() == 'true':
            from django.utils import timezone
            today = timezone.localdate()
            qs = qs.filter(published_at__date=today)

        return qs.order_by('-published_at', '-created_at')

    def retrieve(self, request, *args, **kwargs):
        """ดึงรายละเอียดข่าว พร้อม Lazy Backfill เนื้อหาฉบับเต็มหากยังไม่มีหรือแปลไม่ครบ 100%"""
        import re
        instance = self.get_object()
        has_thai_title = bool(re.search(r'[\u0e00-\u0e7f]', instance.title_th or ''))
        has_thai_content = bool(re.search(r'[\u0e00-\u0e7f]', instance.content_th or ''))
        eng_paras = len([p for p in (instance.content or '').split('\n\n') if p.strip()])
        th_paras = len([p for p in (instance.content_th or '').split('\n\n') if p.strip()])
        if not instance.content or not instance.content_th or not has_thai_title or not has_thai_content or eng_paras > th_paras + 1:
            from .news_service import enrich_article_if_empty
            instance = enrich_article_if_empty(instance, force=(not has_thai_title or not has_thai_content))
        serializer = self.get_serializer(instance)
        return response.Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='sync')
    def sync(self, request):
        """Action สั่งดึงและแปลข่าวใหม่ล่าสุดของหุ้นในพอร์ตทันที"""
        from .news_service import sync_all_portfolio_news
        result = sync_all_portfolio_news(user=request.user)
        return response.Response({
            'message': 'ซิงค์และแปลข่าวสารล่าสุดเรียบร้อยแล้ว',
            'details': result
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='translate')
    def translate(self, request, pk=None):
        """Action แปลข่าวเป็นภาษาไทยและดึงเนื้อหาฉบับเต็ม On-demand"""
        article = self.get_object()
        from .news_service import enrich_article_if_empty
        article = enrich_article_if_empty(article)
        return response.Response(StockNewsArticleSerializer(article).data)


class StockWatchlistViewSet(viewsets.ModelViewSet):
    """
    CRUD รายการสินทรัพย์เฝ้าดู (Watchlist) สำหรับศึกษาและติดตามราคาก่อนซื้อ
    """
    serializer_class = StockWatchlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StockWatchlist.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        ticker_input = request.data.get('ticker', '')
        if not ticker_input:
            return response.Response({'ticker': 'กรุณาระบุสัญลักษณ์สินทรัพย์'}, status=status.HTTP_400_BAD_REQUEST)

        clean_ticker = normalize_ticker(ticker_input)
        verified = verify_ticker_exists(clean_ticker)
        if not verified and not clean_ticker.endswith('.BK') and not clean_ticker.endswith('-USD'):
            th_v = verify_ticker_exists(f"{clean_ticker}.BK")
            if th_v:
                clean_ticker = f"{clean_ticker}.BK"
                verified = th_v

        name = request.data.get('name') or (verified.get('name') if verified else clean_ticker)
        asset_type = request.data.get('asset_type') or (verified.get('asset_type') if verified else 'STOCK')
        currency = request.data.get('currency') or (verified.get('currency') if verified else 'USD')

        item, created = StockWatchlist.objects.get_or_create(
            user=request.user,
            ticker=clean_ticker,
            defaults={
                'name': name,
                'asset_type': asset_type,
                'currency': currency,
                'notes': request.data.get('notes', '')
            }
        )

        fetch_and_cache_market_prices([clean_ticker])
        from .news_service import ingest_news_for_ticker
        ingest_news_for_ticker(clean_ticker, limit_per_source=2)

        return response.Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle(self, request):
        """Toggle watchlist status: สลับเพิ่มหรือเอาออกจาก Watchlist"""
        ticker_input = request.data.get('ticker', '')
        if not ticker_input:
            return response.Response({'ticker': 'กรุณาระบุสัญลักษณ์สินทรัพย์'}, status=status.HTTP_400_BAD_REQUEST)

        clean_ticker = normalize_ticker(ticker_input)
        existing = StockWatchlist.objects.filter(user=request.user, ticker__iexact=clean_ticker).first()
        if existing:
            existing.delete()
            return response.Response({
                'is_watchlisted': False,
                'ticker': clean_ticker,
                'message': f'นำ {clean_ticker} ออกจาก Watchlist เรียบร้อยแล้ว'
            }, status=status.HTTP_200_OK)

        verified = verify_ticker_exists(clean_ticker)
        if not verified and not clean_ticker.endswith('.BK') and not clean_ticker.endswith('-USD'):
            th_v = verify_ticker_exists(f"{clean_ticker}.BK")
            if th_v:
                clean_ticker = f"{clean_ticker}.BK"
                verified = th_v

        name = verified.get('name', clean_ticker) if verified else clean_ticker
        asset_type = verified.get('asset_type', 'STOCK') if verified else 'STOCK'
        currency = verified.get('currency', 'USD') if verified else 'USD'

        created = StockWatchlist.objects.create(
            user=request.user,
            ticker=clean_ticker,
            name=name,
            asset_type=asset_type,
            currency=currency
        )
        fetch_and_cache_market_prices([clean_ticker])
        from .news_service import ingest_news_for_ticker
        ingest_news_for_ticker(clean_ticker, limit_per_source=2)

        return response.Response({
            'is_watchlisted': True,
            'ticker': clean_ticker,
            'data': self.get_serializer(created).data,
            'message': f'เพิ่ม {clean_ticker} ลงใน Watchlist เรียบร้อยแล้ว'
        }, status=status.HTTP_201_CREATED)
