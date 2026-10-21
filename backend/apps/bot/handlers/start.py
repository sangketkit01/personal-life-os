from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from apps.finance.services import get_financial_overview
from apps.portfolio.services import get_portfolio_overview

User = get_user_model()


@sync_to_async
def pair_user_by_token(token: str, chat_id: int):
    """จับคู่ Telegram Chat ID เข้ากับ User ตาม One-time Token"""
    try:
        user = User.objects.get(telegram_connect_token=token)
        user.telegram_chat_id = str(chat_id)
        user.telegram_connect_token = None
        user.save(update_fields=['telegram_chat_id', 'telegram_connect_token'])
        return user
    except User.DoesNotExist:
        return None


@sync_to_async
def get_user_by_chat_id(chat_id: int):
    """ค้นหา User ตาม Telegram Chat ID"""
    return User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()


@sync_to_async
def get_user_overview_summary(user):
    """ดึงข้อมูลสรุปการเงินของ User คนนี้"""
    return get_financial_overview(user)


@sync_to_async
def get_user_portfolio_summary(user):
    """ดึงข้อมูลสรุปพอร์ตการลงทุนของ User คนนี้"""
    return get_portfolio_overview(user)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler สำหรับคำสั่ง /start และ /start <TOKEN>"""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    args = context.args

    # กรณีมี Token ส่งมาด้วย เช่น /start TOKEN_1234
    if args and len(args) > 0:
        connect_token = args[0].strip()
        user = await pair_user_by_token(connect_token, chat_id)

        if user:
            text = (
                f"🎉 *เชื่อมต่อบัญชีสำเร็จเรียบร้อยแล้ว!*\n\n"
                f"สวัสดีคุณ *{user.username}* ยินดีต้อนรับสู่ **Personal Life OS** ⚡\n\n"
                f"พ่อบ้านจะคอยดูแลเตือนบิลล่วงหน้า 1 วันทุกเช้าเวลา *10:00 น.* ตรงเข้าห้องแชตนี้ครับ\n\n"
                f"• พิมพ์ /status เพื่อดูสรุปภาระการเงินเดือนนี้\n"
                f"• พิมพ์ /help เพื่อดูวิธีใช้งานเพิ่มเติม"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        else:
            text = (
                "❌ *โทเค็นไม่ถูกต้องหรือหมดอายุแล้ว*\n\n"
                "กรุณาเปิดหน้าเว็บ Personal Life OS แล้วกดปุ่ม *[ เชื่อมต่อ Telegram Bot ]* เพื่อรับลิงก์ใหม่อีกครั้งครับ"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
            return

    # กรณีไม่มี Token: เช็คว่า Chat ID นี้ผูกกับใครไว้แล้วหรือยัง
    user = await get_user_by_chat_id(chat_id)
    if user:
        text = (
            f"👋 *สวัสดีคุณ {user.username}!*\n\n"
            f"บัญชี Telegram ของคุณเชื่อมต่อกับ Personal Life OS เรียบร้อยแล้ว\n\n"
            f"• พิมพ์ /status เพื่อดูสรุปภาพรวมการเงิน\n"
            f"• พิมพ์ /help เพื่อดูคำสั่งทั้งหมด"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        text = (
            "⚠️ *ยังไม่ได้เชื่อมต่อบัญชี*\n\n"
            "ห้องแชตนี้ยังไม่ได้ผูกกับบัญชีผู้ใช้ใน Personal Life OS\n\n"
            "👉 *วิธีเชื่อมต่อ:*\n"
            "1. เข้าสู่ระบบหน้าเว็บ Life OS\n"
            "2. กดปุ่ม *[ เชื่อมต่อ Telegram ]* ที่มุมบนขวา\n"
            "3. ระบบจะเปิดแชตนี้พร้อมโทเค็นให้คุณกดเริ่มใช้งานอัตโนมัติครับ"
        )
        await update.message.reply_text(text, parse_mode='Markdown')


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler สำหรับคำสั่ง /status เช็คยอด Burn Rate และภาระเดือนนี้"""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("⚠️ บัญชีนี้ยังไม่ได้เชื่อมต่อ กรุณากดเชื่อมต่อจากหน้าเว็บก่อนครับ")
        return

    overview = await get_user_overview_summary(user)
    burn_rate = float(overview.get('confirmed_burn_rate', 0))
    risk_amount = float(overview.get('potential_risk_amount', 0))
    trials_count = overview.get('active_trials_count', 0)
    upcoming_count = overview.get('upcoming_7_days_count', 0)
    month_name = overview.get('target_month', '')

    text = (
        f"📊 *สรุปสถานะการเงินเดือนนี้ ({month_name})*\n"
        f"👤 ผู้ใช้: *{user.username}*\n\n"
        f"• 💸 *Monthly Burn Rate:* ฿{burn_rate:,.2f}\n"
        f"  _(ภาระคงที่ที่ต้องเตรียมจ่ายเดือนนี้)_\n\n"
        f"• 🚨 *Free Trial Risk:* ฿{risk_amount:,.2f} ({trials_count} รายการ)\n"
        f"  _(ยอดที่จะโดนตัดถ้าลืมกดยกเลิก)_\n\n"
        f"• ⏰ *บิลใน 7 วันข้างหน้า:* {upcoming_count} รายการ\n"
    )

    if upcoming_count > 0:
        text += "\n*รายการที่ใกล้ถึงกำหนด:*\n"
        for item in overview.get('upcoming_7_days', [])[:5]:
            text += f"  - {item['title']}: ฿{float(item['amount']):,.2f} (อีก {item['days_left']} วัน)\n"

    await update.message.reply_text(text, parse_mode='Markdown')


async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler สำหรับคำสั่ง /portfolio เช็คสรุปภาพรวมพอร์ตและผลตอบแทน"""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("⚠️ บัญชีนี้ยังไม่ได้เชื่อมต่อ กรุณากดเชื่อมต่อจากหน้าเว็บก่อนครับ")
        return

    overview = await get_user_portfolio_summary(user)
    market_val = float(overview.get('total_market_value', 0))
    invested = float(overview.get('total_cost_basis', 0))
    unrealized = float(overview.get('total_unrealized_pnl', 0))
    unrealized_pct = float(overview.get('total_unrealized_pnl_pct', 0))
    realized = float(overview.get('total_realized_pnl', 0))
    dividends = float(overview.get('total_dividends', 0))
    holdings = overview.get('holdings', [])

    pnl_sign = "+" if unrealized >= 0 else ""
    pnl_icon = "🟢" if unrealized >= 0 else "🔴"

    text = (
        f"📈 *สรุปภาพรวมพอร์ตการลงทุน*\n"
        f"👤 บัญชี: *{user.username}*\n\n"
        f"• 💰 *มูลค่าพอร์ต:* ฿{market_val:,.2f}\n"
        f"• 📊 *เงินลงทุนสุทธิ:* ฿{invested:,.2f}\n"
        f"• {pnl_icon} *กำไร/ขาดทุน (Unrealized):* {pnl_sign}฿{unrealized:,.2f} ({pnl_sign}{unrealized_pct:.2f}%)\n"
        f"• 💵 *กำไรจริงสะสม (Realized PnL):* ฿{realized:,.2f}\n"
        f"• 🎁 *เงินปันผลรับสะสม:* ฿{dividends:,.2f}\n"
    )

    active_holdings = [h for h in holdings if h['position']['is_active']]
    if active_holdings:
        text += f"\n*สินทรัพย์ที่ถือครอง ({len(active_holdings)} ตัว):*\n"
        for h in active_holdings[:8]:
            pos = h['position']
            item_pnl = float(pos['unrealized_pnl'])
            item_sign = "+" if item_pnl >= 0 else ""
            item_icon = "🟢" if item_pnl >= 0 else "🔴"
            text += (
                f"  - *{h['ticker']}*: {float(pos['shares']):,.2f} หุ้น @ ฿{float(pos['current_price']):,.2f} "
                f"({item_icon} {item_sign}฿{item_pnl:,.2f})\n"
            )
    else:
        text += "\n_(ยังไม่มีรายการสินทรัพย์ที่ถือครอง พิมพ์เพิ่มผ่านหน้าเว็บ Portfolio ได้เลยครับ)_"

    await update.message.reply_text(text, parse_mode='Markdown')


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler สำหรับคำสั่ง /help"""
    if not update.message:
        return

    text = (
        "🤖 *พ่อบ้าน Life OS — คำสั่งที่ใช้งานได้:*\n\n"
        "• /brief — สรุปภาพรวมเช้า Executive Morning Briefing\n"
        "• /status — ดูสรุปภาพรวม Monthly Burn Rate และบิลเดือนนี้\n"
        "• /portfolio — ดูสรุปพอร์ตหุ้น สินทรัพย์ และผลตอบแทน PnL\n"
        "• /news [หุ้น] — ดูข่าวด่วนสินทรัพย์ล่าสุดแปลไทย (เช่น /news NVDA)\n"
        "• /help — ดูคู่มือการใช้งาน\n\n"
        "⏰ *ระบบแจ้งเตือนอัตโนมัติ:*\n"
        "• 08:30 น. — ส่ง Morning Executive Briefing สรุปภารกิจและข่าวหุ้น\n"
        "• 10:00 น. — ส่งข้อความเตือนบิลและเอกสารที่จะครบกำหนดวันพรุ่งนี้"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


async def brief_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler สำหรับคำสั่ง /brief เรียกดู Morning Executive Briefing ทันที"""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ บัญชีนี้ยังไม่ได้เชื่อมต่อ กรุณากดเชื่อมต่อจากหน้าเว็บก่อนครับ")
        return

    from apps.bot.dispatcher import send_morning_briefing
    await send_morning_briefing(context.bot, str(chat_id), user)


async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler สำหรับคำสั่ง /news หรือ /news <TICKER> ดูข่าวหุ้นแปลไทย"""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ บัญชีนี้ยังไม่ได้เชื่อมต่อ กรุณากดเชื่อมต่อจากหน้าเว็บก่อนครับ")
        return

    from apps.portfolio.models import StockNewsArticle, StockHolding
    from apps.portfolio.services import normalize_ticker

    args = context.args
    target_ticker = None
    if args and len(args) > 0:
        target_ticker = normalize_ticker(args[0].strip())

    @sync_to_async
    def get_news(ticker=None):
        qs = StockNewsArticle.objects.all()
        if ticker:
            qs = qs.filter(ticker__iexact=ticker)
        else:
            held = StockHolding.objects.filter(user=user).values_list('ticker', flat=True)
            qs = qs.filter(ticker__in=held)
        return list(qs.order_by('-published_at')[:4])

    articles = await get_news(target_ticker)
    if not articles:
        msg = f"ไม่พบข่าวสำหรับ {target_ticker}" if target_ticker else "ยังไม่มีข่าวล่าสุดสำหรับหุ้นในพอร์ตของคุณ (สามารถกด Refresh ได้จากหน้าเว็บ Portfolio)"
        await update.message.reply_text(f"📰 {msg}")
        return

    lines = [f"📰 *สรุปข่าวสารสินทรัพย์ล่าสุด (แปลไทย)*:"]
    for a in articles:
        headline = a.title_th or a.title
        sent_icon = "🟢" if a.sentiment == 'BULLISH' else ("🔴" if a.sentiment == 'BEARISH' else "⚪")
        lines.append(f"\n{sent_icon} *[{a.ticker}]* [{a.source}]\n*{headline}*")
        if a.summary_th:
            lines.append(f"_{a.summary_th}_")
        if a.url:
            lines.append(f"[🔗 อ่านข่าวต้นฉบับ]({a.url})")

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown', disable_web_page_preview=True)
