import os
import sys
from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portfolio'

    def ready(self):
        # หลีกเลี่ยงการรัน scheduler ขณะทำ migrate, test หรือคำสั่ง CLI อื่นๆ
        skip_commands = ['migrate', 'makemigrations', 'test', 'collectstatic', 'shell']
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # ป้องกันการรันซ้ำ 2 ครั้งเมื่อใช้ Django runserver auto-reloader
        is_main_worker = os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv
        if is_main_worker:
            try:
                from .scheduler import start_portfolio_scheduler
                start_portfolio_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not initialize background scheduler: {e}")
