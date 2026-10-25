from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from apps.finance.services import get_financial_overview
from apps.portfolio.services import get_portfolio_overview
from apps.bot.i18n import bot_msg
from apps.bot.markdown_utils import escape_md

User = get_user_model()


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
            text = (
                f"🎉 *Account Connected Successfully!*\n\n"
                f"Hello *{user.username}*, welcome to **Personal Life OS** ⚡\n\n"
                f"Daily bill reminders will be delivered 1 day in advance at *10:00 AM* directly to this chat.\n\n"
                f"• Type /status to view this month's financial summary\n"
                f"• Type /help to view all available commands"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        else:
            text = (
                "❌ *Invalid or Expired Token*\n\n"
                "Please open the Personal Life OS web app and click *[ Connect Telegram Bot ]* to generate a fresh link."
            )
            await update.message.reply_text(text, parse_mode='Markdown')
            return

    # If no token: check if chat ID is already paired
    user = await get_user_by_chat_id(chat_id)
    if user:
        text = (
            f"👋 *Hello {user.username}!*\n\n"
            f"Your Telegram account is connected to Personal Life OS.\n\n"
            f"• Type /status to check your financial summary\n"
            f"• Type /help to see all available commands"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        text = (
            "⚠️ *Account Not Connected*\n\n"
            "This chat is not linked to any Personal Life OS account.\n\n"
            "👉 *How to connect:*\n"
            "1. Log in to the Life OS web app\n"
            "2. Click *[ Connect Telegram ]* in the top right header\n"
            "3. The bot will open with an automatic pairing token"
        )
        await update.message.reply_text(text, parse_mode='Markdown')


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /status command to check burn rate and active obligations."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("⚠️ This account is not connected. Please connect from the web app first.")
        return

    overview = await get_user_overview_summary(user)
    burn_rate = float(overview.get('confirmed_burn_rate', 0))
    risk_amount = float(overview.get('potential_risk_amount', 0))
    trials_count = overview.get('active_trials_count', 0)
    upcoming_count = overview.get('upcoming_7_days_count', 0)
    month_name = overview.get('target_month', '')

    text = (
        f"📊 *Financial Summary ({month_name})*\n"
        f"👤 User: *{user.username}*\n\n"
        f"• 💸 *Monthly Burn Rate:* ฿{burn_rate:,.2f}\n"
        f"  _(Fixed obligations due this month)_\n\n"
        f"• 🚨 *Free Trial Risk:* ฿{risk_amount:,.2f} ({trials_count} items)\n"
        f"  _(Potential charges if not cancelled)_\n\n"
        f"• ⏰ *Due in next 7 days:* {upcoming_count} obligations\n"
    )

    if upcoming_count > 0:
        text += "\n*Upcoming Obligations:*\n"
        for item in overview.get('upcoming_7_days', [])[:5]:
            text += f"  - {item['title']}: ฿{float(item['amount']):,.2f} (in {item['days_left']} days)\n"

    await update.message.reply_text(text, parse_mode='Markdown')


async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /portfolio command to check investment portfolio overview."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("⚠️ This account is not connected. Please connect from the web app first.")
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
        f"📈 *Portfolio Overview*\n"
        f"👤 Account: *{user.username}*\n\n"
        f"• 💰 *Portfolio Value:* ฿{market_val:,.2f}\n"
        f"• 📊 *Net Invested Capital:* ฿{invested:,.2f}\n"
        f"• {pnl_icon} *Unrealized PnL:* {pnl_sign}฿{unrealized:,.2f} ({pnl_sign}{unrealized_pct:.2f}%)\n"
        f"• 💵 *Realized PnL:* ฿{realized:,.2f}\n"
        f"• 🎁 *Total Dividends:* ฿{dividends:,.2f}\n"
    )

    active_holdings = [h for h in holdings if h['position']['is_active']]
    if active_holdings:
        text += f"\n*Holdings ({len(active_holdings)} assets):*\n"
        for h in active_holdings[:8]:
            pos = h['position']
            item_pnl = float(pos['unrealized_pnl'])
            item_sign = "+" if item_pnl >= 0 else ""
            item_icon = "🟢" if item_pnl >= 0 else "🔴"
            text += (
                f"  - *{h['ticker']}*: {float(pos['shares']):,.2f} shares @ ฿{float(pos['current_price']):,.2f} "
                f"({item_icon} {item_sign}฿{item_pnl:,.2f})\n"
            )
    else:
        text += "\n_(No active holdings found. You can add holdings via the Portfolio page)_"

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
        await update.message.reply_text("⚠️ This account is not connected. Please connect from the web app first.")
        return

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
        await update.message.reply_text("⚠️ This account is not connected. Please connect from the web app first.")
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
            parts.append(f"฿{float(p.ma_amount):,.2f}/{p.ma_billing_cycle}")
        lines.append(f"   {' · '.join(parts)}")

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command."""
    if not update.message:
        return

    text = (
        "🤖 *Life OS Assistant — Available Commands:*\n\n"
        "• /brief — Executive Morning Briefing summary\n"
        "• /status — Monthly Burn Rate & upcoming bills\n"
        "• /portfolio — Investment portfolio & PnL overview\n"
        "• /news [TICKER] — Latest market & asset news (e.g. /news NVDA)\n"
        "• /servers — Servers & infrastructure live status\n"
        "• /ma — MA contracts, expiry dates & next billing\n"
        "• /help — Show help manual\n\n"
        "⏰ *Automated Dispatches:*\n"
        "• 08:30 — Morning Executive Briefing (tasks & market overview)\n"
        "• 10:00 — Bill & document due reminders (1 day advance notice)"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


async def brief_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /brief command to trigger immediate Executive Morning Briefing."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ This account is not connected. Please connect from the web app first.")
        return

    from apps.bot.dispatcher import send_morning_briefing
    await send_morning_briefing(context.bot, str(chat_id), user)


async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /news or /news <TICKER> command to view market news."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text("⚠️ This account is not connected. Please connect from the web app first.")
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
        msg = f"No news found for {target_ticker}" if target_ticker else "No recent news for your portfolio holdings (you can sync news from the Portfolio page)."
        await update.message.reply_text(f"📰 {msg}")
        return

    lines = [f"📰 *Latest Asset News:*"]
    for a in articles:
        headline = a.title or a.title_th
        sent_icon = "🟢" if a.sentiment == 'BULLISH' else ("🔴" if a.sentiment == 'BEARISH' else "⚪")
        lines.append(f"\n{sent_icon} *[{a.ticker}]* [{a.source}]\n*{headline}*")
        if a.summary:
            lines.append(f"_{a.summary}_")
        elif a.summary_th:
            lines.append(f"_{a.summary_th}_")
        if a.url:
            lines.append(f"[🔗 Original Article]({a.url})")

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown', disable_web_page_preview=True)
