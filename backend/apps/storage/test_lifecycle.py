from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.finance.models import FinancialObligation, ObligationAttachment, PaymentHistory
from apps.workspace.models import Note, WorkspaceProject, ProjectAttachment, TaskDocument
from .models import GoogleDriveConnection, DriveFile
from .encryption import encrypt_token
from .organization import resolve_context, file_references
from .services import _find_or_create_folder, _valid_folder, ensure_folder_structure, folder_for_context
from .maintenance import preview


class DriveLifecycleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='drive-lifecycle')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.connection = GoogleDriveConnection.objects.create(
            user=self.user, google_email='owner@example.com',
            access_token=encrypt_token('fixture'), token_expiry=timezone.now() + timedelta(hours=1),
        )
        self.obligation = FinancialObligation.objects.create(
            user=self.user, title='Rent', type='SUBSCRIPTION', amount=100,
            due_date=timezone.localdate(),
        )

    def row(self, **kwargs):
        return DriveFile.objects.create(user=self.user, drive_file_id='file1', file_name='proof.png', **kwargs)

    def note(self, **kwargs):
        return Note.objects.create(user=self.user, title='Note', blocks=[
            {'id': 'image1', 'type': 'image', 'drive_file_id': 'file1'},
        ], **kwargs)

    def metadata(self, **kwargs):
        return MagicMock(status_code=200, json=MagicMock(return_value=dict(
            id='file1', name='proof.png', mimeType='image/png', size=10,
            webViewLink='https://drive.google.com/file/d/file1/view', **kwargs,
        )))

    def complete(self, **kwargs):
        payload = dict(drive_file_id='file1', domain='finance', target_id=str(self.obligation.pk),
                       file_name='proof.png', file_type='image/png', file_size=10)
        payload.update(kwargs)
        with patch('apps.storage.services.requests.get', return_value=self.metadata()):
            return self.client.post('/api/storage/complete-upload/', payload, format='json')

    def test_invalid_target_does_not_register_file(self):
        response = self.complete(target_id='00000000-0000-0000-0000-000000000001')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(DriveFile.objects.exists())

    def test_failed_domain_hook_rolls_back_registration(self):
        with patch('apps.finance.models.ObligationAttachment.objects.create', side_effect=RuntimeError('fixture failure')):
            response = self.complete(category='CONTRACT')
        self.assertEqual(response.status_code, 500)
        self.assertFalse(DriveFile.objects.exists())

    def test_categories_and_payment_history_are_attached_idempotently(self):
        payment = PaymentHistory.objects.create(user=self.user, obligation=self.obligation, paid_amount=100)
        for _ in range(2):
            response = self.complete(category='SLIP', payment_history_id=str(payment.pk))
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(DriveFile.objects.count(), 1)
        self.assertEqual(ObligationAttachment.objects.count(), 1)
        self.assertEqual(ObligationAttachment.objects.get().payment_history_id, payment.pk)
        self.assertEqual(ObligationAttachment.objects.get().file_type, 'SLIP')

    def test_foreign_payment_is_rejected_before_registration(self):
        other = FinancialObligation.objects.create(user=self.user, title='Other', type='SUBSCRIPTION', amount=100)
        payment = PaymentHistory.objects.create(user=self.user, obligation=other, paid_amount=100)
        response = self.complete(category='SLIP', payment_history_id=str(payment.pk))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(DriveFile.objects.exists())

    def test_staged_slip_is_linked_only_after_successful_payment(self):
        response = self.complete(category='SLIP', defer_attachment=True)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(ObligationAttachment.objects.exists())
        from apps.finance.strategies import ObligationStrategyFactory
        cycle_key = ObligationStrategyFactory.get_strategy('SUBSCRIPTION').get_cycle_key(self.obligation.due_date, 'MONTHLY')
        response = self.client.post(f'/api/finance/obligations/{self.obligation.pk}/pay/',
                                    {'paid_amount': 100, 'drive_file_id': 'file1', 'cycle_key': cycle_key}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        row = DriveFile.objects.get()
        self.assertEqual(row.target_id, str(self.obligation.pk))
        self.assertEqual(row.payment_history_id, str(ObligationAttachment.objects.get().payment_history_id))
        self.assertFalse(row.pending_payment)

    def test_failed_payment_keeps_staged_slip_for_retry(self):
        self.complete(category='SLIP', defer_attachment=True)
        response = self.client.post(f'/api/finance/obligations/{self.obligation.pk}/pay/',
                                    {'paid_amount': -1, 'drive_file_id': 'file1'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(DriveFile.objects.get().pending_payment)
        self.assertFalse(ObligationAttachment.objects.exists())

    def test_signed_upload_cannot_register_a_different_file_or_context(self):
        context = resolve_context(self.user, 'finance', str(self.obligation.pk), 'CONTRACT')
        token = signing.dumps(dict(user_id=str(self.user.pk), google_email=self.connection.google_email,
            context=context, parent='expected-folder', nonce='nonce1', file_size=10), salt='drive-upload')
        response = self.complete(category='CONTRACT', upload_token=token)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(DriveFile.objects.exists())

    def test_signed_upload_records_verified_folder_and_context(self):
        context = resolve_context(self.user, 'finance', str(self.obligation.pk), 'CONTRACT')
        token = signing.dumps(dict(user_id=str(self.user.pk), google_email=self.connection.google_email,
            context=context, parent='expected-folder', nonce='nonce1', file_size=10), salt='drive-upload')
        payload = dict(drive_file_id='file1', domain='finance', target_id=str(self.obligation.pk),
            category='CONTRACT', file_name='proof.png', file_type='image/png', file_size=10, upload_token=token)
        with patch('apps.storage.services.requests.get', return_value=self.metadata(
            parents=['expected-folder'], appProperties={'plos_upload': 'nonce1'})):
            response = self.client.post('/api/storage/complete-upload/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        row = DriveFile.objects.get()
        self.assertEqual(row.parent_folder_id, 'expected-folder')
        self.assertEqual(row.folder_path[-1], 'Contracts')
        self.assertEqual(row.google_email, self.connection.google_email)

    def test_project_pages_and_standalone_tasks_have_distinct_destinations(self):
        project = WorkspaceProject.objects.create(user=self.user, name='Client')
        note = self.note(project=project)
        task = TaskDocument.objects.create(user=self.user, title='Standalone')
        page_context = resolve_context(self.user, 'note', str(note.pk))
        task_context = resolve_context(self.user, 'workspace', str(task.pk))
        self.assertEqual(page_context['segments'][0]['name'], 'Workspace')
        self.assertIn('Pages', [s['name'] for s in page_context['segments']])
        self.assertIn('Standalone Tasks', [s['name'] for s in task_context['segments']])
        self.assertNotEqual(page_context['segments'][-1]['key'], task_context['segments'][-1]['key'])

    def test_shared_note_file_cannot_be_deleted_directly(self):
        self.note()
        self.note(is_trashed=True)
        self.row(domain='note')
        with patch('apps.storage.services.requests.delete') as remote:
            response = self.client.delete('/api/storage/files/by-drive-id/file1/')
        self.assertEqual(response.status_code, 409)
        remote.assert_not_called()
        self.assertTrue(DriveFile.objects.exists())

    def test_editing_note_removes_reference_without_destroying_undo_or_copy(self):
        note = self.note()
        copy = self.note()
        self.row(domain='note', target_id=str(note.pk))
        with patch('apps.storage.services.requests.delete') as remote:
            response = self.client.patch(f'/api/workspace/notes/{note.pk}/', {'blocks': []}, format='json')
        self.assertEqual(response.status_code, 200)
        remote.assert_not_called()
        self.assertEqual([r['id'] for r in file_references(self.user, 'file1')], [str(copy.pk)])

    def test_permanent_delete_preserves_shared_file_then_cleans_last_reference(self):
        source = self.note(is_trashed=True)
        copy = self.note(is_trashed=True)
        self.row(domain='note', target_id=str(source.pk))
        with patch('apps.storage.services.requests.delete', return_value=MagicMock(status_code=204)) as remote:
            first = self.client.delete(f'/api/workspace/notes/{source.pk}/permanent/')
            self.assertEqual(first.status_code, 200)
            remote.assert_not_called()
            second = self.client.delete(f'/api/workspace/notes/{copy.pk}/permanent/')
            self.assertEqual(second.status_code, 200)
            remote.assert_called_once()
        self.assertFalse(DriveFile.objects.exists())

    def test_disconnected_permanent_delete_reports_retained_files(self):
        note = self.note(is_trashed=True)
        self.row(domain='note')
        self.connection.is_connected = False
        self.connection.save()
        response = self.client.delete(f'/api/workspace/notes/{note.pk}/permanent/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['retained_files'], 1)
        self.assertTrue(DriveFile.objects.exists())

    def test_failed_workspace_delete_preserves_attachment_and_metadata(self):
        attachment = ProjectAttachment.objects.create(user=self.user, file_name='proof.png', drive_file_id='file1')
        self.row(domain='workspace')
        with patch('apps.storage.services.requests.delete', return_value=MagicMock(status_code=503)):
            response = self.client.delete(f'/api/workspace/attachments/{attachment.pk}/')
        self.assertEqual(response.status_code, 502)
        self.assertTrue(ProjectAttachment.objects.exists())
        self.assertTrue(DriveFile.objects.exists())

    def test_shared_attachment_detaches_without_deleting_remote_file(self):
        self.note()
        attachment = ObligationAttachment.objects.create(user=self.user, obligation=self.obligation,
                                                         file_name='proof.png', drive_file_id='file1')
        self.row(domain='finance')
        with patch('apps.storage.services.requests.delete') as remote:
            response = self.client.delete(f'/api/finance/attachments/{attachment.pk}/')
        self.assertEqual(response.status_code, 204)
        remote.assert_not_called()
        self.assertFalse(ObligationAttachment.objects.exists())
        self.assertTrue(DriveFile.objects.exists())

    def test_folder_lookup_failure_does_not_create_duplicate(self):
        with patch('apps.storage.services.requests.get', return_value=MagicMock(status_code=503)), \
             patch('apps.storage.services.requests.post') as create:
            with self.assertRaises(ValueError):
                _find_or_create_folder('fixture', 'Personal Life OS')
        create.assert_not_called()

    def test_cached_root_is_preserved_when_renamed(self):
        self.connection.root_folder_id = 'original-root'
        self.connection.save()
        with patch('apps.storage.services._valid_folder', return_value=True), \
             patch('apps.storage.services._find_or_create_folder') as create:
            result = ensure_folder_structure(self.connection)
        self.assertEqual(result['root_folder_id'], 'original-root')
        create.assert_not_called()

    def test_deleted_cached_folder_is_recreated_lazily(self):
        self.connection.root_folder_id = 'root'
        self.connection.subfolder_ids = {'domain:general': 'deleted-domain'}
        self.connection.save()
        context = resolve_context(self.user, 'general')
        with patch('apps.storage.services._valid_folder', side_effect=[True, False, False]), \
             patch('apps.storage.services._find_or_create_folder', side_effect=['new-domain', 'unfiled']) as create:
            parent = folder_for_context(self.connection, context)
        self.assertEqual(parent, 'unfiled')
        self.assertEqual(create.call_count, 2)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.subfolder_ids['domain:general'], 'new-domain')

    def test_entity_title_changes_rename_the_same_folder_id(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {'id': 'same-folder', 'name': 'Old title',
            'mimeType': 'application/vnd.google-apps.folder', 'parents': ['parent']}
        with patch('apps.storage.services.requests.get', return_value=response), \
             patch('apps.storage.services.requests.patch', return_value=MagicMock(status_code=200)) as rename:
            self.assertTrue(_valid_folder('fixture', 'same-folder', 'parent', 'New title'))
        self.assertTrue(rename.call_args.args[0].endswith('/same-folder'))
        self.assertEqual(rename.call_args.kwargs['json'], {'name': 'New title'})

    def test_project_page_uses_workspace_folder_instead_of_legacy_notes_folder(self):
        project = WorkspaceProject.objects.create(user=self.user, name='Client')
        note = self.note(project=project)
        self.connection.root_folder_id = 'root'
        self.connection.subfolder_ids = {'note': 'legacy-notes', 'workspace': 'legacy-workspace'}
        self.connection.save()
        context = resolve_context(self.user, 'note', str(note.pk))
        with patch('apps.storage.services._valid_folder', return_value=True) as validate:
            folder_for_context(self.connection, context)
        self.assertEqual(validate.call_args_list[1].args[1], 'legacy-workspace')

    def test_general_files_have_their_own_folder(self):
        context = resolve_context(self.user, 'general')
        self.assertEqual([s['name'] for s in context['segments']], ['General', 'Unfiled'])

    def test_duplicate_named_folders_are_not_silently_selected(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {'files': [{'id': 'one'}, {'id': 'two'}]}
        with patch('apps.storage.services.requests.get', return_value=response), \
             patch('apps.storage.services.requests.post') as create:
            with self.assertRaises(ValueError):
                _find_or_create_folder('fixture', 'Finance')
        create.assert_not_called()

    def test_expired_preview_is_rejected_without_remote_work(self):
        row = self.row(domain='note')
        with patch('apps.storage.maintenance.signing.loads', side_effect=signing.SignatureExpired()), \
             patch('apps.storage.maintenance.remote_metadata') as remote:
            response = self.client.post(f'/api/storage/files/{row.pk}/organization/',
                                       {'move_token': 'expired'}, format='json')
        self.assertEqual(response.status_code, 409)
        remote.assert_not_called()

    def test_preview_is_read_only_and_infers_legacy_target_from_actual_reference(self):
        note = self.note()
        row = self.row(domain='note', target_id='')
        with patch('apps.storage.maintenance.remote_metadata', return_value={'parents': ['old'], 'modifiedTime': 'v1'}), \
             patch('apps.storage.maintenance.folder_for_context') as folders, \
             patch('requests.patch') as move, patch('requests.delete') as delete:
            result = preview(self.user, row)
        self.assertEqual(result['state'], 'move')
        proof = signing.loads(result['move_token'], salt='drive-move')
        self.assertEqual(proof['context']['target_id'], str(note.pk))
        folders.assert_not_called()
        move.assert_not_called()
        delete.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.target_id, '')

    def test_apply_moves_same_id_and_preserves_note_reference(self):
        note = self.note()
        row = self.row(domain='note')
        meta = {'parents': ['old'], 'modifiedTime': 'v1'}
        with patch('apps.storage.maintenance.remote_metadata', return_value=meta), \
             patch('apps.storage.maintenance.folder_for_context', return_value='new-folder'), \
             patch('apps.storage.maintenance.requests.patch', return_value=MagicMock(status_code=200)) as move:
            token = preview(self.user, row)['move_token']
            response = self.client.post(f'/api/storage/files/{row.pk}/organization/', {'move_token': token}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(move.call_args.kwargs['params']['removeParents'], 'old')
        row.refresh_from_db(); note.refresh_from_db()
        self.assertEqual(row.drive_file_id, 'file1')
        self.assertEqual(note.blocks[0]['drive_file_id'], 'file1')
        self.assertEqual(row.target_id, str(note.pk))
        self.assertEqual(row.parent_folder_id, 'new-folder')

    def test_stale_preview_rejects_changed_remote_file(self):
        self.note(); row = self.row(domain='note')
        with patch('apps.storage.maintenance.remote_metadata', side_effect=[
            {'parents': ['old'], 'modifiedTime': 'v1'}, {'parents': ['elsewhere'], 'modifiedTime': 'v2'},
        ]), patch('apps.storage.maintenance.folder_for_context') as folders:
            token = preview(self.user, row)['move_token']
            response = self.client.post(f'/api/storage/files/{row.pk}/organization/', {'move_token': token}, format='json')
        self.assertEqual(response.status_code, 409)
        folders.assert_not_called()

    def test_stale_preview_rejects_changed_references(self):
        self.note(); row = self.row(domain='note')
        with patch('apps.storage.maintenance.remote_metadata', return_value={'parents': ['old'], 'modifiedTime': 'v1'}), \
             patch('apps.storage.maintenance.folder_for_context') as folders:
            token = preview(self.user, row)['move_token']
            self.note()
            response = self.client.post(f'/api/storage/files/{row.pk}/organization/', {'move_token': token}, format='json')
        self.assertEqual(response.status_code, 409)
        folders.assert_not_called()

    def test_file_manager_is_paginated_and_owner_scoped(self):
        row = self.row(domain='finance')
        other = get_user_model().objects.create_user(username='other-drive-owner')
        DriveFile.objects.create(user=other, drive_file_id='foreign', file_name='private.png')
        response = self.client.get('/api/storage/files/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], str(row.pk))
        self.assertTrue(response.data['results'][0]['unreferenced'])

    def test_different_google_account_cannot_move_or_delete_existing_file(self):
        row = self.row(domain='note', google_email='old-account@example.com')
        with patch('requests.get') as get, patch('requests.delete') as delete:
            response = self.client.get(f'/api/storage/files/{row.pk}/organization/')
            deleted = self.client.delete(f'/api/storage/files/{row.pk}/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(deleted.status_code, 409)
        get.assert_not_called(); delete.assert_not_called()

    def test_unknown_file_id_never_causes_arbitrary_remote_deletion(self):
        with patch('requests.delete') as remote:
            response = self.client.delete('/api/storage/files/by-drive-id/not-registered/')
        self.assertEqual(response.status_code, 204)
        remote.assert_not_called()

    def test_legacy_task_url_is_a_live_reference_even_without_attachment_record(self):
        task = TaskDocument.objects.create(user=self.user, title='Legacy task',
            file_url='https://drive.google.com/file/d/file1/view')
        self.row(domain='workspace')
        with patch('apps.storage.services.requests.delete') as remote:
            response = self.client.delete('/api/storage/files/by-drive-id/file1/')
        self.assertEqual(response.status_code, 409)
        remote.assert_not_called()
        refs = file_references(self.user, 'file1')
        self.assertEqual(refs[0]['target_id'], str(task.pk))

    def test_initiation_validates_target_before_creating_any_drive_folders(self):
        with patch('apps.storage.services.folder_for_context') as folders:
            response = self.client.post('/api/storage/initiate-upload/', {
                'domain': 'finance', 'target_id': '00000000-0000-0000-0000-000000000001',
                'category': 'CONTRACT', 'file_name': 'proof.png', 'file_size': 10,
            }, format='json')
        self.assertEqual(response.status_code, 400)
        folders.assert_not_called()

    def test_unregistered_upload_cleanup_requires_the_same_signed_session(self):
        context = resolve_context(self.user, 'general')
        proof = signing.dumps(dict(user_id=str(self.user.pk), google_email=self.connection.google_email,
            context=context, parent='folder', nonce='nonce1', file_size=10), salt='drive-upload')
        with patch('apps.storage.views.requests.get', return_value=MagicMock(status_code=200,
            json=MagicMock(return_value={'appProperties': {'plos_upload': 'wrong-nonce'}}))), \
             patch('apps.storage.services.requests.delete') as remote:
            response = self.client.delete('/api/storage/files/by-drive-id/file1/',
                                          {'upload_token': proof}, format='json')
        self.assertEqual(response.status_code, 400)
        remote.assert_not_called()
