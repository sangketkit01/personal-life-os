from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from apps.finance.models import FinancialObligation, ObligationType
from apps.finance.strategies import ObligationStrategyFactory

User = get_user_model()


@sync_to_async
def process_pay_callback(obligation_id: str, chat_id: int):
    """ประมวลผลการกดปุ่ม [จ่ายแล้ว] จาก Telegram อย่างปลอดภัย"""
    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'ไม่พบบัญชีผู้ใช้ หรือยังไม่ได้ผูกบอท'}

    try:
        obligation = FinancialObligation.objects.get(id=obligation_id, user=user)
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'ไม่พบบิลนี้ หรือคุณไม่มีสิทธิ์เข้าถึง'}

    strategy = ObligationStrategyFactory.get_strategy(obligation.type)
    summary = strategy.on_paid(obligation, note='ชำระผ่านปุ่มกดใน Telegram Bot')
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
    """ประมวลผลการกดปุ่ม [กดยกเลิกแล้ว] สำหรับ Free Trial จาก Telegram"""
    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'ไม่พบบัญชีผู้ใช้'}

    try:
        obligation = FinancialObligation.objects.get(id=obligation_id, user=user)
    except FinancialObligation.DoesNotExist:
        return {'success': False, 'message': 'ไม่พบรายการ Free Trial นี้'}

    if obligation.type != ObligationType.FREE_TRIAL:
        return {'success': False, 'message': 'รายการนี้ไม่ใช่ Free Trial'}

    strategy = ObligationStrategyFactory.get_strategy(obligation.type)
    strategy.cancel(obligation)

    return {
        'success': True,
        'title': obligation.title
    }


@sync_to_async
def process_done_task_callback(task_id: str, chat_id: int):
    """ประมวลผลการกดปุ่ม [ทำเสร็จแล้ว] สำหรับงานเอกสารจาก Telegram"""
    from apps.workspace.models import TaskDocument, TaskStatus
    from django.utils import timezone

    try:
        user = User.objects.get(telegram_chat_id=str(chat_id), is_active=True)
    except User.DoesNotExist:
        return {'success': False, 'message': 'ไม่พบบัญชีผู้ใช้'}

    try:
        task = TaskDocument.objects.get(id=task_id, user=user)
    except TaskDocument.DoesNotExist:
        return {'success': False, 'message': 'ไม่พบงานเอกสารนี้'}

    task.status = TaskStatus.COMPLETED
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])

    return {
        'success': True,
        'title': task.title
    }


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """จัดการ Event เมื่อผู้ใช้คลิกปุ่ม Inline Button ในแชต Telegram"""
    query = update.callback_query
    if not query or not query.data or not update.effective_chat:
        return

    await query.answer()  # ปิด Loading spinner บนปุ่มใน Telegram
    chat_id = update.effective_chat.id
    data = query.data

    # 1. Action ชำระเงิน / ตัดงวด
    if data.startswith('pay:'):
        ob_id = data.split(':')[1]
        result = await process_pay_callback(ob_id, chat_id)

        if result['success']:
            if result['type'] == 'INSTALLMENT':
                new_text = (
                    f"✅ *ชำระค่างวดสำเร็จ!*\n"
                    f"รายการ: *{result['title']}*\n"
                    f"• ตัดงวดที่: *{result['summary']['current_term']}/{result['summary']['total_terms']}*\n"
                    f"• ยอดหนี้คงเหลือ: ฿{result['summary']['remaining_balance']:,.2f}\n"
                )
                if result['status'] == 'COMPLETED':
                    new_text += "\n🎉 *ยินดีด้วย! คุณผ่อนชำระครบทุกงวดแล้ว (ปิดหนี้เรียบร้อย)*"
                elif result['next_due']:
                    new_text += f"• วันครบกำหนดงวดถัดไป: *{result['next_due']}*"
            else:
                new_text = f"✅ *บันทึกการชำระเงินสำเร็จ!*\nรายการ: *{result['title']}*"

            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 2. Action กดยกเลิก Free Trial
    elif data.startswith('cancel_trial:'):
        ob_id = data.split(':')[1]
        result = await process_cancel_trial_callback(ob_id, chat_id)

        if result['success']:
            new_text = (
                f"✅ *บันทึกการยกเลิกเรียบร้อย!*\n"
                f"รายการ: *{result['title']}*\n"
                f"สถานะเปลี่ยนเป็น: `CANCELLED` (เก็บเป็นประวัติแล้ว ไม่โดนหักเงินแน่นอน)"
            )
            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")

    # 3. Action ทำงานเอกสารเสร็จสิ้น
    elif data.startswith('done_task:'):
        task_id = data.split(':')[1]
        result = await process_done_task_callback(task_id, chat_id)

        if result['success']:
            new_text = (
                f"✅ *บันทึกสถานะงานเอกสารเสร็จสิ้นเรียบร้อย!*\n"
                f"ชื่องาน: *{result['title']}*\n"
                f"สถานะเปลี่ยนเป็น: `COMPLETED` 🎉"
            )
            await query.edit_message_text(new_text, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ {result['message']}")
