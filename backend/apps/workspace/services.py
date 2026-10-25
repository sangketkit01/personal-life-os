from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, List
from django.db.models import Count, Q, Sum
from django.utils import timezone
from .models import (
    WorkspaceProject,
    TaskDocument,
    TaskStatus,
    Note,
    ProjectType,
    InfrastructureAsset,
    BillingOwnership,
    ServerCredential,
    ServerRunbook
)

# Billing cycles that map to a recurring Financial Radar obligation.
RECURRING_CYCLES = {'MONTHLY', 'QUARTERLY', 'YEARLY', 'WEEKLY'}


def _normalize_monthly(amount: Decimal, cycle: str) -> Decimal:
    """Normalize a per-cycle amount into its monthly equivalent."""
    amount = Decimal(str(amount or 0))
    cycle = str(cycle or 'MONTHLY').upper()
    if cycle == 'YEARLY':
        return (amount / Decimal('12.0')).quantize(Decimal('0.01'))
    if cycle == 'QUARTERLY':
        return (amount / Decimal('3.0')).quantize(Decimal('0.01'))
    if cycle == 'WEEKLY':
        return (amount * Decimal('4.3333')).quantize(Decimal('0.01'))
    return amount


def _normalize_annual(amount: Decimal, cycle: str) -> Decimal:
    """Normalize a per-cycle amount into its annualized total."""
    amount = Decimal(str(amount or 0))
    cycle = str(cycle or 'MONTHLY').upper()
    if cycle == 'YEARLY':
        return amount
    if cycle == 'QUARTERLY':
        return (amount * Decimal('4.0')).quantize(Decimal('0.01'))
    if cycle == 'WEEKLY':
        return (amount * Decimal('52.0')).quantize(Decimal('0.01'))
    return (amount * Decimal('12.0')).quantize(Decimal('0.01'))


def sync_project_ma_obligation(project: WorkspaceProject):
    """
    Create or update the Financial Radar obligation mirroring the project's
    MA contract (recurring INFLOW). Deactivates the linked obligation when
    the MA configuration no longer qualifies for syncing.
    """
    from apps.finance.models import FinancialObligation, ObligationType, FlowDirection, ObligationStatus

    qualifies = (
        project.ma_next_billing_date is not None
        and Decimal(str(project.ma_amount or 0)) > 0
        and str(project.ma_billing_cycle or 'MONTHLY').upper() in RECURRING_CYCLES
    )

    if not qualifies:
        if project.ma_obligation_id:
            FinancialObligation.objects.filter(
                id=project.ma_obligation_id, user=project.user
            ).exclude(status=ObligationStatus.COMPLETED).update(status=ObligationStatus.CANCELLED)
            project.ma_obligation = None
            project.save(update_fields=['ma_obligation', 'updated_at'])
        return None

    base_metadata = {
        'billing_cycle': str(project.ma_billing_cycle).upper(),
        'source_type': 'MA_CONTRACT',
        'project_id': str(project.id),
        'client_name': project.client_name,
        'plan_name': f"Maintenance Agreement - {project.client_name or project.name}",
        'notes': 'Auto-synced from Workspace MA contract'
    }

    obligation = project.ma_obligation
    if obligation is None:
        obligation = FinancialObligation.objects.create(
            user=project.user,
            title=f"MA: {project.name}",
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.INFLOW,
            amount=project.ma_amount,
            currency=project.ma_currency or 'THB',
            due_date=project.ma_next_billing_date,
            project=project,
            metadata=base_metadata
        )
        project.ma_obligation = obligation
        project.save(update_fields=['ma_obligation', 'updated_at'])
    else:
        obligation.title = f"MA: {project.name}"
        obligation.amount = project.ma_amount
        obligation.currency = project.ma_currency or 'THB'
        obligation.due_date = project.ma_next_billing_date
        obligation.project = project
        if obligation.status == ObligationStatus.CANCELLED:
            obligation.status = ObligationStatus.ACTIVE
        meta = dict(obligation.metadata or {})
        meta.update(base_metadata)
        obligation.metadata = meta
        obligation.save()
    return obligation


def sync_infra_asset_obligation(asset: InfrastructureAsset):
    """
    Create or update the Financial Radar obligation mirroring the infra asset
    cost (recurring OUTFLOW) when 'sync_to_radar' is enabled and the user
    actually pays the bill themselves. Deactivates the linked obligation
    otherwise.
    """
    from apps.finance.models import FinancialObligation, ObligationType, FlowDirection, ObligationStatus

    qualifies = (
        asset.sync_to_radar
        and asset.next_billing_date is not None
        and Decimal(str(asset.cost_amount or 0)) > 0
        and asset.billing_ownership != BillingOwnership.CLIENT_DIRECT
        and str(asset.billing_cycle or 'MONTHLY').upper() in RECURRING_CYCLES
    )

    if not qualifies:
        if asset.financial_obligation_id:
            FinancialObligation.objects.filter(
                id=asset.financial_obligation_id, user=asset.user
            ).exclude(status=ObligationStatus.COMPLETED).update(status=ObligationStatus.CANCELLED)
            asset.financial_obligation = None
            asset.save(update_fields=['financial_obligation', 'updated_at'])
        return None

    provider_label = f" ({asset.provider})" if asset.provider else ''
    base_metadata = {
        'billing_cycle': str(asset.billing_cycle).upper(),
        'source_type': 'INFRA_ASSET',
        'asset_id': str(asset.id),
        'project_id': str(asset.project_id),
        'plan_name': f"Infrastructure - {asset.name}",
        'notes': 'Auto-synced from Infrastructure Asset'
    }

    obligation = asset.financial_obligation
    if obligation is None:
        obligation = FinancialObligation.objects.create(
            user=asset.user,
            title=f"Infra: {asset.name}{provider_label}",
            type=ObligationType.SUBSCRIPTION,
            direction=FlowDirection.OUTFLOW,
            amount=asset.cost_amount,
            currency=asset.cost_currency or 'THB',
            due_date=asset.next_billing_date,
            project=asset.project,
            metadata=base_metadata
        )
        asset.financial_obligation = obligation
        asset.save(update_fields=['financial_obligation', 'updated_at'])
    else:
        obligation.title = f"Infra: {asset.name}{provider_label}"
        obligation.amount = asset.cost_amount
        obligation.currency = asset.cost_currency or 'THB'
        obligation.due_date = asset.next_billing_date
        obligation.project = asset.project
        if obligation.status == ObligationStatus.CANCELLED:
            obligation.status = ObligationStatus.ACTIVE
        meta = dict(obligation.metadata or {})
        meta.update(base_metadata)
        obligation.metadata = meta
        obligation.save()
    return obligation


def sync_billing_dates_from_obligation(obligation) -> None:
    """
    After an obligation payment rolls its due_date forward, mirror the new
    date back onto the linked WorkspaceProject (MA) and/or InfrastructureAsset
    so both surfaces always agree on the next billing date.
    """
    from apps.finance.models import FlowDirection

    meta = obligation.metadata or {}
    new_due = obligation.due_date
    if new_due is None:
        return

    source_type = str(meta.get('source_type', '')).upper()

    if source_type == 'MA_CONTRACT' or (
        obligation.direction == FlowDirection.INFLOW and obligation.project_id
    ):
        WorkspaceProject.objects.filter(
            Q(ma_obligation=obligation) | Q(id=obligation.project_id),
            user=obligation.user
        ).exclude(ma_next_billing_date=new_due).update(ma_next_billing_date=new_due)

    if source_type == 'INFRA_ASSET':
        asset_q = Q(financial_obligation=obligation)
        asset_id = meta.get('asset_id')
        if asset_id:
            asset_q |= Q(id=asset_id)
        InfrastructureAsset.objects.filter(asset_q, user=obligation.user).exclude(
            next_billing_date=new_due
        ).update(next_billing_date=new_due)


def get_project_economics(project: WorkspaceProject) -> Dict[str, Any]:
    """
    Compute MA revenue vs self-funded infrastructure cost economics for a
    project, blending recurring projections with realized payment history.
    """
    from apps.finance.models import FlowDirection, ObligationStatus

    zero = Decimal('0.00')

    # --- Projected MA / client revenue (recurring INFLOW) ---
    ma_cycle = str(project.ma_billing_cycle or 'MONTHLY').upper()
    ma_amount = Decimal(str(project.ma_amount or 0))
    # Any project with a recurring MA fee counts as revenue, not only
    # projects explicitly typed MA_CONTRACT (CLIENT_DEV / INTERNAL too).
    if (project.project_type == ProjectType.MA_CONTRACT or ma_amount > 0) and ma_cycle in RECURRING_CYCLES:
        monthly_inflow = _normalize_monthly(ma_amount, ma_cycle)
        annual_inflow = _normalize_annual(ma_amount, ma_cycle)
    else:
        monthly_inflow = zero
        annual_inflow = zero

    # --- Projected infrastructure cost (self-funded OUTFLOW only) ---
    assets = list(project.infrastructure_assets.filter(
        billing_ownership=BillingOwnership.SELF_FUNDED
    ))
    monthly_outflow = zero
    annual_outflow = zero
    for asset in assets:
        cycle = str(asset.billing_cycle or 'MONTHLY').upper()
        if cycle not in RECURRING_CYCLES:
            continue
        cost = Decimal(str(asset.cost_amount or 0))
        monthly_outflow += _normalize_monthly(cost, cycle)
        annual_outflow += _normalize_annual(cost, cycle)

    # --- Realized cash movements via PaymentHistory on linked obligations ---
    obligation_ids = list(project.financial_obligations.exclude(
        status=ObligationStatus.CANCELLED
    ).values_list('id', flat=True))

    asset_obligation_ids = [
        a.financial_obligation_id for a in assets if a.financial_obligation_id
    ]
    all_obligation_ids = list(set(obligation_ids + asset_obligation_ids))

    realized_inflow = zero
    realized_outflow = zero
    if all_obligation_ids:
        from apps.finance.models import PaymentHistory
        inflow_ids = list(project.financial_obligations.filter(
            direction=FlowDirection.INFLOW
        ).values_list('id', flat=True))
        outflow_ids = [
            oid for oid in all_obligation_ids if oid not in set(inflow_ids)
        ]
        if inflow_ids:
            realized_inflow = Decimal(str(
                PaymentHistory.objects.filter(obligation_id__in=inflow_ids).aggregate(
                    total=Sum('paid_amount')
                )['total'] or 0
            )).quantize(Decimal('0.01'))
        if outflow_ids:
            realized_outflow = Decimal(str(
                PaymentHistory.objects.filter(obligation_id__in=outflow_ids).aggregate(
                    total=Sum('paid_amount')
                )['total'] or 0
            )).quantize(Decimal('0.01'))

    projected_monthly_margin = (monthly_inflow - monthly_outflow).quantize(Decimal('0.01'))
    realized_net_margin = (realized_inflow - realized_outflow).quantize(Decimal('0.01'))
    if realized_inflow > 0:
        margin_pct = (realized_net_margin / realized_inflow * Decimal('100')).quantize(Decimal('0.01'))
    elif monthly_inflow > 0:
        # No payments received yet - project the margin from the recurring plan.
        margin_pct = (projected_monthly_margin / monthly_inflow * Decimal('100')).quantize(Decimal('0.01'))
    else:
        margin_pct = zero

    return {
        'currency': project.ma_currency or 'THB',
        'monthly_ma_inflow': str(monthly_inflow),
        'annual_ma_inflow': str(annual_inflow),
        'realized_inflow': str(realized_inflow),
        'monthly_infra_outflow': str(monthly_outflow),
        'annual_infra_outflow': str(annual_outflow),
        'realized_outflow': str(realized_outflow),
        'projected_monthly_margin': str(projected_monthly_margin),
        'realized_net_margin': str(realized_net_margin),
        'margin_pct': str(margin_pct),
        'self_funded_asset_count': len(assets)
    }


def calculate_deadline_info(deadline) -> Dict[str, Any]:
    """Calculate remaining time and urgency indicator for a deadline."""
    if not deadline:
        return {
            'days_left': None,
            'urgency': 'NONE',
            'is_overdue': False,
            'label': 'No deadline'
        }

    now = timezone.now()
    today = timezone.localdate()
    deadline_date = timezone.localtime(deadline).date()

    days_diff = (deadline_date - today).days

    if deadline < now:
        return {
            'days_left': days_diff,
            'urgency': 'OVERDUE',
            'is_overdue': True,
            'label': 'Overdue'
        }
    elif days_diff == 0:
        return {
            'days_left': 0,
            'urgency': 'CRITICAL',
            'is_overdue': False,
            'label': 'Due Today'
        }
    elif days_diff == 1:
        return {
            'days_left': 1,
            'urgency': 'WARNING',
            'is_overdue': False,
            'label': 'Due Tomorrow'
        }
    elif days_diff <= 3:
        return {
            'days_left': days_diff,
            'urgency': 'ATTENTION',
            'is_overdue': False,
            'label': f'{days_diff} days left'
        }
    else:
        return {
            'days_left': days_diff,
            'urgency': 'NORMAL',
            'is_overdue': False,
            'label': f'{days_diff} days left'
        }


def normalize_task_status(status_str: str) -> str:
    """Normalize legacy pipeline status strings to the modern Kanban statuses."""
    if not status_str:
        return status_str
    normalized = str(status_str).upper().strip()
    from .models import LEGACY_STATUS_MAP
    if normalized in LEGACY_STATUS_MAP:
        return str(LEGACY_STATUS_MAP[normalized])
    return normalized


def transition_task_status(task: TaskDocument, new_status: str) -> TaskDocument:
    """Transition task/document status and automatically update completed_at timestamp."""
    new_status = normalize_task_status(new_status)
    if new_status not in TaskStatus.values:
        raise ValueError(f"Invalid task status: {new_status}")

    task.status = new_status
    if new_status == TaskStatus.DONE:
        task.completed_at = timezone.now()
    else:
        # Reset completed_at if moved back to an active status
        task.completed_at = None

    task.save()
    return task


def get_workspace_overview(user, project_id: str = None) -> Dict[str, Any]:
    """Retrieve workspace summary and active pipelines for user."""
    tasks_qs = TaskDocument.objects.filter(user=user)
    if project_id:
        tasks_qs = tasks_qs.filter(project_id=project_id)

    # Status counts
    todo_count = tasks_qs.filter(status=TaskStatus.TODO).count()
    doing_count = tasks_qs.filter(status=TaskStatus.DOING).count()
    done_count = tasks_qs.filter(status=TaskStatus.DONE).count()
    archived_count = tasks_qs.filter(status=TaskStatus.ARCHIVED).count()

    now = timezone.now()
    next_7_days = now + timedelta(days=7)

    # Active tasks (To Do or Doing)
    active_tasks = tasks_qs.filter(status__in=[TaskStatus.TODO, TaskStatus.DOING])

    # Overdue tasks
    overdue_count = active_tasks.filter(deadline__lt=now).count()

    # Upcoming tasks in 7 days (select_related avoids N+1)
    upcoming_tasks = active_tasks.filter(
        deadline__gte=now,
        deadline__lte=next_7_days
    ).select_related('project').order_by('deadline')

    upcoming_list = []
    for t in upcoming_tasks[:5]:
        dl_info = calculate_deadline_info(t.deadline)
        upcoming_list.append({
            'id': str(t.id),
            'title': t.title,
            'doc_number': t.doc_number,
            'project_name': t.project.name if t.project else None,
            'project_color': t.project.color if t.project else None,
            'status': t.status,
            'priority': t.priority,
            'deadline': t.deadline.isoformat(),
            'file_url': t.file_url,
            'deadline_info': dl_info
        })

    # Pinned notes (select_related avoids N+1)
    pinned_notes = Note.objects.filter(user=user, is_pinned=True, is_trashed=False).select_related('project').order_by('-updated_at')[:5]
    pinned_notes_list = [
        {
            'id': str(n.id),
            'title': n.title,
            'project_name': n.project.name if n.project else None,
            'tags': n.tags,
            'updated_at': n.updated_at.isoformat()
        }
        for n in pinned_notes
    ]

    # Projects annotated with task / note / link / attachment counts (Single query avoiding N+1)
    projects = WorkspaceProject.objects.filter(user=user, is_archived=False).annotate(
        todo_count=Count('documents', filter=Q(documents__status=TaskStatus.TODO)),
        doing_count=Count('documents', filter=Q(documents__status=TaskStatus.DOING)),
        done_count=Count('documents', filter=Q(documents__status=TaskStatus.DONE)),
        total_tasks_count=Count('documents', filter=Q(documents__status__in=[TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE])),
        pending_tasks_count=Count(
            'documents',
            filter=Q(documents__status__in=[TaskStatus.TODO, TaskStatus.DOING])
        ),
        notes_count=Count('notes', filter=Q(notes__is_trashed=False), distinct=True),
        links_count=Count('links', distinct=True),
        attachments_count=Count('attachments', distinct=True)
    )
    project_list = [
        {
            'id': str(p.id),
            'name': p.name,
            'color': p.color,
            'icon': p.icon,
            'todo_count': p.todo_count,
            'doing_count': p.doing_count,
            'done_count': p.done_count,
            'total_tasks_count': p.total_tasks_count,
            'pending_tasks_count': p.pending_tasks_count,
            'notes_count': p.notes_count,
            'links_count': p.links_count,
            'attachments_count': p.attachments_count
        }
        for p in projects
    ]

    return {
        'pipeline_counts': {
            'todo': todo_count,
            'doing': doing_count,
            'done': done_count,
            # Legacy keys kept for backward compatibility with existing clients/tests
            'drafting': todo_count,
            'waiting': doing_count,
            'completed': done_count,
            'archived': archived_count,
            'total_active': todo_count + doing_count
        },
        'overdue_count': overdue_count,
        'upcoming_deadlines_count': len(upcoming_list),
        'upcoming_deadlines': upcoming_list,
        'pinned_notes': pinned_notes_list,
        'projects': project_list
    }
