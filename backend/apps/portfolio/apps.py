import os
import sys
from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portfolio'

    def ready(self):
        # Avoid running scheduler during migrate, test, or CLI management commands.
        # 'run_bot' is skipped too: the bot worker schedules the same hourly news
        # sync via its own job_queue, so running both would double-ingest (P1-BOT-04).
        skip_commands = ['migrate', 'makemigrations', 'test', 'collectstatic', 'shell', 'run_bot']
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # Prevent double execution with Django runserver auto-reloader
        is_main_worker = os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv
        if is_main_worker:
            try:
                from .scheduler import start_portfolio_scheduler
                start_portfolio_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not initialize background scheduler: {e}")
