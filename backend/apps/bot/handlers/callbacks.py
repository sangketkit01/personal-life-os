from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationType, ObligationStatus, PaymentHistory
from apps.finance.strategies import ObligationStrategyFactory
from apps.bot.i18n import bot_msg, currency_symbol
from apps.bot.markdown_utils import escape_md

User = get_user_model()


@sync_to_async
def process_pay_callback(obligation_id: str, chat_id: int, target_cycle_key: str = None):
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

    clean_ob_id = str(obligation_id).strip()
    if not target_cycle_key and ':' in clean_ob_id:
        parts = clean_ob_id.split(':', 1)
        clean_ob_id = parts[0]
        target_cycle_key = parts[1]

    try:
        with transaction.atomic():
            obligation = FinancialObligation.objects.select_for_update().get(
                id=clean_ob_id, user=user
            )

            # Check if obligation is cancelled or completed
            meta = obligation.metadata or {}
            termination = meta.get('termination') or {}
            is_term = (termination.get('status') == 'TERMINATED')
            has_unpaid = termination.get('has_unpaid_final_bill', False)

            if obligation.status in (ObligationStatus.CANCELLED, ObligationStatus.COMPLETED):
                if not (obligation.type == 'SUBSCRIPTION' and is_term and has_unpaid):
                    return {
                        'success': False,
                        'message': 'รายการนี้ถูกยกเลิกหรือเสร็จสิ้นแล้ว'
                    }

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
            if obligation.type == ObligationType.SUBSCRIPTION or obligation.type == 'SUBSCRIPTION':
                if meta.get('current_cycle', {}).get('status') in ('PAID', 'COMPLETED'):
                    return {
                        'success': False,
                        'message': 'บิลรอบนี้ชำระเรียบร้อยแล้ว'
                    }

                sub_summary = strategy.get_summary(obligation)
                if sub_summary.get('is_itemized') and sub_summary.get('pending_dynamic_count', 0) > 0:
                    return {
                        'success': False,
                        'message': 'บิลนี้มีรายการที่ต้องกรอกยอดก่อนชำระ กรุณากรอกยอดและชำระผ่านเว็บแอป'
                    }

                expected_ck = strategy.get_cycle_key(obligation.due_date, meta.get('billing_cycle', 'MONTHLY')) if obligation.due_date else None
                if not target_cycle_key:
                    return {
                        'success': False,
                        'message': 'ไม่พบข้อมูลรอบบิล กรุณาชำระผ่านเว็บแอป'
                    }
                if expected_ck and target_cycle_key != expected_ck:
                    return {
                        'success': False,
                        'message': 'บิลรอบนี้ชำระเรียบร้อยแล้ว'
                    }
                if PaymentHistory.objects.filter(obligation=obligation, metadata__cycle_key=target_cycle_key).exists():
                    return {
                        'success': False,
                        'message': 'บิลรอบนี้ชำระเรียบร้อยแล้ว'
                    }

            summary = strategy.on_paid(
                obligation,
                cycle_key=target_cycle_key,
                note='Settled via Telegram Bot action button'
            )
            obligation.refresh_from_db()

            next_due = obligation.due_date.strftime('%d/%m/%Y') if obligation.due_date else None
            if obligation.type == 'INSTALLMENT':
                remaining_disp = f"{currency_symbol(obligation.currency)}{float(summary.get('remaining_balance', 0)):,.2f}"
                new_text = bot_msg(
                    user, 'cb.pay.inst_recorded',
                    title=escape_md(obligation.title),
                    term=summary.get('current_term'),
                    total=summary.get('total_terms'),
                    remaining=remaining_disp
                )
                if obligation.status == 'COMPLETED':
                    new_text += bot_msg(user, 'cb.pay.completed')
                elif next_due:
                    new_text += bot_msg(user, 'cb.pay.next_due', date=next_due)
            else:
                new_text = bot_msg(user, 'cb.pay.recorded', title=escape_md(obligation.title))

            return {
                'success': True,
                'title': obligation.title,
                'type': obligation.type,
                'status': obligation.status,
                'summary': summary,
                'next_due': next_due,
                'new_text': new_text
            }
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'Obligation not found or access denied.'}


@sync_to_async
def process_cancel_trial_callback(obligation_id: str, chat_id: int):
    """Process [Cancel Trial] button click from Telegram (atomic + idempotent)."""
    from django.db import transaction

    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'User account not found.'}

    try:
        with transaction.atomic():
            obligation = FinancialObligation.objects.select_for_update().get(
                id=obligation_id, user=user
            )

            # Tapping the button on an already-cancelled trial must succeed
            # without running the cancellation logic a second time.
            if obligation.status == ObligationStatus.CANCELLED:
                return {
                    'success': True,
                    'title': obligation.title,
                    'already_cancelled': True,
                    'new_text': bot_msg(user, 'cb.cancel.recorded', title=escape_md(obligation.title))
                }

            if obligation.type != ObligationType.FREE_TRIAL:
                return {'success': False, 'message': 'This item is not a Free Trial.'}

            strategy = ObligationStrategyFactory.get_strategy(obligation.type)
            strategy.cancel(obligation)
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'Free Trial not found.'}

    return {
        'success': True,
        'title': obligation.title,
        'new_text': bot_msg(user, 'cb.cancel.recorded', title=escape_md(obligation.title))
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
        return {
            'success': True,
            'title': task.title,
            'already_done': True,
            'new_text': bot_msg(user, 'cb.task.done', title=escape_md(task.title), extra=bot_msg(user, 'cb.task.already_done'))
        }

    task.status = TaskStatus.DONE
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])

    return {
        'success': True,
        'title': task.title,
        'new_text': bot_msg(user, 'cb.task.done', title=escape_md(task.title), extra=bot_msg(user, 'cb.task.celebrate'))
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

    return {
        'success': True,
        'text': "\n".join(lines),
        'button_label': bot_msg(user, 'watchdog.probe_again')
    }


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle event when user clicks an inline keyboard button in Telegram"""
    query = update.callback_query
    if not query or not query.data or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    data = query.data

    # The VPS probe runs a full SSH round-trip - answer immediately so the
    # user feels the tap registered while it works (safe under test mocks).
    if data.startswith('probe_vps:'):
        try:
            await query.answer()
        except Exception:
            pass
    else:
        await query.answer()

    # 1. Action Pay / Settle Term
    if data.startswith('pay:'):
        parts = data.split(':', 2)
        ob_id = parts[1]
        target_ck = parts[2] if len(parts) > 2 else None
        result = await process_pay_callback(ob_id, chat_id, target_cycle_key=target_ck)

        if result['success']:
            await query.edit_message_text(result['new_text'], parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 2. Action Cancel Free Trial
    elif data.startswith('cancel_trial:'):
        ob_id = data.split(':')[1]
        result = await process_cancel_trial_callback(ob_id, chat_id)

        if result['success']:
            await query.edit_message_text(result['new_text'], parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 3. Action Complete Task Document
    elif data.startswith('done_task:'):
        task_id = data.split(':')[1]
        result = await process_done_task_callback(task_id, chat_id)

        if result['success']:
            await query.edit_message_text(result['new_text'], parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 4. Action Probe VPS (watchdog / servers refresh)
    elif data.startswith('probe_vps:'):
        asset_id = data.split(':')[1]
        result = await process_probe_vps_callback(asset_id, chat_id)

        if result['success']:
            await query.edit_message_text(
                result['text'],
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        result['button_label'],
                        callback_data=f"probe_vps:{asset_id}"
                    )
                ]])
            )
        else:
            await query.edit_message_text(f"❌ {result['message']}")
