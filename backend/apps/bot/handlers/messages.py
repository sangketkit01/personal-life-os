import re
from datetime import datetime, date
from decimal import Decimal
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationType
from apps.finance.strategies import ObligationStrategyFactory

User = get_user_model()


@sync_to_async
def get_user_by_chat_id(chat_id: int):
    return User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()


@sync_to_async
def create_obligation_from_chat(user, title: str, ob_type: str, amount: Decimal, metadata: dict, due_date: date = None):
    strategy = ObligationStrategyFactory.get_strategy(ob_type)
    cleaned_metadata = strategy.validate_metadata(metadata)

    if not due_date:
        due_date = timezone.localdate() + timezone.timedelta(days=30)

    ob = FinancialObligation.objects.create(
        user=user,
        title=title,
        type=ob_type,
        amount=amount,
        due_date=due_date,
        billing_day=due_date.day,
        metadata=cleaned_metadata
    )
    return ob


def parse_quick_text(text: str):
    """
    Parse natural language text into financial obligation data.
    Examples:
    - installment iPad 1500 10
    - trial Canva 499 email work@example.com
    - sub Netflix 419
    - debt John 500
    """
    clean_text = text.strip()
    words = clean_text.split()
    if len(words) < 2:
        return None

    first_word = words[0].lower()

    # 1. Installment: installment <name> <amount> <terms>
    if first_word in ['installment', 'inst']:
        match = re.search(r'(?:installment|inst)\s+([^\d]+)\s+(\d+(?:\.\d+)?)\s+(\d+)\s*(?:terms?)?', clean_text, re.IGNORECASE)
        if match:
            item_name = match.group(1).strip()
            title = f"Installment: {item_name}" if not item_name.lower().startswith('installment') else item_name
            amount = Decimal(match.group(2))
            terms = int(match.group(3))
            return {
                'type': ObligationType.INSTALLMENT,
                'title': title,
                'amount': amount,
                'metadata': {
                    'total_terms': terms,
                    'current_term': 0,
                    'lender': item_name
                }
            }

    # 2. Free Trial: trial <name> <amount> [email]
    if 'trial' in first_word:
        match = re.search(r'trial\s+([^\d]+)\s+(\d+(?:\.\d+)?)', clean_text, re.IGNORECASE)
        if match:
            title = f"{match.group(1).strip()} Free Trial"
            amount = Decimal(match.group(2))
            email = ''
            if 'email' in clean_text or '@' in clean_text:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', clean_text)
                if email_match:
                    email = email_match.group(0)

            return {
                'type': ObligationType.FREE_TRIAL,
                'title': title,
                'amount': amount,
                'metadata': {
                    'account_email': email,
                    'auto_renew_cost': float(amount)
                }
            }

    # 3. Subscription: sub <name> <amount>
    if 'sub' in first_word or first_word == 'subscription':
        match = re.search(r'(?:sub|subscription)\s+(.+?)\s+(\d+(?:\.\d+)?)', clean_text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            amount = Decimal(match.group(2))
            return {
                'type': ObligationType.SUBSCRIPTION,
                'title': title,
                'amount': amount,
                'metadata': {
                    'billing_cycle': 'MONTHLY'
                }
            }

    # 4. Debt: debt <person> <amount>
    if first_word in ['debt', 'loan']:
        match = re.search(r'(?:debt|loan)\s+(.+?)\s+(\d+(?:\.\d+)?)', clean_text, re.IGNORECASE)
        if match:
            person = match.group(1).strip()
            amount = Decimal(match.group(2))
            return {
                'type': ObligationType.DEBT,
                'title': f"Debt: {person}",
                'amount': amount,
                'metadata': {
                    'counterparty': person,
                    'is_flexible': True
                }
            }

    return None


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages sent to bot (Quick-Capture)"""
    if not update.effective_chat or not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ Your Telegram account is not connected. Please connect via your profile settings in the web app.")
        return

    text = update.message.text
    parsed = parse_quick_text(text)

    if parsed:
        ob = await create_obligation_from_chat(
            user=user,
            title=parsed['title'],
            ob_type=parsed['type'],
            amount=parsed['amount'],
            metadata=parsed['metadata']
        )

        reply = (
            f"⚡ *Quick Obligation Recorded!*\n\n"
            f"• Title: *{ob.title}*\n"
            f"• Amount: *฿{float(ob.amount):,.2f}*\n"
            f"• Type: `{ob.type}`\n"
            f"• Next Due Date: *{ob.due_date.strftime('%d/%m/%Y')}*\n\n"
            f"_Data has been synchronized with your Financial Radar dashboard._"
        )
        await update.message.reply_text(reply, parse_mode='Markdown')
    else:
        # Invalid syntax fallback
        await update.message.reply_text(
            "💡 *Quick capture syntax examples:*\n"
            "• `installment iPad 1500 10`\n"
            "• `trial Canva 499 email work@example.com`\n"
            "• `sub Netflix 419`\n"
            "• `debt John 500`",
            parse_mode='Markdown'
        )
