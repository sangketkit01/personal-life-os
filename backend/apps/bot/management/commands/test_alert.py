import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from telegram import Bot
from apps.bot.dispatcher import get_due_tomorrow_obligations_for_user, send_alert_for_obligation
from apps.finance.models import FinancialObligation, ObligationType
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Trigger an immediate test alert to a user on Telegram'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to test')

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} not found"))
            return

        chat_id = user.telegram_chat_id
        if not chat_id:
            self.stdout.write(self.style.ERROR(f"User {username} has not linked Telegram yet (chat_id is null)"))
            return

        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(self.style.ERROR("TELEGRAM_BOT_TOKEN is not configured"))
            return

        async def run_test():
            bot = Bot(token=token)
            due_items = await get_due_tomorrow_obligations_for_user(user)

            if not due_items:
                # If no bills are due tomorrow, dispatch a direct test ping
                self.stdout.write(self.style.WARNING("No bills due tomorrow for this user. Sending a direct test ping..."))
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🔔 *Telegram Butler Notification Test*\n\n"
                        f"Hello *{user.username}*! Bot connection is working properly (100%) ⚡\n\n"
                        f"Every morning at *10:00 AM*, any bills or Free Trials expiring tomorrow will "
                        f"be sent here with quick action buttons ([✅ Paid] or [🔗 Cancel link])."
                    ),
                    parse_mode='Markdown'
                )
                self.stdout.write(self.style.SUCCESS(f"[OK] Test ping sent successfully to {username} ({chat_id})"))
            else:
                self.stdout.write(f"Found {len(due_items)} items due. Sending alerts...")
                for ob in due_items:
                    await send_alert_for_obligation(bot, chat_id, ob)
                self.stdout.write(self.style.SUCCESS(f"[OK] Sent {len(due_items)} alerts to {username} ({chat_id})"))

        asyncio.run(run_test())
