from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.storage.models import GoogleDriveConnection, DriveFile, StorageDomain
from apps.ledger.models import Account, Transaction, TransactionType
from apps.workspace.models import TaskDocument

User = get_user_model()


class StorageGoogleDriveTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='Password123!',
            email='testuser@example.com'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_oauth_url(self):
        resp = self.client.get('/api/storage/auth/url/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('auth_url', resp.data)
        self.assertIn('accounts.google.com', resp.data['auth_url'])
        self.assertIn('drive.file', resp.data['auth_url'])

    def test_status_disconnected_by_default(self):
        resp = self.client.get('/api/storage/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['is_connected'])
        self.assertEqual(resp.data['google_email'], '')

    def test_upload_blocked_without_gdrive_connection(self):
        """
        Hard rule: If Google Drive is not connected, initiating an upload
        is strictly forbidden (HTTP 403 GDRIVE_NOT_CONNECTED).
        """
        resp = self.client.post('/api/storage/initiate-upload/', {
            'domain': 'ledger',
            'file_name': 'receipt.png',
            'file_type': 'image/png',
            'file_size': 102400
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data.get('code'), 'GDRIVE_NOT_CONNECTED')

    @patch('requests.post')
    def test_initiate_upload_with_connected_drive(self, mock_post):
        """
        When connected, backend calls Google Drive API and returns Resumable Upload URL
        for direct frontend-to-cloud upload (Zero-Disk).
        """
        # Create active connection
        GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='mock_access_token',
            refresh_token='mock_refresh_token',
            token_expiry=timezone.now() + timedelta(hours=1),
            root_folder_id='folder_root_123',
            subfolder_ids={'ledger': 'folder_ledger_456'},
            is_connected=True
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Location': 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=mock_session_xyz'}
        mock_post.return_value = mock_response

        resp = self.client.post('/api/storage/initiate-upload/', {
            'domain': 'ledger',
            'file_name': 'bank_transfer_slip.jpg',
            'file_type': 'image/jpeg',
            'file_size': 204800
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('upload_url', resp.data)
        self.assertEqual(resp.data['upload_url'], 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=mock_session_xyz')
        self.assertEqual(resp.data['parent_folder_id'], 'folder_ledger_456')

    @patch('requests.get')
    def test_complete_upload_and_ledger_hook(self, mock_get):
        """
        After client uploads to Google Drive, complete-upload stores metadata in database
        and hooks up to Ledger Transaction without writing any bytes to disk.
        """
        GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='mock_access_token',
            token_expiry=timezone.now() + timedelta(hours=1),
            is_connected=True
        )

        # Mock metadata query to Google Drive API
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'id': 'gdrive_file_999',
            'name': 'bank_transfer_slip.jpg',
            'mimeType': 'image/jpeg',
            'size': 204800,
            'webViewLink': 'https://drive.google.com/file/d/gdrive_file_999/view',
            'webContentLink': 'https://drive.google.com/uc?id=gdrive_file_999'
        }
        mock_get.return_value = mock_resp

        # Create sample transaction
        acc = Account.objects.create(user=self.user, name='KBank', account_type='BANK')
        tx = Transaction.objects.create(
            user=self.user,
            account=acc,
            transaction_type=TransactionType.OUTFLOW,
            gross_amount=500,
            net_amount=500,
            title='Dinner',
            transaction_date='2026-10-23'
        )

        resp = self.client.post('/api/storage/complete-upload/', {
            'drive_file_id': 'gdrive_file_999',
            'domain': 'ledger',
            'target_id': str(tx.id),
            'file_name': 'bank_transfer_slip.jpg',
            'file_type': 'image/jpeg',
            'file_size': 204800
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['drive_file_id'], 'gdrive_file_999')
        self.assertEqual(resp.data['web_view_link'], 'https://drive.google.com/file/d/gdrive_file_999/view')

        # Check DriveFile record
        drive_file = DriveFile.objects.filter(drive_file_id='gdrive_file_999').first()
        self.assertIsNotNone(drive_file)
        self.assertEqual(drive_file.domain, StorageDomain.LEDGER)

        # Check that TransactionAttachment in ledger was also created
        self.assertEqual(tx.attachments.count(), 1)
        att = tx.attachments.first()
        self.assertEqual(att.drive_file_id, 'gdrive_file_999')
        self.assertEqual(att.drive_view_link, 'https://drive.google.com/file/d/gdrive_file_999/view')

    @patch('requests.post')
    def test_disconnect_google_drive(self, mock_post):
        conn = GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='token123',
            refresh_token='refresh123',
            is_connected=True
        )

        mock_post.return_value = MagicMock(status_code=200)

        resp = self.client.post('/api/storage/disconnect/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        conn.refresh_from_db()
        self.assertFalse(conn.is_connected)
        self.assertEqual(conn.access_token, '')
        self.assertEqual(conn.refresh_token, '')

    def test_oauth_callback_state_verification_rejects_mismatch(self):
        """
        Security Test: If OAuth callback state does not match the authenticated user id,
        the request must be rejected with HTTP 400 to prevent CSRF.
        """
        resp = self.client.post('/api/storage/auth/callback/', {
            'code': 'mock_auth_code_123',
            'state': 'attacker_user_id_999'
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('state verification failed', resp.data['error'])

    @patch('requests.get')
    def test_complete_upload_rejects_missing_drive_file(self, mock_get):
        """
        Security Test: If the drive_file_id is not found on Google Drive (HTTP 404),
        the server must reject the upload with HTTP 400 instead of creating a bogus record.
        """
        GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='mock_token',
            token_expiry=timezone.now() + timedelta(hours=1),
            is_connected=True
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        resp = self.client.post('/api/storage/complete-upload/', {
            'drive_file_id': 'bogus_nonexistent_file_id',
            'domain': 'ledger',
            'file_name': 'test.png',
            'file_type': 'image/png',
            'file_size': 1024
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('was not found in Google Drive', resp.data['error'])

    @patch('requests.get')
    def test_complete_upload_workspace_task_hook(self, mock_get):
        """
        Domain Hook Test: Uploading a document with domain='workspace' and target_id
        automatically links the drive view link to TaskDocument.file_url.
        """
        GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='mock_token',
            token_expiry=timezone.now() + timedelta(hours=1),
            is_connected=True
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'id': 'gdrive_workspace_doc_1',
            'name': 'contract_spec.pdf',
            'mimeType': 'application/pdf',
            'size': 512000,
            'webViewLink': 'https://drive.google.com/file/d/gdrive_workspace_doc_1/view',
            'webContentLink': 'https://drive.google.com/uc?id=gdrive_workspace_doc_1'
        }
        mock_get.return_value = mock_resp

        task = TaskDocument.objects.create(
            user=self.user,
            title='Client Contract Review'
        )

        resp = self.client.post('/api/storage/complete-upload/', {
            'drive_file_id': 'gdrive_workspace_doc_1',
            'domain': 'workspace',
            'target_id': str(task.id),
            'file_name': 'contract_spec.pdf',
            'file_type': 'application/pdf',
            'file_size': 512000
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        task.refresh_from_db()
        self.assertEqual(task.file_url, 'https://drive.google.com/file/d/gdrive_workspace_doc_1/view')

    @patch('apps.storage.services.requests.get')
    def test_file_stream_endpoint(self, mock_get):
        """
        The stream endpoint proxies raw bytes from Google Drive (alt=media) with the
        proper Content-Type so inline <img>/<audio> can render (Zero-Disk proxy).
        """
        GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='mock_access_token',
            refresh_token='mock_refresh_token',
            token_expiry=timezone.now() + timedelta(hours=1),
            root_folder_id='folder_root_123',
            subfolder_ids={'note': 'folder_notes'},
            is_connected=True
        )
        DriveFile.objects.create(
            user=self.user,
            drive_file_id='gdrive_image_123',
            file_name='photo.png',
            file_type='image/png',
            file_size=11,
            domain=StorageDomain.NOTE
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Content-Type': 'image/png'}
        mock_resp.iter_content.return_value = iter([b'binary-part'])
        mock_get.return_value = mock_resp

        resp = self.client.get('/api/storage/files/gdrive_image_123/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'image/png')
        self.assertIn('inline', resp['Content-Disposition'])
        body = b''.join(chunk for chunk in resp.streaming_content)
        self.assertEqual(body, b'binary-part')

        # Google Drive was called with alt=media
        called_url = mock_get.call_args.args[0]
        self.assertIn('alt=media', called_url)
        self.assertIn('gdrive_image_123', called_url)

    def test_file_stream_requires_ownership(self):
        """A user cannot stream a Drive file owned by another user."""
        other = User.objects.create_user(
            username='otheruser',
            password='Password123!',
            email='other@example.com'
        )
        DriveFile.objects.create(
            user=other,
            drive_file_id='foreign_file_1',
            file_name='secret.png',
            file_type='image/png',
            domain=StorageDomain.NOTE
        )
        resp = self.client.get('/api/storage/files/foreign_file_1/stream/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch('apps.storage.services.requests.get')
    def test_file_stream_missing_from_drive(self, mock_get):
        """If Google Drive no longer has the file, the endpoint returns 502."""
        GoogleDriveConnection.objects.create(
            user=self.user,
            google_email='user@gmail.com',
            access_token='mock_access_token',
            refresh_token='mock_refresh_token',
            token_expiry=timezone.now() + timedelta(hours=1),
            root_folder_id='folder_root_123',
            is_connected=True
        )
        DriveFile.objects.create(
            user=self.user,
            drive_file_id='deleted_file_1',
            file_name='gone.png',
            file_type='image/png',
            domain=StorageDomain.NOTE
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        resp = self.client.get('/api/storage/files/deleted_file_1/stream/')
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
