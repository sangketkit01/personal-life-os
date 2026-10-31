import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import timedelta
import datetime
from django.db import transaction
from django.utils import timezone
from .base import BaseObligationStrategy


class SubscriptionStrategy(BaseObligationStrategy):
    """
    Strategy for recurring SaaS / Subscriptions (Netflix, iCloud, Spotify, ChatGPT, VPS)
    - Supports MONTHLY, YEARLY, QUARTERLY, and WEEKLY cycles
    - Supports Single Amount and Multi-Item Expense Breakdown (Fixed & Dynamic items)
    - Separates Subscription Plan (template) from Billing Cycle Bills (current_cycle)
    - Supports Subscription Termination Lifecycle (Immediate & Scheduled End Date)
    - Auto-rolls due_date forward upon payment recording (or marks COMPLETED if terminated)
    - Computes normalized monthly burn and annualized cost with disclaimers for pending dynamic items
    """

    @staticmethod
    def get_cycle_key(due_date, billing_cycle: str = 'MONTHLY') -> str:
        if not due_date:
            return 'CURRENT'
        cycle = str(billing_cycle or 'MONTHLY').upper()
        if cycle == 'YEARLY':
            return f"{due_date.year}"
        elif cycle == 'QUARTERLY':
            quarter = (due_date.month - 1) // 3 + 1
            return f"{due_date.year}-Q{quarter}"
        elif cycle == 'WEEKLY':
            iso = due_date.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        else:
            return f"{due_date.year}-{due_date.month:02d}"

    @staticmethod
    def sync_current_cycle(plan_items=None, existing_cycle: Optional[Dict[str, Any]] = None, due_date=None, billing_cycle: str = 'MONTHLY') -> Dict[str, Any]:
        """
        Synchronize current cycle bill with plan template items.
        - Matches existing draft items by persistent 'id' so user-entered dynamic amounts are preserved.
        - Advancing to a new cycle initializes Dynamic items as unfilled (None).
        - Fixed items always reflect plan template price.
        """
        if hasattr(plan_items, 'metadata'):
            obligation = plan_items
            meta = obligation.metadata or {}
            plan_items = meta.get('items') or meta.get('line_items') or []
            existing_cycle = meta.get('current_cycle')
            due_date = obligation.due_date
            billing_cycle = meta.get('billing_cycle', 'MONTHLY')

        cycle_key = SubscriptionStrategy.get_cycle_key(due_date, billing_cycle)
        is_same_cycle = bool(existing_cycle and existing_cycle.get('cycle_key') == cycle_key)

        existing_items_map = {}
        if is_same_cycle and isinstance(existing_cycle.get('items'), list):
            for it in existing_cycle['items']:
                if isinstance(it, dict) and 'id' in it:
                    existing_items_map[str(it['id'])] = it

        cycle_items = []
        fixed_total = Decimal('0.00')
        dynamic_total = Decimal('0.00')
        has_dynamic_filled = False
        pending_dynamic_count = 0

        for item in (plan_items or []):
            item_id = str(item.get('id') or uuid.uuid4())
            name = str(item.get('name', '')).strip()
            item_type = str(item.get('type', 'FIXED')).upper()
            if item_type not in ('FIXED', 'DYNAMIC'):
                item_type = 'FIXED'

            if item_type == 'FIXED':
                try:
                    amt = Decimal(str(item.get('amount') or '0.00'))
                except Exception:
                    amt = Decimal('0.00')
                if amt < Decimal('0.00'):
                    amt = Decimal('0.00')
                fixed_total += amt
                cycle_items.append({
                    'id': item_id,
                    'name': name,
                    'type': 'FIXED',
                    'amount': float(amt)
                })
            else:
                # DYNAMIC
                existing_entry = existing_items_map.get(item_id) if is_same_cycle else None
                if existing_entry is not None and existing_entry.get('amount') is not None and str(existing_entry.get('amount')).strip() != '':
                    try:
                        amt = Decimal(str(existing_entry['amount']))
                        if amt < Decimal('0.00'):
                            amt = Decimal('0.00')
                        dynamic_total += amt
                        has_dynamic_filled = True
                        cycle_items.append({
                            'id': item_id,
                            'name': name,
                            'type': 'DYNAMIC',
                            'amount': float(amt)
                        })
                    except Exception:
                        pending_dynamic_count += 1
                        cycle_items.append({
                            'id': item_id,
                            'name': name,
                            'type': 'DYNAMIC',
                            'amount': None
                        })
                else:
                    pending_dynamic_count += 1
                    cycle_items.append({
                        'id': item_id,
                        'name': name,
                        'type': 'DYNAMIC',
                        'amount': None
                    })

        is_complete = (pending_dynamic_count == 0)
        total_amount = (fixed_total + dynamic_total) if is_complete else None
        status = existing_cycle.get('status', 'DRAFT') if is_same_cycle else 'DRAFT'

        return {
            'cycle_key': cycle_key,
            'due_date': due_date.isoformat() if hasattr(due_date, 'isoformat') else (str(due_date) if due_date else None),
            'items': cycle_items,
            'status': status,
            'is_complete': is_complete,
            'pending_dynamic_count': pending_dynamic_count,
            'fixed_total': float(fixed_total),
            'dynamic_total': float(dynamic_total) if is_complete else None,
            'total_amount': float(total_amount) if is_complete else None
        }

    @staticmethod
    def update_cycle_draft(current_cycle: Dict[str, Any], items_update: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update dynamic amounts in current cycle draft without finalizing payment."""
        if not current_cycle or 'items' not in current_cycle:
            return current_cycle

        update_map = {}
        for it in (items_update or []):
            if isinstance(it, dict) and 'id' in it:
                update_map[str(it['id'])] = it.get('amount')

        updated_items = []
        fixed_total = Decimal('0.00')
        dynamic_total = Decimal('0.00')
        pending_dynamic_count = 0

        for it in current_cycle.get('items', []):
            item_id = str(it.get('id', ''))
            item_type = str(it.get('type', 'FIXED')).upper()
            name = it.get('name', '')

            if item_type == 'FIXED':
                try:
                    amt = Decimal(str(it.get('amount') or '0.00'))
                except Exception:
                    amt = Decimal('0.00')
                fixed_total += amt
                updated_items.append({
                    'id': item_id,
                    'name': name,
                    'type': 'FIXED',
                    'amount': float(amt)
                })
            else:
                # Dynamic item
                if item_id in update_map:
                    raw_val = update_map[item_id]
                    if raw_val is None or str(raw_val).strip() == '':
                        val = None
                    else:
                        str_val = str(raw_val).strip().lower()
                        if str_val in ('inf', '-inf', '+inf', 'infinity', '-infinity', '+infinity', 'nan'):
                            raise ValueError(f"Invalid monetary amount '{raw_val}'.")
                        try:
                            val = Decimal(str(raw_val))
                        except Exception:
                            raise ValueError(f"Invalid monetary amount '{raw_val}'.")
                        if not val.is_finite():
                            raise ValueError(f"Invalid monetary amount '{raw_val}'.")
                        if val < Decimal('0.00'):
                            raise ValueError(f"Dynamic item amount cannot be negative ({val}).")
                        if val.as_tuple().exponent < -2:
                            raise ValueError(f"Amount {val} cannot have more than 2 decimal places.")
                        val = val.quantize(Decimal('0.01'))
                else:
                    raw_val = it.get('amount')
                    if raw_val is not None and str(raw_val).strip() != '':
                        str_val = str(raw_val).strip().lower()
                        if str_val in ('inf', '-inf', '+inf', 'infinity', '-infinity', '+infinity', 'nan'):
                            val = None
                        else:
                            try:
                                val = Decimal(str(raw_val))
                                if not val.is_finite() or val < Decimal('0.00') or val.as_tuple().exponent < -2:
                                    val = None
                                else:
                                    val = val.quantize(Decimal('0.01'))
                            except Exception:
                                val = None
                    else:
                        val = None

                if val is not None:
                    dynamic_total += val
                    updated_items.append({
                        'id': item_id,
                        'name': name,
                        'type': 'DYNAMIC',
                        'amount': float(val)
                    })
                else:
                    pending_dynamic_count += 1
                    updated_items.append({
                        'id': item_id,
                        'name': name,
                        'type': 'DYNAMIC',
                        'amount': None
                    })

        is_complete = (pending_dynamic_count == 0)
        total_amount = (fixed_total + dynamic_total) if is_complete else None

        current_cycle['items'] = updated_items
        current_cycle['is_complete'] = is_complete
        current_cycle['pending_dynamic_count'] = pending_dynamic_count
        current_cycle['fixed_total'] = float(fixed_total)
        current_cycle['dynamic_total'] = float(dynamic_total) if is_complete else None
        current_cycle['total_amount'] = float(total_amount) if is_complete else None
        return current_cycle

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        cycle = str(metadata.get('billing_cycle', 'MONTHLY')).upper()
        if cycle not in ['MONTHLY', 'YEARLY', 'QUARTERLY', 'WEEKLY']:
            cycle = 'MONTHLY'

        try:
            alert_days = int(metadata.get('alert_days_before', 3))
        except (ValueError, TypeError):
            alert_days = 3

        validated = {
            'billing_cycle': cycle,
            'plan_name': str(metadata.get('plan_name', '')).strip(),
            'account_email': str(metadata.get('account_email', '')).strip(),
            'payment_method': str(metadata.get('payment_method', '')).strip(),
            'category': str(metadata.get('category', 'GENERAL')).strip().upper(),
            'cancel_url': str(metadata.get('cancel_url', '')).strip(),
            'cancel_steps': str(metadata.get('cancel_steps', '')).strip(),
            'alert_days_before': alert_days,
            'documents': metadata.get('documents', []) if isinstance(metadata.get('documents'), list) else [],
            'notes': str(metadata.get('notes', '')).strip()
        }

        # Itemized expense breakdown validation
        is_itemized = bool(metadata.get('is_itemized', False))
        validated['is_itemized'] = is_itemized

        if is_itemized:
            raw_items = metadata.get('items')
            if raw_items is None:
                raw_items = metadata.get('line_items', [])
            if not isinstance(raw_items, list) or len(raw_items) == 0:
                raise ValueError("Itemized subscription requires at least one expense line item.")

            validated_items = []
            for idx, raw_item in enumerate(raw_items):
                if not isinstance(raw_item, dict):
                    continue
                name = str(raw_item.get('name', '')).strip()
                if not name:
                    raise ValueError(f"Line item #{idx+1} must have a non-empty name.")
                item_type = str(raw_item.get('type', 'FIXED')).strip().upper()
                if item_type not in ('FIXED', 'DYNAMIC'):
                    item_type = 'FIXED'

                item_id = str(raw_item.get('id') or '').strip()
                if not item_id:
                    item_id = str(uuid.uuid4())

                if item_type == 'FIXED':
                    raw_amt = raw_item.get('amount')
                    if raw_amt is None or str(raw_amt).strip() == '':
                        raise ValueError(f"Line item '{name}' requires an amount (cannot be left blank).")

                    str_amt = str(raw_amt).strip().lower()
                    if str_amt in ('inf', '-inf', '+inf', 'infinity', '-infinity', '+infinity', 'nan'):
                        raise ValueError(f"Line item '{name}' has invalid amount '{raw_amt}'.")
                    try:
                        amt = Decimal(str(raw_amt))
                    except Exception:
                        raise ValueError(f"Line item '{name}' has invalid fixed amount.")

                    if not amt.is_finite():
                        raise ValueError(f"Line item '{name}' has invalid amount '{raw_amt}'.")
                    if amt < Decimal('0.00'):
                        raise ValueError(f"Line item '{name}' amount cannot be negative.")
                    if amt.as_tuple().exponent < -2:
                        raise ValueError(f"Line item '{name}' amount cannot have more than 2 decimal places.")
                    amt = amt.quantize(Decimal('0.01'))

                    validated_items.append({
                        'id': item_id,
                        'name': name,
                        'type': 'FIXED',
                        'amount': float(amt)
                    })
                else:
                    validated_items.append({
                        'id': item_id,
                        'name': name,
                        'type': 'DYNAMIC',
                        'amount': None
                    })

            if len(validated_items) == 0:
                raise ValueError("Itemized subscription requires at least one expense line item.")

            validated['items'] = validated_items
            validated['line_items'] = validated_items

            # Preserve/sync current_cycle draft if provided or previously stored
            existing_cycle = metadata.get('current_cycle')
            due_date = metadata.get('due_date')
            validated['current_cycle'] = self.sync_current_cycle(
                validated_items,
                existing_cycle,
                due_date,
                cycle
            )
        else:
            validated['items'] = []

        # Termination lifecycle metadata preservation
        termination = metadata.get('termination')
        if isinstance(termination, dict) and termination.get('status') == 'TERMINATED':
            mode = str(termination.get('mode', 'IMMEDIATE')).upper()
            if mode not in ('IMMEDIATE', 'SCHEDULED'):
                mode = 'IMMEDIATE'
            validated['termination'] = {
                'status': 'TERMINATED',
                'mode': mode,
                'effective_end_date': str(termination.get('effective_end_date', '')).strip() or None,
                'terminated_at': str(termination.get('terminated_at', '')).strip() or timezone.now().isoformat(),
                'has_unpaid_final_bill': bool(termination.get('has_unpaid_final_bill', False))
            }

        # Preserve workspace bridge keys (MA contracts / infrastructure assets)
        source_type = str(metadata.get('source_type', '')).strip().upper()
        if source_type in ('INFRA_ASSET', 'MA_CONTRACT'):
            validated['source_type'] = source_type
            for aux_key in ('asset_id', 'project_id'):
                aux_val = str(metadata.get(aux_key, '')).strip()
                if aux_val:
                    validated[aux_key] = aux_val
            client_name = str(metadata.get('client_name', '')).strip()
            if client_name:
                validated['client_name'] = client_name

        return validated

    def get_summary(self, obligation) -> Dict[str, Any]:
        metadata = obligation.metadata or {}
        billing_cycle = metadata.get('billing_cycle', 'MONTHLY').upper()
        is_itemized = bool(metadata.get('is_itemized', False))
        items = metadata.get('items') or metadata.get('line_items') or []

        termination = metadata.get('termination') or {}
        is_terminated = (termination.get('status') == 'TERMINATED')
        termination_mode = termination.get('mode', 'IMMEDIATE')
        has_unpaid_final_bill = termination.get('has_unpaid_final_bill', False)

        current_cycle = None
        is_pure_dynamic = False
        pending_dynamic_count = 0
        is_bill_complete = True
        burn_disclaimer = None
        fixed_total = Decimal('0.00')
        total_bill_amount = None

        if is_itemized:
            fixed_items = [it for it in items if it.get('type') == 'FIXED']
            dynamic_items = [it for it in items if it.get('type') == 'DYNAMIC']
            is_pure_dynamic = (len(fixed_items) == 0 and len(dynamic_items) > 0)

            # Sync current cycle with obligation due date
            existing_cycle = metadata.get('current_cycle')
            current_cycle = self.sync_current_cycle(
                items,
                existing_cycle,
                obligation.due_date,
                billing_cycle
            )
            fixed_total = Decimal(str(current_cycle.get('fixed_total', '0.00')))
            pending_dynamic_count = current_cycle.get('pending_dynamic_count', 0)
            is_bill_complete = current_cycle.get('is_complete', False)

            if is_bill_complete and current_cycle.get('total_amount') is not None:
                total_bill_amount = Decimal(str(current_cycle['total_amount']))

            # Base amount for burn computation:
            # - If bill is complete, use exact total bill amount
            # - If dynamic items are pending, use fixed_total (or None if pure dynamic)
            if is_pure_dynamic and pending_dynamic_count > 0:
                base_burn_amount = None
                burn_disclaimer = f"ไม่ทราบยอด (มี {pending_dynamic_count} รายการที่ต้องกรอกยอดแต่ละรอบ)"
            elif pending_dynamic_count > 0:
                base_burn_amount = fixed_total
                burn_disclaimer = f"ยอดคาดการณ์คิดจากส่วนคงที่ ฿{fixed_total:,.2f} (ยังไม่รวม {pending_dynamic_count} รายการที่รอกรอก)"
            else:
                base_burn_amount = total_bill_amount if total_bill_amount is not None else fixed_total
        else:
            base_burn_amount = Decimal(str(obligation.amount or '0.00'))

        # Calculate normalized monthly equivalent and annualized burn
        if base_burn_amount is not None:
            if billing_cycle == 'YEARLY':
                monthly_equivalent = (base_burn_amount / Decimal('12.0')).quantize(Decimal('0.01'))
                annual_burn = base_burn_amount
            elif billing_cycle == 'QUARTERLY':
                monthly_equivalent = (base_burn_amount / Decimal('3.0')).quantize(Decimal('0.01'))
                annual_burn = (base_burn_amount * Decimal('4.0')).quantize(Decimal('0.01'))
            elif billing_cycle == 'WEEKLY':
                monthly_equivalent = (base_burn_amount * Decimal('4.3333')).quantize(Decimal('0.01'))
                annual_burn = (base_burn_amount * Decimal('52.0')).quantize(Decimal('0.01'))
            else:
                monthly_equivalent = base_burn_amount
                annual_burn = (base_burn_amount * Decimal('12.0')).quantize(Decimal('0.01'))
        else:
            # Pure dynamic and incomplete
            monthly_equivalent = None
            annual_burn = None

        days_until_renewal = None
        urgency = 'SAFE'
        if obligation.due_date:
            today = timezone.localdate()
            days_until_renewal = (obligation.due_date - today).days
            if days_until_renewal < 0:
                urgency = 'EXPIRED'
            elif days_until_renewal <= 1:
                urgency = 'CRITICAL'
            elif days_until_renewal <= metadata.get('alert_days_before', 3):
                urgency = 'WARNING'
            else:
                urgency = 'SAFE'

        # Status label logic for termination
        termination_label = None
        if is_terminated:
            if has_unpaid_final_bill or obligation.status == 'ACTIVE':
                termination_label = "สิ้นสุดแล้ว · มีบิลค้าง"
            else:
                termination_label = "สิ้นสุดแล้ว"

        return {
            'billing_cycle': billing_cycle,
            'is_yearly': billing_cycle == 'YEARLY',
            'plan_name': metadata.get('plan_name', ''),
            'account_email': metadata.get('account_email', ''),
            'payment_method': metadata.get('payment_method', ''),
            'category': metadata.get('category', 'GENERAL'),
            'cancel_url': metadata.get('cancel_url', ''),
            'cancel_steps': metadata.get('cancel_steps', ''),
            'alert_days_before': metadata.get('alert_days_before', 3),
            'amount_per_period': base_burn_amount,
            'monthly_equivalent': monthly_equivalent,
            'annual_burn': annual_burn,
            'days_until_renewal': days_until_renewal,
            'days_left': days_until_renewal,
            'urgency': urgency,
            'documents': metadata.get('documents', []),
            # Itemized breakdown fields
            'cycle_key': self.get_cycle_key(obligation.due_date, billing_cycle),
            'is_itemized': is_itemized,
            'items': items,
            'current_cycle': current_cycle,
            'is_pure_dynamic': is_pure_dynamic,
            'pending_dynamic_count': pending_dynamic_count,
            'is_bill_complete': is_bill_complete,
            'is_complete': is_bill_complete,
            'fixed_total': fixed_total,
            'dynamic_total': current_cycle.get('dynamic_total') if current_cycle else None,
            'total_bill_amount': total_bill_amount,
            'burn_disclaimer': burn_disclaimer,
            # Termination lifecycle fields
            'is_terminated': is_terminated,
            'termination': termination if is_terminated else None,
            'termination_mode': termination_mode if is_terminated else None,
            'has_unpaid_final_bill': has_unpaid_final_bill if is_terminated else False,
            'termination_label': termination_label
        }

    def terminate(self, obligation, mode: str = 'IMMEDIATE', effective_end_date: str = None) -> Dict[str, Any]:
        """
        Terminate subscription lifecycle.
        - IMMEDIATE: Stops future cycles immediately. Unpaid current cycle remains accessible as final bill.
        - SCHEDULED: Runs until effective_end_date, then ceases renewals.
        """
        meta = obligation.metadata or {}
        mode = str(mode or 'IMMEDIATE').strip().upper()
        if mode not in ('IMMEDIATE', 'SCHEDULED'):
            mode = 'IMMEDIATE'

        today = timezone.localdate()
        parsed_end_date = None
        if effective_end_date:
            try:
                parsed_end_date = datetime.date.fromisoformat(str(effective_end_date).strip())
            except (ValueError, TypeError):
                parsed_end_date = None

        if mode == 'SCHEDULED' and not parsed_end_date:
            raise ValueError("Effective end date is required for scheduled termination.")

        from apps.finance.models import ObligationStatus, PaymentHistory

        billing_cycle = meta.get('billing_cycle', 'MONTHLY').upper()
        current_cycle_key = self.get_cycle_key(obligation.due_date, billing_cycle) if obligation.due_date else None

        has_unpaid_bill = False
        if mode == 'IMMEDIATE' or (parsed_end_date and parsed_end_date <= today):
            mode = 'IMMEDIATE'
            end_date_str = today.isoformat()

            # Check if current cycle has already been paid
            is_paid = False
            current_cycle = meta.get('current_cycle')
            if current_cycle and current_cycle.get('status') in ('PAID', 'COMPLETED'):
                is_paid = True
            elif current_cycle_key:
                is_paid = PaymentHistory.objects.filter(
                    obligation=obligation,
                    metadata__cycle_key=current_cycle_key
                ).exists()

            if is_paid:
                has_unpaid_bill = False
            else:
                # Cycle bill has not been paid. Determine if it is an existing active bill vs unaccrued future cycle.
                if obligation.due_date and obligation.due_date <= today:
                    has_unpaid_bill = True
                else:
                    # Due date is in future. Check if active billing period has started or has prepared items:
                    has_draft_items = False
                    is_itemized = meta.get('is_itemized', False)
                    if is_itemized and current_cycle:
                        has_draft_items = any(
                            it.get('amount') is not None and str(it.get('amount')).strip() != ''
                            for it in current_cycle.get('items', [])
                            if it.get('type') == 'DYNAMIC'
                        )

                    has_prior_payments = PaymentHistory.objects.filter(obligation=obligation).exists()

                    if has_draft_items:
                        has_unpaid_bill = True
                    elif not has_prior_payments:
                        # Initial cycle of subscription that hasn't been paid
                        has_unpaid_bill = True
                    else:
                        # Prior payment exists and next due date is in the future (> today) without drafted items.
                        # That future cycle has not accrued an unpaid bill.
                        has_unpaid_bill = False

            if not has_unpaid_bill:
                obligation.status = ObligationStatus.CANCELLED
            else:
                obligation.status = ObligationStatus.ACTIVE

            meta['termination'] = {
                'status': 'TERMINATED',
                'mode': 'IMMEDIATE',
                'effective_end_date': end_date_str,
                'terminated_at': timezone.now().isoformat(),
                'has_unpaid_final_bill': has_unpaid_bill
            }
        else:
            # Scheduled termination in the future (parsed_end_date > today)
            # If obligation.due_date is after parsed_end_date, the subscription terminates
            # BEFORE the due date arrives! No future bills should be accrued or paid.
            if obligation.due_date and obligation.due_date > parsed_end_date:
                has_unpaid_bill = False
                obligation.status = ObligationStatus.CANCELLED
            else:
                is_paid = False
                current_cycle = meta.get('current_cycle')
                if current_cycle and current_cycle.get('status') in ('PAID', 'COMPLETED'):
                    is_paid = True
                elif current_cycle_key:
                    is_paid = PaymentHistory.objects.filter(
                        obligation=obligation,
                        metadata__cycle_key=current_cycle_key
                    ).exists()
                has_unpaid_bill = not is_paid
                if not has_unpaid_bill:
                    # If current cycle is paid and next due date would be > parsed_end_date, cancel now
                    if billing_cycle == 'WEEKLY':
                        next_due = obligation.due_date + timedelta(days=7) if obligation.due_date else None
                    else:
                        m_add = 12 if billing_cycle == 'YEARLY' else (3 if billing_cycle == 'QUARTERLY' else 1)
                        next_due = self.calculate_next_due_date(obligation.due_date, billing_day=obligation.billing_day, months_to_add=m_add) if obligation.due_date else None
                    if next_due and next_due > parsed_end_date:
                        obligation.status = ObligationStatus.CANCELLED

            meta['termination'] = {
                'status': 'TERMINATED',
                'mode': 'SCHEDULED',
                'effective_end_date': parsed_end_date.isoformat(),
                'terminated_at': timezone.now().isoformat(),
                'has_unpaid_final_bill': has_unpaid_bill
            }

        obligation.metadata = meta
        obligation.save(update_fields=['metadata', 'status'])
        return self.get_summary(obligation)

    def on_paid(self, obligation, paid_amount: Decimal = None, term_number: int = None, note: str = '', cycle_items: List[Dict[str, Any]] = None, cycle_key: str = None, **kwargs) -> Dict[str, Any]:
        """
        Record subscription cycle payment.
        - Enforces completeness of dynamic line items if itemized.
        - Verifies backend calculated total against paid amount.
        - Records immutable snapshot of items and prices in PaymentHistory.metadata.
        - Advances cycle due date, OR terminates obligation without creating new cycle if terminated.
        - Supports 0.00 bill closure.
        """
        from apps.finance.models import PaymentHistory, ObligationStatus

        metadata = obligation.metadata or {}
        billing_cycle = metadata.get('billing_cycle', 'MONTHLY').upper()
        is_itemized = bool(metadata.get('is_itemized', False))

        termination = metadata.get('termination') or {}
        is_terminated = (termination.get('status') == 'TERMINATED')
        termination_mode = termination.get('mode', 'IMMEDIATE')

        # 0. Enforce active/final-bill lock check & scheduled end date
        if obligation.status in (ObligationStatus.COMPLETED, ObligationStatus.CANCELLED) and not (is_terminated and termination.get('has_unpaid_final_bill', False)):
            raise ValueError("This subscription is already completed or cancelled.")

        if is_terminated and termination.get('effective_end_date') and not termination.get('has_unpaid_final_bill', False):
            try:
                eff_end = datetime.date.fromisoformat(termination['effective_end_date'])
                if obligation.due_date and obligation.due_date > eff_end:
                    raise ValueError("This subscription has ended and no further billing cycles can be paid.")
            except (ValueError, TypeError):
                pass

        expected_cycle_key = self.get_cycle_key(obligation.due_date, billing_cycle) if obligation.due_date else None
        if cycle_key and expected_cycle_key and cycle_key != expected_cycle_key:
            raise ValueError("บิลรอบนี้ชำระเรียบร้อยแล้ว")

        # 1. Resolve and validate payment amount and line items
        if is_itemized:
            items = metadata.get('items') or metadata.get('line_items') or []
            current_cycle = metadata.get('current_cycle') or self.sync_current_cycle(
                items, None, obligation.due_date, billing_cycle
            )

            # Check if cycle draft is already marked paid
            if current_cycle.get('status') in ('PAID', 'COMPLETED'):
                raise ValueError("บิลรอบนี้ชำระเรียบร้อยแล้ว")

            # Apply any dynamic item updates passed along with the payment request
            if cycle_items:
                current_cycle = self.update_cycle_draft(current_cycle, cycle_items)
                metadata['current_cycle'] = current_cycle

            # Enforce dynamic completeness
            pending_count = current_cycle.get('pending_dynamic_count', 0)
            if pending_count > 0:
                raise ValueError(f"Cannot pay subscription bill: {pending_count} dynamic item(s) are pending amount.")

            expected_total = Decimal(str(current_cycle.get('total_amount', '0.00'))).quantize(Decimal('0.01'))
            if paid_amount is None:
                paid_amount = expected_total
            else:
                paid_amount = Decimal(str(paid_amount)).quantize(Decimal('0.01'))
                if paid_amount != expected_total:
                    raise ValueError(f"Full subscription payment of ฿{expected_total:,.2f} is required.")
        else:
            scheduled_amount = obligation.amount.quantize(Decimal('0.01'))
            if paid_amount is None:
                paid_amount = scheduled_amount
            else:
                paid_amount = Decimal(str(paid_amount)).quantize(Decimal('0.01'))
                if paid_amount != scheduled_amount:
                    raise ValueError(f"Full subscription payment of ฿{scheduled_amount:,.2f} is required.")

        with transaction.atomic():
            # 2. Record payment history with immutable cycle snapshot for audits & reversal
            hist_meta = {
                'prev_due_date': obligation.due_date.isoformat() if obligation.due_date else None,
                'is_itemized': is_itemized,
                'prev_status': obligation.status,
                'prev_termination': dict(termination) if termination else None,
                'cycle_key': expected_cycle_key
            }
            if is_itemized:
                hist_meta['cycle_key'] = current_cycle.get('cycle_key') or expected_cycle_key
                hist_meta['cycle_items'] = current_cycle.get('items', [])
                hist_meta['fixed_total'] = str(current_cycle.get('fixed_total', '0.00'))
                hist_meta['dynamic_total'] = str(current_cycle.get('dynamic_total', '0.00'))
                hist_meta['total_amount'] = str(paid_amount)
                hist_meta['prev_cycle'] = dict(current_cycle)

            payment = PaymentHistory.objects.create(
                user=obligation.user,
                obligation=obligation,
                paid_amount=paid_amount,
                note=note or f"Subscription payment ({billing_cycle})",
                metadata=hist_meta
            )

            # 3. Check Termination Lifecycle vs Cycle Advancement
            should_terminate_now = False
            base_due = obligation.due_date or timezone.localdate()

            if is_terminated:
                if termination_mode == 'IMMEDIATE':
                    should_terminate_now = True
                elif termination_mode == 'SCHEDULED':
                    effective_end_date_str = termination.get('effective_end_date')
                    if effective_end_date_str:
                        try:
                            effective_end_date = datetime.date.fromisoformat(effective_end_date_str)
                            # Check next potential due date
                            if billing_cycle == 'WEEKLY':
                                potential_next = base_due + timedelta(days=7)
                            else:
                                months_to_add = 12 if billing_cycle == 'YEARLY' else (3 if billing_cycle == 'QUARTERLY' else 1)
                                potential_next = self.calculate_next_due_date(
                                    base_due,
                                    billing_day=obligation.billing_day,
                                    months_to_add=months_to_add
                                )
                            if potential_next > effective_end_date:
                                should_terminate_now = True
                        except Exception:
                            should_terminate_now = True
                    else:
                        should_terminate_now = True

            if should_terminate_now:
                # Cease future cycles: mark as cancelled and clear pending final bill flag
                obligation.status = ObligationStatus.CANCELLED
                metadata['termination']['has_unpaid_final_bill'] = False
                if is_itemized:
                    current_cycle['status'] = 'PAID'
                    metadata['current_cycle'] = current_cycle
                obligation.metadata = metadata
                obligation.save(update_fields=['status', 'metadata'])
            else:
                # Regular cycle advancement
                if billing_cycle == 'WEEKLY':
                    obligation.due_date = base_due + timedelta(days=7)
                else:
                    months_to_add = 12 if billing_cycle == 'YEARLY' else (3 if billing_cycle == 'QUARTERLY' else 1)
                    obligation.due_date = self.calculate_next_due_date(
                        base_due,
                        billing_day=obligation.billing_day,
                        months_to_add=months_to_add
                    )

                # Initialize fresh cycle draft for the new due_date
                if is_itemized:
                    metadata['current_cycle'] = self.sync_current_cycle(
                        metadata.get('items') or metadata.get('line_items') or [],
                        None,  # Reset dynamic amounts to None for new cycle!
                        obligation.due_date,
                        billing_cycle
                    )
                obligation.metadata = metadata
                obligation.save(update_fields=['due_date', 'metadata'])

        summary = self.get_summary(obligation)
        summary['payment_id'] = str(payment.id)
        return summary
