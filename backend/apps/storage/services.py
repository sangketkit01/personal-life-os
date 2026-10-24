import json
import logging
import urllib.parse
from datetime import timedelta
import requests
from django.conf import settings
from django.utils import timezone
from .models import GoogleDriveConnection, DriveFile, StorageDomain

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
GOOGLE_REVOKE_URL = 'https://oauth2.googleapis.com/revoke'
GOOGLE_DRIVE_FILES_URL = 'https://www.googleapis.com/drive/v3/files'
GOOGLE_DRIVE_RESUMABLE_UPLOAD_URL = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable'


def build_oauth_url(state: str = '') -> str:
    """
    Constructs Google OAuth 2.0 authorization consent URL for Google Drive.
    Uses 'drive.file' scope for strict security and granular application isolation.
    """
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(settings.GOOGLE_DRIVE_SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
    }
    if state:
        params['state'] = state
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchanges the authorization code for an OAuth access token and refresh token.
    """
    payload = {
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    resp = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=15)
    if resp.status_code != 200:
        logger.error(f"Failed to exchange Google OAuth code: {resp.text}")
        raise ValueError(f"Google OAuth token exchange failed: {resp.text}")
    return resp.json()


def fetch_google_user_email(access_token: str) -> str:
    """
    Retrieves the connected user's Google email address for UI confirmation.
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        resp = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('email', '')
    except Exception as e:
        logger.warning(f"Could not retrieve Google userinfo: {e}")
    return ''


def refresh_access_token_if_needed(connection: GoogleDriveConnection) -> str:
    """
    Validates the connection's access token and automatically refreshes it
    using the refresh token if expired.
    """
    if connection.is_token_valid():
        return connection.get_access_token()

    plain_refresh_token = connection.get_refresh_token()
    if not plain_refresh_token:
        raise ValueError("Google Drive connection lacks a valid refresh token. Please reconnect.")

    payload = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'refresh_token': plain_refresh_token,
        'grant_type': 'refresh_token',
    }
    resp = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=15)
    if resp.status_code != 200:
        logger.error(f"Failed to refresh Google OAuth token: {resp.text}")
        connection.is_connected = False
        connection.save(update_fields=['is_connected'])
        raise ValueError(f"Failed to refresh Google Drive session: {resp.text}")

    data = resp.json()
    connection.set_tokens(access_token=data['access_token'])
    expires_in = data.get('expires_in', 3600)
    connection.token_expiry = timezone.now() + timedelta(seconds=expires_in)
    connection.is_connected = True
    connection.save(update_fields=['access_token', 'token_expiry', 'is_connected'])
    return connection.get_access_token()


def _find_or_create_folder(access_token: str, folder_name: str, parent_id: str = None) -> str:
    """
    Finds an existing folder by name (and optional parent) or creates it in Google Drive.
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # Query for existing non-trashed folder
    query_parts = [
        f"name = '{folder_name}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false"
    ]
    if parent_id:
        query_parts.append(f"'{parent_id}' in parents")

    params = {
        'q': ' and '.join(query_parts),
        'fields': 'files(id, name)',
        'spaces': 'drive'
    }
    resp = requests.get(GOOGLE_DRIVE_FILES_URL, headers=headers, params=params, timeout=15)
    if resp.status_code == 200:
        files = resp.json().get('files', [])
        if files:
            return files[0]['id']

    # Create new folder if not found
    body = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
    }
    if parent_id:
        body['parents'] = [parent_id]

    create_resp = requests.post(GOOGLE_DRIVE_FILES_URL, headers=headers, json=body, timeout=15)
    if create_resp.status_code in (200, 201):
        return create_resp.json()['id']

    logger.error(f"Failed to create Google Drive folder '{folder_name}': {create_resp.text}")
    raise ValueError(f"Failed to create folder '{folder_name}' in Google Drive")


def ensure_folder_structure(connection: GoogleDriveConnection) -> dict:
    """
    Ensures that the root 'Personal Life OS' directory and all domain subfolders
    (Ledger, Finance, Portfolio, Workspace) exist in Google Drive.
    """
    access_token = refresh_access_token_if_needed(connection)

    # 1. Root folder
    root_id = _find_or_create_folder(access_token, "Personal Life OS")
    connection.root_folder_id = root_id

    # 2. Domain subfolders
    subfolders = {}
    domain_folder_names = {
        StorageDomain.LEDGER: "Ledger",
        StorageDomain.FINANCE: "Finance",
        StorageDomain.PORTFOLIO: "Portfolio",
        StorageDomain.WORKSPACE: "Workspace",
        StorageDomain.NOTE: "Notes"
    }
    for domain_key, folder_name in domain_folder_names.items():
        sub_id = _find_or_create_folder(access_token, folder_name, parent_id=root_id)
        subfolders[domain_key] = sub_id

    connection.subfolder_ids = subfolders
    connection.save(update_fields=['root_folder_id', 'subfolder_ids'])
    return {
        'root_folder_id': root_id,
        'subfolders': subfolders
    }


def initiate_resumable_upload(
    connection: GoogleDriveConnection,
    domain: str,
    file_name: str,
    file_type: str,
    file_size: int,
    origin: str = None
) -> dict:
    """
    Initiates a Google Drive Resumable Upload session for Option B.
    Returns a resumable upload URI to which the client browser can PUT bytes directly,
    bypassing server storage entirely (Zero-Disk guarantee).
    """
    if not connection.is_connected:
        raise ValueError("Google Drive is not connected for this account.")

    access_token = refresh_access_token_if_needed(connection)

    # Determine parent folder (re-ensure hierarchy when the domain subfolder is new)
    folder_id = connection.subfolder_ids.get(domain)
    if not folder_id:
        folder_info = ensure_folder_structure(connection)
        folder_id = folder_info['subfolders'].get(domain, folder_info['root_folder_id'])

    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Upload-Content-Type': file_type or 'application/octet-stream',
        'X-Upload-Content-Length': str(file_size),
        'Content-Type': 'application/json; charset=UTF-8'
    }
    if origin:
        headers['Origin'] = origin

    body = {
        'name': file_name,
        'parents': [folder_id]
    }

    resp = requests.post(
        GOOGLE_DRIVE_RESUMABLE_UPLOAD_URL,
        headers=headers,
        data=json.dumps(body),
        timeout=15
    )

    if resp.status_code != 200 or 'Location' not in resp.headers:
        logger.error(f"Failed to initiate GDrive resumable upload: status {resp.status_code}, response: {resp.text}")
        raise ValueError("Failed to initiate Google Drive direct upload session.")

    upload_url = resp.headers['Location']
    return {
        'upload_url': upload_url,
        'file_name': file_name,
        'file_type': file_type,
        'file_size': file_size,
        'parent_folder_id': folder_id
    }


def complete_resumable_upload(
    user,
    drive_file_id: str,
    domain: str,
    target_id: str,
    file_name: str,
    file_type: str,
    file_size: int
) -> DriveFile:
    """
    Registers metadata of an uploaded file into the database.
    Queries Google Drive API to fetch canonical URLs (view link, download link, thumbnail).
    Zero file bytes are written to server disk.
    """
    connection = getattr(user, 'google_drive_connection', None)
    web_view_link = ''
    web_content_link = ''
    thumbnail_link = ''

    if connection and connection.is_connected:
        try:
            token = refresh_access_token_if_needed(connection)
            fields_url = f"{GOOGLE_DRIVE_FILES_URL}/{drive_file_id}?fields=id,name,mimeType,size,webViewLink,webContentLink,thumbnailLink"
            headers = {'Authorization': f'Bearer {token}'}
            resp = requests.get(fields_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                meta = resp.json()
                file_name = meta.get('name') or file_name
                file_type = meta.get('mimeType') or file_type
                file_size = int(meta.get('size') or file_size)
                web_view_link = meta.get('webViewLink', '')
                web_content_link = meta.get('webContentLink', '')
                thumbnail_link = meta.get('thumbnailLink', '')
            elif resp.status_code == 404:
                raise ValueError(f"Uploaded file ID '{drive_file_id}' was not found in Google Drive application scope.")
            else:
                raise ValueError(f"Google Drive verification failed (HTTP {resp.status_code}): {resp.text}")
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Error fetching Google Drive file metadata for {drive_file_id}: {e}")
            raise ValueError(f"Could not verify file with Google Drive: {str(e)}")

    drive_file = DriveFile.objects.create(
        user=user,
        drive_file_id=drive_file_id,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        web_view_link=web_view_link,
        web_content_link=web_content_link,
        thumbnail_link=thumbnail_link,
        domain=domain,
        target_id=target_id or ''
    )
    return drive_file


def stream_file_from_drive(user, drive_file: DriveFile):
    """
    Opens a streaming iterator to the raw bytes of a file in Google Drive (alt=media).
    Returns (chunk_iterator, content_type) or None when the file cannot be streamed.
    Zero bytes are written to local disk - chunks are proxied straight to the client.
    """
    connection = getattr(user, 'google_drive_connection', None)
    if not connection or not connection.is_connected:
        return None
    try:
        token = refresh_access_token_if_needed(connection)
        media_url = f"{GOOGLE_DRIVE_FILES_URL}/{drive_file.drive_file_id}?alt=media"
        resp = requests.get(
            media_url,
            headers={'Authorization': f'Bearer {token}'},
            stream=True,
            timeout=30
        )
        if resp.status_code != 200:
            resp.close()
            logger.warning(
                "Could not stream file %s from Google Drive (HTTP %s)",
                drive_file.drive_file_id,
                resp.status_code
            )
            return None
        content_type = resp.headers.get('Content-Type') or drive_file.file_type or 'application/octet-stream'
        return resp.iter_content(chunk_size=64 * 1024), content_type
    except Exception as e:
        logger.warning("Error streaming file %s from Google Drive: %s", drive_file.drive_file_id, e)
        return None


def delete_file_from_drive(user, drive_file: DriveFile) -> bool:
    """
    Deletes the file from Google Drive and removes the local metadata record.
    """
    connection = getattr(user, 'google_drive_connection', None)
    if connection and connection.is_connected:
        try:
            token = refresh_access_token_if_needed(connection)
            headers = {'Authorization': f'Bearer {token}'}
            del_url = f"{GOOGLE_DRIVE_FILES_URL}/{drive_file.drive_file_id}"
            requests.delete(del_url, headers=headers, timeout=10)
        except Exception as e:
            logger.warning(f"Failed to delete file {drive_file.drive_file_id} from Google Drive: {e}")

    drive_file.delete()
    return True


def revoke_and_disconnect(user) -> bool:
    """
    Revokes the Google OAuth token and deactivates the user's Google Drive connection.
    """
    connection = getattr(user, 'google_drive_connection', None)
    if not connection:
        return False

    token_to_revoke = connection.get_refresh_token() or connection.get_access_token()
    if token_to_revoke:
        try:
            requests.post(GOOGLE_REVOKE_URL, params={'token': token_to_revoke}, timeout=10)
        except Exception as e:
            logger.warning(f"Failed to revoke Google token at revoke endpoint: {e}")

    connection.is_connected = False
    connection.access_token = ''
    connection.refresh_token = ''
    connection.token_expiry = None
    connection.save(update_fields=['is_connected', 'access_token', 'refresh_token', 'token_expiry'])
    return True
