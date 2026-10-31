from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.finance.services import get_financial_overview
from apps.portfolio.services import get_portfolio_overview
from apps.bot.i18n import bot_msg, currency_symbol
from apps.bot.markdown_utils import escape_md

User = get_user_model()


async def _send_typing(context, chat_id):
    """Show the typing indicator while data loads (never raises - safe under
    unit-test mocks that have no real bot behind the context)."""
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    except Exception:
        pass


@sync_to_async
def pair_user_by_token(token: str, chat_id: int):
    """Pair Telegram Chat ID with User using one-time token (valid for 15 minutes)."""
    from datetime import timedelta
    from django.db import transaction
    from django.utils import timezone
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(telegram_connect_token=token, is_active=True)
            if user.updated_at and (timezone.now() - user.updated_at) > timedelta(minutes=15):
                user.telegram_connect_token = None
                user.save(update_fields=['telegram_connect_token', 'updated_at'])
                return None

            # Clear any previous owner of this chat id first so the unique
            # constraint can never raise IntegrityError on re-pairing.
            User.objects.filter(telegram_chat_id=str(chat_id)).exclude(id=user.id).update(telegram_chat_id=None)

            user.telegram_chat_id = str(chat_id)
            user.telegram_connect_token = None
            user.save(update_fields=['telegram_chat_id', 'telegram_connect_token', 'updated_at'])
            return user
    except User.DoesNotExist:
        return None


@sync_to_async
def get_user_by_chat_id(chat_id: int):
    """Find User by Telegram Chat ID."""
    return User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()


@sync_to_async
def get_user_overview_summary(user):
    """Retrieve financial summary for user."""
    return get_financial_overview(user)


@sync_to_async
def get_user_portfolio_summary(user):
    """Retrieve portfolio summary for user."""
    return get_portfolio_overview(user)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start and /start <TOKEN> commands."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    args = context.args

    # If token provided, e.g. /start TOKEN_1234
    if args and len(args) > 0:
        connect_token = args[0].strip()
        user = await pair_user_by_token(connect_token, chat_id)

        if user:
            text = bot_msg(user, 'start.connected', username=escape_md(user.username))
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        else:
            # No user object yet -> catalog defaults to English.
            text = bot_msg(None, 'start.invalid_token')
            await update.message.reply_text(text, parse_mode='Markdown')
            return

    # If no token: check if chat ID is already paired
    user = await get_user_by_chat_id(chat_id)
    if user:
        text = bot_msg(user, 'start.already_connected', username=escape_md(user.username))
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        text = bot_msg(None, 'start.unpaired')
        await update.message.reply_text(text, parse_mode='Markdown')


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /status command to check burn rate and active obligations."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text(bot_msg(None, 'common.not_connected'))
        return

    await _send_typing(context, chat_id)
    overview = await get_user_overview_summary(user)
    burn_rate = float(overview.get('confirmed_burn_rate', 0))
    risk_amount = float(overview.get('potential_risk_amount', 0))
    trials_count = overview.get('active_trials_count', 0)
    upcoming_count = overview.get('upcoming_7_days_count', 0)
    month_name = overview.get('target_month', '')

    text = (
        f"{bot_msg(user, 'status.title', month=month_name)}\n"
        f"{bot_msg(user, 'status.user', username=escape_md(user.username))}\n\n"
        f"{bot_msg(user, 'status.burn_rate', value=f'{burn_rate:,.2f}')}\n"
        f"{bot_msg(user, 'status.burn_rate_sub')}\n\n"
        f"{bot_msg(user, 'status.trial_risk', value=f'{risk_amount:,.2f}', count=trials_count)}\n"
        f"{bot_msg(user, 'status.trial_risk_sub')}\n\n"
        f"{bot_msg(user, 'status.due_7d', count=upcoming_count)}\n"
    )

    if upcoming_count > 0:
        text += f"\n{bot_msg(user, 'status.upcoming_header')}\n"
        for item in overview.get('upcoming_7_days', [])[:5]:
            when = (
                bot_msg(user, 'status.due_today')
                if item.get('days_left', 0) <= 0
                else bot_msg(user, 'status.due_in_days', n=item['days_left'])
            )
            text += (
                f"  - {escape_md(item['title'])}: "
                f"{escape_md(__import__('apps.bot.dispatcher', fromlist=['billing_amount_text']).billing_amount_text(item))} ({when})\n"
            )

    if overview.get('has_pending_dynamic'):
        text += '\n⚠️ ยังมียอด Dynamic ที่รอกรอก; ยอดข้างต้นยังไม่ใช่ยอดทั้งหมด'
    await update.message.reply_text(text, parse_mode='Markdown')


async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /portfolio command to check investment portfolio overview."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text(bot_msg(None, 'common.not_connected'))
        return

    await _send_typing(context, chat_id)
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
        f"{bot_msg(user, 'portfolio.title')}\n"
        f"{bot_msg(user, 'portfolio.account', username=escape_md(user.username))}\n\n"
        f"{bot_msg(user, 'portfolio.value', value=f'{market_val:,.2f}')}\n"
        f"{bot_msg(user, 'portfolio.invested', value=f'{invested:,.2f}')}\n"
        f"{bot_msg(user, 'portfolio.unrealized', icon=pnl_icon, sign=pnl_sign, value=f'{unrealized:,.2f}', pct=f'{unrealized_pct:.2f}')}\n"
        f"{bot_msg(user, 'portfolio.realized', value=f'{realized:,.2f}')}\n"
        f"{bot_msg(user, 'portfolio.dividends', value=f'{dividends:,.2f}')}\n"
    )

    active_holdings = [h for h in holdings if h['position']['is_active']]
    if active_holdings:
        text += f"\n{bot_msg(user, 'portfolio.holdings', count=len(active_holdings))}\n"
        for h in active_holdings[:8]:
            pos = h['position']
            item_pnl = float(pos['unrealized_pnl'])
            item_sign = "+" if item_pnl >= 0 else ""
            item_icon = "🟢" if item_pnl >= 0 else "🔴"
            text += bot_msg(
                user, 'portfolio.holding_line',
                ticker=escape_md(h['ticker']),
                currency=currency_symbol(pos.get('currency') or h.get('currency')),
                shares=f"{float(pos['shares']):,.2f}",
                price=f"{float(pos['current_price']):,.2f}",
                icon=item_icon, sign=item_sign, pnl=f"{item_pnl:,.2f}"
            ) + "\n"
    else:
        text += f"\n{bot_msg(user, 'portfolio.empty')}"

    stamps = [h.get('position', {}).get('quote', {}).get('as_of') for h in active_holdings]
    stamps = [x for x in stamps if x]
    if stamps:
        text += '\nPrice as of: ' + escape_md(min(stamps))
    sync = overview.get('quote_sync', {})
    if sync.get('stale_count', 0) or sync.get('missing_count', 0) or (active_holdings and not stamps):
        text += '\nPrice data is stale, incomplete, or has no verified timestamp.'
    await update.message.reply_text(text, parse_mode='Markdown')


@sync_to_async
def get_user_servers(user):
    """List infrastructure assets with the latest telemetry snapshot."""
    from apps.workspace.models import InfrastructureAsset
    return list(InfrastructureAsset.objects.filter(user=user).order_by('name'))


@sync_to_async
def get_user_ma_contracts(user):
    """List MA contracts (MA-typed projects or any project with an MA fee)."""
    from django.db.models import Q
    from apps.workspace.models import WorkspaceProject, ProjectType
    return list(WorkspaceProject.objects.filter(
        user=user
    ).filter(
        Q(project_type=ProjectType.MA_CONTRACT) | Q(ma_amount__gt=0)
    ).order_by('ma_end_date'))


async def servers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /servers: list servers & infrastructure with live status."""
    if not update.effective_chat or not update.message:
        return

    user = await get_user_by_chat_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(bot_msg(None, 'common.not_connected'))
        return

    await _send_typing(context, update.effective_chat.id)
    assets = await get_user_servers(user)
    if not assets:
        await update.message.reply_text(bot_msg(user, 'servers.empty'))
        return

    status_icon = {'ONLINE': '🟢', 'WARNING': '🟡', 'OFFLINE': '🔴'}

    lines = [bot_msg(user, 'servers.title'), ""]
    keyboard = []
    for asset in assets[:12]:
        icon = status_icon.get(asset.health_status, '⚪')
        tel = asset.last_telemetry or {}
        lines.append(f"{icon} *{escape_md(asset.name)}* [{asset.asset_type}]")
        detail_parts = []
        if asset.ip_address:
            detail_parts.append(asset.ip_address)
        if tel.get('uptime_human'):
            detail_parts.append(f"up {tel['uptime_human']}")
        if tel.get('cpu_pct') is not None:
            detail_parts.append(f"CPU {tel['cpu_pct']}%")
        if tel.get('ram_pct') is not None:
            detail_parts.append(f"RAM {tel['ram_pct']}%")
        if not detail_parts:
            checked = asset.last_checked_at.strftime('%d/%m %H:%M') if asset.last_checked_at else None
            detail_parts.append(checked or bot_msg(user, 'servers.never'))
        lines.append(f"   {' · '.join(str(p) for p in detail_parts)}")
        keyboard.append([InlineKeyboardButton(
            f"{bot_msg(user, 'servers.refresh')} · {asset.name[:24]}",
            callback_data=f"probe_vps:{asset.id}"
        )])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def ma_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ma: list MA contracts, expiry and next billing."""
    if not update.effective_chat or not update.message:
        return

    user = await get_user_by_chat_id(update.effective_chat.id)
    if not user:
        await update.message.reply_text(bot_msg(None, 'common.not_connected'))
        return

    projects = await get_user_ma_contracts(user)
    if not projects:
        await update.message.reply_text(bot_msg(user, 'ma.empty'))
        return

    from django.utils import timezone as dj_tz

    lines = [bot_msg(user, 'ma.title'), ""]
    for p in projects[:10]:
        lines.append(f"• *{escape_md(p.name)}*")
        parts = []
        if p.client_name:
            parts.append(escape_md(p.client_name))
        if p.ma_end_date:
            days = (p.ma_end_date - dj_tz.localdate()).days
            if days < 0:
                parts.append(bot_msg(user, 'ma.expired', date=p.ma_end_date.strftime('%d/%m/%Y')))
            else:
                parts.append(bot_msg(user, 'ma.ends', date=p.ma_end_date.strftime('%d/%m/%Y'), days=days))
        if p.ma_next_billing_date:
            parts.append(bot_msg(user, 'ma.next_billing', date=p.ma_next_billing_date.strftime('%d/%m/%Y')))
        if p.ma_amount and float(p.ma_amount) > 0:
            parts.append(f"{currency_symbol(p.ma_currency)}{float(p.ma_amount):,.2f}/{p.ma_billing_cycle}")
        lines.append(f"   {' · '.join(parts)}")

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command, rendered in the user's preferred language."""
    if not update.message:
        return

    user = await get_user_by_chat_id(update.effective_chat.id) if update.effective_chat else None
    body = bot_msg(user, 'help.body').split('⏰')[0]
    if user:
        from apps.bot.delivery import preferences
        pref = await sync_to_async(preferences)(user)
        clock = pref.briefing_time.strftime('%H:%M')
        if getattr(user, 'preferred_language', 'en') == 'th':
            body += f'⏰ *การแจ้งเตือนอัตโนมัติ*\n• สรุปเช้า {clock} ({escape_md(pref.timezone)})\n• บิล งาน และรายการค้าง ตั้งแต่ 10:00 ตามเขตเวลาที่เลือก\n• สรุปพอร์ตหลังตลาดปิด SET/US และเตือนราคาที่ตั้งเอง\n• เลือกหมวด ช่วงเงียบ และเปิดปิดฟีเจอร์ได้ใน Settings → Telegram'
        else:
            body += f'⏰ *Automated notifications*\n• Briefing at {clock} ({escape_md(pref.timezone)})\n• Bills, tasks and overdue digests from 10:00 local time\n• SET/US market-close reports and your one-shot price rules\n• Configure categories, quiet hours and enabled features in Settings → Telegram'
    await update.message.reply_text(body, parse_mode='Markdown')


async def brief_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /brief command to trigger immediate Executive Morning Briefing."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text(bot_msg(None, 'common.not_connected'))
        return

    await _send_typing(context, chat_id)
    from apps.bot.dispatcher import send_morning_briefing
    await send_morning_briefing(context.bot, str(chat_id), user)


async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /news or /news <TICKER> command to view market news."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text(bot_msg(None, 'common.not_connected'))
        return

    from apps.portfolio.models import StockNewsArticle, StockHolding
    from apps.portfolio.services import normalize_ticker
    from apps.portfolio.identity import active_tickers, revalidate_stored_news

    args = context.args
    target_ticker = None
    if args and len(args) > 0:
        target_ticker = normalize_ticker(args[0].strip())

    await _send_typing(context, chat_id)
    @sync_to_async
    def get_news(ticker=None):
        revalidate_stored_news()
        qs = StockNewsArticle.objects.filter(relevance='ACCEPTED', published_at__gte=timezone.now()-timedelta(hours=48))
        if ticker:
            qs = qs.filter(ticker__iexact=ticker)
        else:
            held = active_tickers(user)
            qs = qs.filter(ticker__in=held)
        return list(qs.order_by('-published_at')[:4])

    articles = await get_news(target_ticker)
    if not articles:
        msg = (
            bot_msg(user, 'news.empty_ticker', ticker=target_ticker)
            if target_ticker else bot_msg(user, 'news.empty_portfolio')
        )
        await update.message.reply_text(f"📰 {msg}")
        return

    is_th = getattr(user, 'preferred_language', 'en') == 'th'
    lines = [bot_msg(user, 'news.title')]
    from apps.bot.message_chunks import split_plain_text, pack_blocks
    for a in articles:
        headline = (a.title_th or a.title) if is_th else (a.title or a.title_th)
        summary_text = (a.summary_th or a.summary) if is_th else (a.summary or a.summary_th)
        sent_icon = "🟢" if a.sentiment == 'BULLISH' else ("🔴" if a.sentiment == 'BEARISH' else "⚪")
        lines.append(f"\n{sent_icon} *[{escape_md(a.ticker)}]* [{escape_md(a.source)}]\n*{escape_md(headline)}*")
        if summary_text:
            lines.extend(f"_{escape_md(part)}_" for part in split_plain_text(summary_text))
        if a.url:
            lines.append(f"[{bot_msg(user, 'news.read_more')}]({a.url})")

    for text in pack_blocks(lines):
        await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)
