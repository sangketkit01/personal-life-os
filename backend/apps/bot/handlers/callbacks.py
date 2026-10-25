from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationType, PaymentHistory
from apps.finance.strategies import ObligationStrategyFactory
from apps.bot.i18n import bot_msg
from apps.bot.markdown_utils import escape_md

User = get_user_model()


@sync_to_async
def process_pay_callback(obligation_id: str, chat_id: int):
    """Safely process [Pay] button click from Telegram.

    Locks the obligation row and refuses duplicate settlement for the same
    day, so clicking a button on an old message never double-pays.
    """
    from django.db import transaction
    from django.utils import timezone

    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'User account not found or bot not connected.'}

    try:
        with transaction.atomic():
            obligation = FinancialObligation.objects.select_for_update().get(
                id=obligation_id, user=user
            )

            already_paid_today = PaymentHistory.objects.filter(
                obligation=obligation,
                paid_at__date=timezone.localdate()
            ).exists()
            if already_paid_today:
                return {
                    'success': False,
                    'message': bot_msg(user, 'pay.already_settled'),
                    'duplicate': True
                }

            strategy = ObligationStrategyFactory.get_strategy(obligation.type)
            summary = strategy.on_paid(
                obligation,
                note='Settled via Telegram Bot action button'
            )
            obligation.refresh_from_db()

            return {
                'success': True,
                'title': obligation.title,
                'type': obligation.type,
                'status': obligation.status,
                'summary': summary,
                'next_due': obligation.due_date.strftime('%d/%m/%Y') if obligation.due_date else None
            }
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'Obligation not found or access denied.'}


@sync_to_async
def process_cancel_trial_callback(obligation_id: str, chat_id: int):
    """Process [Cancel Trial] button click from Telegram"""
    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'User account not found.'}

    try:
        obligation = FinancialObligation.objects.get(id=obligation_id, user=user)
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'Free Trial not found.'}

    if obligation.type != ObligationType.FREE_TRIAL:
        return {'success': False, 'message': 'This item is not a Free Trial.'}

    strategy = ObligationStrategyFactory.get_strategy(obligation.type)
    strategy.cancel(obligation)

    return {
        'success': True,
        'title': obligation.title
    }


@sync_to_async
def process_done_task_callback(task_id: str, chat_id: int):
    """Process [Mark Done] button click for task document from Telegram"""
    from apps.workspace.models import TaskDocument, TaskStatus
    from django.utils import timezone

    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'User account not found.'}

    try:
        task = TaskDocument.objects.get(id=task_id, user=user)
    except TaskDocument.DoesNotExist:
        return {'success': False, 'message': 'Task document not found.'}

    if task.status == TaskStatus.DONE:
        return {'success': True, 'title': task.title, 'already_done': True}

    task.status = TaskStatus.DONE
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])

    return {
        'success': True,
        'title': task.title
    }


@sync_to_async
def process_probe_vps_callback(asset_id: str, chat_id: int):
    """Process [Probe Again] button: re-probe the asset and report status."""
    from apps.workspace.models import InfrastructureAsset
    from apps.workspace.ssh_service import probe_server_telemetry

    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'User account not found.'}

    try:
        asset = InfrastructureAsset.objects.get(id=asset_id, user=user)
    except InfrastructureAsset.DoesNotExist:
        return {'success': False, 'message': 'Server not found or access denied.'}

    telemetry = probe_server_telemetry(asset)

    status_icon = {
        'ONLINE': '🟢', 'WARNING': '🟡', 'OFFLINE': '🔴'
    }.get(asset.health_status, '⚪')

    lines = [f"{status_icon} *{escape_md(asset.name)}*: {asset.health_status}"]
    if telemetry.get('error'):
        lines.append(f"• {bot_msg(user, 'watchdog.offline')}")
    if telemetry.get('uptime_human'):
        lines.append(f"• Uptime: {telemetry['uptime_human']}")
    if telemetry.get('cpu_pct') is not None:
        lines.append(f"• CPU: {telemetry['cpu_pct']}%")
    if telemetry.get('ram_pct') is not None:
        lines.append(
            f"• RAM: {telemetry['ram_pct']}% "
            f"({int(telemetry.get('ram_used_mb') or 0)}/{int(telemetry.get('ram_total_mb') or 0)} MB)"
        )
    if telemetry.get('disk_pct') is not None:
        lines.append(f"• Disk: {telemetry['disk_pct']}%")

    containers = telemetry.get('containers') or []
    if containers:
        running = sum(1 for c in containers if str(c.get('State', '')).lower() == 'running')
        lines.append(f"• Containers: {running}/{len(containers)} running")

    return {'success': True, 'text': "\n".join(lines)}


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle event when user clicks an inline keyboard button in Telegram"""
    query = update.callback_query
    if not query or not query.data or not update.effective_chat:
        return

    await query.answer()
    chat_id = update.effective_chat.id
    data = query.data

    # 1. Action Pay / Settle Term
    if data.startswith('pay:'):
        ob_id = data.split(':')[1]
        result = await process_pay_callback(ob_id, chat_id)

        if result['success']:
            if result['type'] == 'INSTALLMENT':
                new_text = (
                    f"✅ *Installment Payment Recorded!*\n"
                    f"Item: *{escape_md(result['title'])}*\n"
                    f"• Term: *{result['summary']['current_term']}/{result['summary']['total_terms']}*\n"
                    f"• Remaining Balance: ฿{result['summary']['remaining_balance']:,.2f}\n"
                )
                if result['status'] == 'COMPLETED':
                    new_text += "\n🎉 *Congratulations! All installments have been completed.*"
                elif result['next_due']:
                    new_text += f"• Next Due Date: *{result['next_due']}*"
            else:
                new_text = f"✅ *Payment Recorded Successfully!*\nItem: *{escape_md(result['title'])}*"

            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 2. Action Cancel Free Trial
    elif data.startswith('cancel_trial:'):
        ob_id = data.split(':')[1]
        result = await process_cancel_trial_callback(ob_id, chat_id)

        if result['success']:
            new_text = (
                f"✅ *Cancellation Recorded!*\n"
                f"Item: *{escape_md(result['title'])}*\n"
                f"Status updated to: `CANCELLED` (Will not be charged)"
            )
            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 3. Action Complete Task Document
    elif data.startswith('done_task:'):
        task_id = data.split(':')[1]
        result = await process_done_task_callback(task_id, chat_id)

        if result['success']:
            done_label = " (already completed)" if result.get('already_done') else " 🎉"
            new_text = (
                f"✅ *Task Marked Completed!*\n"
                f"Task: *{escape_md(result['title'])}*\n"
                f"Status: `DONE`{done_label}"
            )
            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 4. Action Probe VPS (watchdog / servers refresh)
    elif data.startswith('probe_vps:'):
        asset_id = data.split(':')[1]
        result = await process_probe_vps_callback(asset_id, chat_id)

        if result['success']:
            await query.edit_message_text(result['text'], parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")
