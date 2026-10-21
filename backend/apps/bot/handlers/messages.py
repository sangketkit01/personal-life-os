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
    วิเคราะห์ข้อความภาษาคนเพื่อแปลงเป็นข้อมูลภาระการเงิน
    ตัวอย่าง:
    - ผ่อน tiktok 450 3 งวด
    - trial canva 499 2026-10-25 เมล work@gmail.com
    - sub netflix 419
    - หนี้ ตั้ม 500
    """
    clean_text = text.strip()
    words = clean_text.split()
    if len(words) < 2:
        return None

    first_word = words[0].lower()

    # 1. เคส: ผ่อน <ชื่อ> <ยอด> <จำนวนงวด>
    if 'ผ่อน' in first_word or first_word == 'installment':
        match = re.search(r'(?:ผ่อน|installment)\s+([^\d]+)\s+(\d+(?:\.\d+)?)\s+(\d+)\s*(?:งวด)?', clean_text, re.IGNORECASE)
        if match:
            title = f"ผ่อน {match.group(1).strip()}"
            amount = Decimal(match.group(2))
            terms = int(match.group(3))
            return {
                'type': ObligationType.INSTALLMENT,
                'title': title,
                'amount': amount,
                'metadata': {
                    'total_terms': terms,
                    'current_term': 0,
                    'lender': match.group(1).strip()
                }
            }

    # 2. เคส: trial <ชื่อ> <ยอด> [วันหมดอายุ]
    if 'trial' in first_word:
        # trial canva 499 หรือ trial canva 499 2026-10-25
        match = re.search(r'trial\s+([^\d]+)\s+(\d+(?:\.\d+)?)', clean_text, re.IGNORECASE)
        if match:
            title = f"{match.group(1).strip()} Free Trial"
            amount = Decimal(match.group(2))
            email = ''
            if 'เมล' in clean_text or '@' in clean_text:
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

    # 3. เคส: sub <ชื่อ> <ยอด>
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

    # 4. เคส: หนี้ <คน> <ยอด>
    if 'หนี้' in first_word or first_word == 'debt':
        match = re.search(r'(?:หนี้|debt)\s+(.+?)\s+(\d+(?:\.\d+)?)', clean_text, re.IGNORECASE)
        if match:
            person = match.group(1).strip()
            amount = Decimal(match.group(2))
            return {
                'type': ObligationType.DEBT,
                'title': f"หนี้ {person}",
                'amount': amount,
                'metadata': {
                    'counterparty': person,
                    'is_flexible': True
                }
            }

    return None


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler จัดการข้อความทั่วไปที่ส่งเข้ามาในห้องแชต (Quick-Capture)"""
    if not update.effective_chat or not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ บัญชีของคุณยังไม่ได้เชื่อมต่อกับระบบ กรุณากดเชื่อมต่อจากหน้าเว็บก่อนครับ")
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
            f"⚡ *บันทึกรายการด่วนสำเร็จแล้ว!*\n\n"
            f"• รายการ: *{ob.title}*\n"
            f"• ยอดเงิน: *฿{float(ob.amount):,.2f}*\n"
            f"• ประเภท: `{ob.type}`\n"
            f"• วันตัดรอบถัดไป: *{ob.due_date.strftime('%d/%m/%Y')}*\n\n"
            f"_ข้อมูลถูกซิงค์ขึ้นหน้า Dashboard เรียบร้อยแล้วครับ_"
        )
        await update.message.reply_text(reply, parse_mode='Markdown')
    else:
        # ข้อความที่ไม่ตรงรูปแบบ
        await update.message.reply_text(
            "💡 *ตัวอย่างการพิมพ์บันทึกด่วน:*\n"
            "• `ผ่อน tiktok 450 3 งวด`\n"
            "• `trial canva 499 เมล work@gmail.com`\n"
            "• `sub netflix 419`\n"
            "• `หนี้ ตั้ม 500`",
            parse_mode='Markdown'
        )
