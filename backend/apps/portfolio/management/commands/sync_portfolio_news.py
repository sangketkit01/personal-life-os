from django.core.management.base import BaseCommand
from apps.portfolio.scheduler import sync_hourly_portfolio_news
from apps.portfolio.news_service import ingest_news_for_ticker


class Command(BaseCommand):
    help = 'Automatically ingest and translate portfolio market news (Hourly News Sync / On-Demand)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker',
            type=str,
            help='Specify single ticker symbol e.g. NVDA, PTT.BK, BTC-USD'
        )

    def handle(self, *args, **options):
        ticker = options.get('ticker')
        if ticker:
            self.stdout.write(self.style.NOTICE(f"Syncing news for single ticker: {ticker}..."))
            count = ingest_news_for_ticker(ticker, limit_per_source=3)
            self.stdout.write(self.style.SUCCESS(f"Done! {count} new articles added for {ticker}."))
        else:
            self.stdout.write(self.style.NOTICE("Running hourly news sync across all user holdings..."))
            res = sync_hourly_portfolio_news()
            self.stdout.write(self.style.SUCCESS(
                f"Sync completed: {res.get('new_articles', 0)} new articles added across {res.get('tickers_count', 0)} tickers."
            ))
