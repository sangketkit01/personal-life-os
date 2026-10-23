from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationType
from apps.finance.strategies import ObligationStrategyFactory

User = get_user_model()


@sync_to_async
def process_pay_callback(obligation_id: str, chat_id: int):
    """Safely process [Pay] button click from Telegram"""
    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'User account not found or bot not connected.'}

    try:
        obligation = FinancialObligation.objects.get(id=obligation_id, user=user)
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'Obligation not found or access denied.'}

    strategy = ObligationStrategyFactory.get_strategy(obligation.type)
    summary = strategy.on_paid(obligation, note='Settled via Telegram Bot action button')
    obligation.refresh_from_db()

    return {
        'success': True,
        'title': obligation.title,
        'type': obligation.type,
        'status': obligation.status,
        'summary': summary,
        'next_due': obligation.due_date.strftime('%d/%m/%Y') if obligation.due_date else None
    }


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

    task.status = TaskStatus.COMPLETED
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])

    return {
        'success': True,
        'title': task.title
    }


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
                    f"Item: *{result['title']}*\n"
                    f"• Term: *{result['summary']['current_term']}/{result['summary']['total_terms']}*\n"
                    f"• Remaining Balance: ฿{result['summary']['remaining_balance']:,.2f}\n"
                )
                if result['status'] == 'COMPLETED':
                    new_text += "\n🎉 *Congratulations! All installments have been completed.*"
                elif result['next_due']:
                    new_text += f"• Next Due Date: *{result['next_due']}*"
            else:
                new_text = f"✅ *Payment Recorded Successfully!*\nItem: *{result['title']}*"

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
                f"Item: *{result['title']}*\n"
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
            new_text = (
                f"✅ *Task Document Marked Completed!*\n"
                f"Task: *{result['title']}*\n"
                f"Status: `COMPLETED` 🎉"
            )
            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")
