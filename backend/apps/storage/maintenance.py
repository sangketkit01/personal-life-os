"""Read-only previews followed by explicit, stale-safe moves of existing file IDs."""
import requests
from django.core import signing
from .models import GoogleDriveConnection
from .organization import file_references, context_for_file
from .services import GOOGLE_DRIVE_FILES_URL, refresh_access_token_if_needed, folder_for_context


def connection_for_file(user, row):
    connection = GoogleDriveConnection.objects.filter(user=user, is_connected=True).first()
    if not connection:
        raise ValueError('Connect Google Drive first.')
    if row.google_email and row.google_email != connection.google_email:
        raise ValueError('Reconnect the Google account that owns this file.')
    return connection


def describe(user, row):
    refs = file_references(user, row.drive_file_id)
    try:
        context = context_for_file(user, row, refs)
        destination = [part['name'] for part in context['segments']] if context else []
    except ValueError:
        destination = []
    return dict(references=refs, shared=len(refs) > 1, unreferenced=not refs,
                destination=destination)


def remote_metadata(connection, row):
    token = refresh_access_token_if_needed(connection)
    response = requests.get(f'{GOOGLE_DRIVE_FILES_URL}/{row.drive_file_id}',
                            headers={'Authorization': f'Bearer {token}'},
                            params={'fields': 'id,name,parents,trashed,modifiedTime'}, timeout=15)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise ValueError(f'Could not inspect Drive file (HTTP {response.status_code}).')
    return response.json()


def preview(user, row):
    connection = connection_for_file(user, row)
    refs = file_references(user, row.drive_file_id)
    context = context_for_file(user, row, refs)
    meta = remote_metadata(connection, row)
    result = describe(user, row)
    result.update(state='unreferenced', move_token='', current_parents=[], remote_name=row.file_name)
    if not meta or meta.get('trashed'):
        result['state'] = 'missing' if not meta else 'trashed'
        return result
    result.update(current_parents=meta.get('parents', []), remote_name=meta.get('name', row.file_name))
    if not context:
        return result
    destination = [s['name'] for s in context['segments']]
    result['state'] = ('current' if row.folder_path == destination and row.parent_folder_id
                       in meta.get('parents', []) else 'move')
    result['move_token'] = signing.dumps(dict(
        user_id=str(user.pk), row_id=str(row.pk), drive_id=row.drive_file_id,
        google_email=connection.google_email, context=context, references=refs,
        parents=meta.get('parents', []), modified=meta.get('modifiedTime'),
    ), salt='drive-move', compress=True)
    return result


def apply_move(user, row, move_token):
    proof = signing.loads(move_token, salt='drive-move', max_age=600)
    connection = connection_for_file(user, row)
    refs = file_references(user, row.drive_file_id)
    context = context_for_file(user, row, refs)
    if (proof['user_id'] != str(user.pk) or proof['row_id'] != str(row.pk)
            or proof['drive_id'] != row.drive_file_id or not context
            or proof['google_email'] != connection.google_email
            or proof['context'] != context or proof['references'] != refs):
        raise ValueError('File ownership or references changed. Preview again before moving.')
    meta = remote_metadata(connection, row)
    if (not meta or meta.get('trashed') or meta.get('parents', []) != proof['parents']
            or meta.get('modifiedTime') != proof['modified']):
        raise ValueError('File changed in Google Drive. Preview again before moving.')
    parent = folder_for_context(connection, context)
    old_parents = meta.get('parents', [])
    if parent not in old_parents:
        token = refresh_access_token_if_needed(connection)
        params = {'addParents': parent, 'fields': 'id,parents'}
        if old_parents:
            params['removeParents'] = ','.join(old_parents)
        response = requests.patch(f'{GOOGLE_DRIVE_FILES_URL}/{row.drive_file_id}',
                                  headers={'Authorization': f'Bearer {token}'}, params=params,
                                  json={}, timeout=15)
        if response.status_code != 200:
            raise ValueError('Could not move the file. Preview again before retrying.')
    row.domain = context['domain']
    row.target_id = context['target_id']
    row.target_type = context['target_type']
    row.category = context['category']
    row.payment_history_id = context['payment_history_id']
    row.google_email = connection.google_email
    row.parent_folder_id = parent
    row.folder_path = [s['name'] for s in context['segments']]
    row.save()
    return row
