"""Resolve storage destinations and live references without calling Google Drive."""
import uuid
from urllib.parse import urlparse, parse_qs

DOMAIN_NAMES = {
    'ledger': 'Ledger', 'finance': 'Finance', 'portfolio': 'Portfolio',
    'workspace': 'Workspace', 'note': 'Notes', 'general': 'General',
}
CATEGORY_FOLDERS = {
    'CONTRACT': 'Contracts', 'SLIP': 'Payments', 'STATEMENT': 'Statements',
    'SCREENSHOT': 'Screenshots', 'DOCUMENT': 'Documents', 'OTHER': 'Documents',
}


def file_ids(value):
    result = set()
    if isinstance(value, dict):
        if value.get('drive_file_id'):
            result.add(str(value['drive_file_id']))
        for child in value.values():
            result.update(file_ids(child))
    elif isinstance(value, list):
        for child in value:
            result.update(file_ids(child))
    return result


def label(name, pk):
    # IDs distinguish equal titles; the full ID remains in the folder's private key.
    name = ' '.join(str(name or 'Untitled').replace('/', '-').split())[:80]
    return f'{name} [{str(pk)[:8]}]'


def resolve_context(user, domain, target_id='', category='OTHER', payment_history_id='',
                    target_type='', defer_attachment=False):
    if domain not in DOMAIN_NAMES or category not in CATEGORY_FOLDERS:
        raise ValueError('Invalid storage domain or document category.')
    if domain == 'finance' and category == 'DOCUMENT':
        raise ValueError('Use OTHER for an uncategorized finance document.')
    result = dict(domain=domain, target_id=str(target_id or ''), target_type='',
                  category=category, payment_history_id=str(payment_history_id or ''),
                  defer_attachment=bool(defer_attachment), segments=[])

    def segment(name, key):
        result['segments'].append({'name': name, 'key': key})

    segment(DOMAIN_NAMES[domain], f'domain:{domain}')
    if not target_id:
        if payment_history_id or defer_attachment:
            raise ValueError('A target is required for a payment attachment.')
        segment('Unfiled', f'{domain}:unfiled')
        return result
    try:
        pk = uuid.UUID(str(target_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Invalid attachment target ID.')
    if domain == 'ledger':
        from apps.ledger.models import Transaction
        obj = Transaction.objects.filter(pk=pk, account__user=user).first()
        if obj:
            result['target_type'] = 'transaction'
            segment(str(obj.transaction_date.year), f'ledger:year:{obj.transaction_date.year}')
            segment(obj.transaction_date.strftime('%m'), f'ledger:month:{obj.transaction_date:%Y-%m}')
            segment(label(obj.title, obj.pk), f'transaction:{obj.pk}')
    elif domain == 'finance':
        from apps.finance.models import FinancialObligation, PaymentHistory
        obj = FinancialObligation.objects.filter(pk=pk, user=user).first()
        if obj:
            result['target_type'] = 'obligation'
            segment(obj.type.title().replace('_', ' '), f'finance:type:{obj.type}')
            segment(label(obj.title, obj.pk), f'obligation:{obj.pk}')
            segment(CATEGORY_FOLDERS[category], f'obligation:{obj.pk}:category:{CATEGORY_FOLDERS[category]}')
            if payment_history_id:
                try:
                    payment_pk = uuid.UUID(str(payment_history_id))
                except (ValueError, TypeError, AttributeError):
                    raise ValueError('Invalid payment history ID.')
                if not PaymentHistory.objects.filter(pk=payment_pk, obligation=obj).exists():
                    raise ValueError('Payment history does not belong to this obligation.')
    elif domain == 'workspace':
        from apps.workspace.models import WorkspaceProject, TaskDocument
        obj = None
        if target_type in ('', 'project'):
            obj = WorkspaceProject.objects.filter(pk=pk, user=user).first()
            if obj:
                result['target_type'] = 'project'
                segment(label(obj.name, obj.pk), f'project:{obj.pk}')
                segment('Documents', f'project:{obj.pk}:documents')
        if obj is None and target_type in ('', 'task'):
            obj = TaskDocument.objects.filter(pk=pk, user=user).select_related('project').first()
            if obj:
                result['target_type'] = 'task'
                if obj.project:
                    segment(label(obj.project.name, obj.project.pk), f'project:{obj.project.pk}')
                else:
                    segment('Standalone Tasks', 'workspace:standalone-tasks')
                segment('Tasks', 'tasks')
                segment(label(obj.title, obj.pk), f'task:{obj.pk}')
    elif domain == 'note':
        from apps.workspace.models import Note
        obj = Note.objects.filter(pk=pk, user=user).select_related('project', 'folder').first()
        if obj:
            result['target_type'] = 'note'
            if obj.project:
                result['segments'] = []
                segment('Workspace', 'domain:workspace')
                segment(label(obj.project.name, obj.project.pk), f'project:{obj.project.pk}')
                segment('Pages', f'project:{obj.project.pk}:pages')
            elif obj.folder:
                segment(label(obj.folder.name, obj.folder.pk), f'note-folder:{obj.folder.pk}')
            segment(label(obj.title, obj.pk), f'note:{obj.pk}')
    elif domain == 'portfolio':
        from apps.portfolio.models import InvestmentPortfolio
        obj = InvestmentPortfolio.objects.filter(pk=pk, user=user).first()
        if obj:
            result['target_type'] = 'portfolio'
            segment(label(obj.name, obj.pk), f'portfolio:{obj.pk}')
    else:
        obj = None
    if obj is None:
        raise ValueError('Attachment target not found or does not belong to user.')
    if payment_history_id and domain != 'finance':
        raise ValueError('Payment history is only valid for finance attachments.')
    if defer_attachment and (domain != 'finance' or category != 'SLIP' or payment_history_id):
        raise ValueError('Only a new payment slip may defer attachment.')
    if target_type and result['target_type'] != target_type:
        raise ValueError('Attachment target type does not match.')
    return result


def file_references(user, drive_id):
    """Use real relationships, including trashed notes, rather than stale target_id."""
    from apps.ledger.models import TransactionAttachment
    from apps.finance.models import ObligationAttachment
    from apps.workspace.models import ProjectAttachment, Note, TaskDocument
    refs = []
    for att in TransactionAttachment.objects.filter(
        transaction__account__user=user, drive_file_id=drive_id,
    ).select_related('transaction'):
        refs.append(dict(kind='ledger', id=str(att.pk), target_id=str(att.transaction_id),
                         target_type='transaction', name=att.transaction.title, category='SLIP', payment_history_id=''))
    for att in ObligationAttachment.objects.filter(user=user, drive_file_id=drive_id).select_related('obligation'):
        refs.append(dict(kind='finance', id=str(att.pk), target_id=str(att.obligation_id),
                         target_type='obligation', name=att.obligation.title, category=att.file_type,
                         payment_history_id=str(att.payment_history_id or '')))
    for att in ProjectAttachment.objects.filter(user=user, drive_file_id=drive_id).select_related('project', 'task'):
        obj = att.task or att.project
        if obj:
            refs.append(dict(kind='workspace', id=str(att.pk), target_id=str(obj.pk),
                             target_type='task' if att.task_id else 'project',
                             name=obj.title if att.task_id else obj.name, category='DOCUMENT', payment_history_id=''))
    covered_tasks = {r['target_id'] for r in refs if r['kind'] == 'workspace' and r['target_type'] == 'task'}
    # Older tasks may have a Drive URL but no ProjectAttachment record.
    for task in TaskDocument.objects.filter(user=user, file_url__contains=drive_id).only('id', 'title', 'file_url'):
        parsed = urlparse(task.file_url)
        if parsed.hostname not in ('drive.google.com', 'www.drive.google.com', 'docs.google.com'):
            continue
        path_parts = parsed.path.strip('/').split('/')
        matches = (parse_qs(parsed.query).get('id', [''])[0] == drive_id
                   or ('d' in path_parts and path_parts.index('d') + 1 < len(path_parts)
                       and path_parts[path_parts.index('d') + 1] == drive_id))
        if matches and str(task.pk) not in covered_tasks:
            refs.append(dict(kind='workspace', id=f'task-url:{task.pk}', target_id=str(task.pk),
                             target_type='task', name=task.title, category='DOCUMENT', payment_history_id=''))
    for note in Note.objects.filter(user=user).only('id', 'title', 'blocks', 'attachments', 'is_trashed'):
        if drive_id in file_ids(note.blocks) | file_ids(note.attachments):
            refs.append(dict(kind='note', id=str(note.pk), target_id=str(note.pk), target_type='note',
                             name=note.title, category='OTHER', payment_history_id='', trashed=note.is_trashed))
    return sorted(refs, key=lambda ref: (ref['kind'], ref['target_id'], ref['id']))


def context_for_file(user, drive_file, refs):
    if refs:
        # Prefer the original owner while it exists. Shared files keep a single home.
        ref = next((r for r in refs if r['kind'] == drive_file.domain and
                    r['target_id'] == drive_file.target_id), refs[0])
        return resolve_context(user, ref['kind'], ref['target_id'], ref['category'],
                               ref['payment_history_id'], ref['target_type'])
    if drive_file.domain in ('general', 'portfolio'):
        return resolve_context(user, drive_file.domain, drive_file.target_id,
                               drive_file.category, target_type=drive_file.target_type)
    return None
