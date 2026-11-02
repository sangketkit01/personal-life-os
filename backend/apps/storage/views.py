import logging
import requests
from datetime import timedelta
from django.utils import timezone
from django.core import signing
from django.db import transaction
from rest_framework import permissions, status
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import GoogleDriveConnection, DriveFile
from .serializers import (
    GoogleDriveStatusSerializer,
    InitiateUploadSerializer,
    CompleteUploadSerializer,
    DriveFileSerializer
)
from . import services

logger = logging.getLogger(__name__)


class GoogleAuthUrlView(APIView):
    """
    Returns the Google OAuth 2.0 authorization URL with cryptographically signed state.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        state = signing.dumps({'user_id': str(request.user.id)}, salt='google-drive-oauth')
        url = services.build_oauth_url(state=state)
        return Response({'auth_url': url})


class GoogleAuthCallbackView(APIView):
    """
    Receives OAuth authorization code from frontend after user consent,
    exchanges code for tokens, initializes folder structure, and activates connection.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response(
                {'error': 'Authorization code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        state = request.data.get('state')
        if not state:
            return Response(
                {'error': 'OAuth state parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            state_data = signing.loads(state, salt='google-drive-oauth', max_age=600)
            if state_data.get('user_id') != str(request.user.id):
                return Response(
                    {'error': 'OAuth state verification failed. User mismatch.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            return Response(
                {'error': 'OAuth state verification failed. Expired or invalid state token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tokens = services.exchange_code_for_tokens(code)
            access_token = tokens['access_token']
            refresh_token = tokens.get('refresh_token', '')
            expires_in = tokens.get('expires_in', 3600)
            token_expiry = timezone.now() + timedelta(seconds=expires_in)

            # Get user Google email
            google_email = services.fetch_google_user_email(access_token)

            # Create or update connection
            connection, _ = GoogleDriveConnection.objects.get_or_create(user=request.user)
            if connection.google_email and google_email and connection.google_email != google_email:
                connection.root_folder_id = ''
                connection.subfolder_ids = {}
                connection.refresh_token = ''
            connection.set_tokens(access_token=access_token, refresh_token=refresh_token if refresh_token else None)
            connection.token_expiry = token_expiry
            connection.google_email = google_email
            connection.is_connected = True
            connection.save()

            # Initialize folder structure in Google Drive
            services.ensure_folder_structure(connection)

            return Response({
                'message': 'Google Drive connected successfully.',
                'status': GoogleDriveStatusSerializer(connection).data
            })
        except Exception as e:
            logger.exception("Error during Google OAuth callback")
            return Response(
                {'error': f"Failed to complete Google Drive authentication: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class GoogleDriveStatusView(APIView):
    """
    Returns the current Google Drive storage connection status for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        connection = getattr(request.user, 'google_drive_connection', None)
        if not connection or not connection.is_connected:
            return Response({
                'is_connected': False,
                'google_email': '',
                'root_folder_id': '',
                'subfolder_ids': {}
            })

        return Response(GoogleDriveStatusSerializer(connection).data)


class InitiateUploadView(APIView):
    """
    Initiates a direct Google Drive Resumable Upload session for Option B.
    Bypasses local disk entirely (Zero-Disk guarantee).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        connection = getattr(request.user, 'google_drive_connection', None)
        if not connection or not connection.is_connected:
            return Response(
                {
                    'error': 'Google Drive is not connected. File storage is disabled until Google Drive is linked.',
                    'code': 'GDRIVE_NOT_CONNECTED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InitiateUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        origin = request.META.get('HTTP_ORIGIN')
        try:
            upload_session = services.initiate_resumable_upload(
                connection=connection,
                domain=data['domain'],
                file_name=data['file_name'],
                file_type=data['file_type'],
                file_size=data['file_size'],
                origin=origin,
                **{key: data[key] for key in ('target_id', 'target_type', 'category', 'payment_history_id', 'defer_attachment')},
            )
            return Response(upload_session)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error initiating resumable upload")
            return Response(
                {'error': f"Could not initiate Google Drive upload session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompleteUploadView(APIView):
    """
    Confirms an uploaded file and registers its metadata in the database.
    Optionally links to domain objects (Ledger Transaction, Finance Obligation, etc.).
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        connection = getattr(request.user, 'google_drive_connection', None)
        if not connection or not connection.is_connected:
            return Response(
                {'error': 'Google Drive is not connected.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            GoogleDriveConnection.objects.select_for_update().get(pk=connection.pk)
            drive_file = services.complete_resumable_upload(
                user=request.user,
                drive_file_id=data['drive_file_id'],
                domain=data['domain'],
                target_id=data.get('target_id', ''),
                file_name=data['file_name'],
                file_type=data.get('file_type', ''),
                file_size=data.get('file_size', 0),
                **{key: data[key] for key in ('target_type', 'category', 'payment_history_id', 'defer_attachment', 'upload_token')},
            )

            # Domain-specific attachment hooks
            domain = data['domain']
            target_id = data.get('target_id', '')

            if domain == 'ledger' and target_id:
                from apps.ledger.models import Transaction, TransactionAttachment
                tx = Transaction.objects.filter(id=target_id, account__user=request.user).first()
                if not tx:
                    raise ValueError('Ledger transaction no longer exists or does not belong to user.')
                if not TransactionAttachment.objects.filter(transaction=tx, drive_file_id=drive_file.drive_file_id).exists():
                    TransactionAttachment.objects.create(
                        transaction=tx,
                        file_name=drive_file.file_name,
                        file_type=drive_file.file_type or 'application/octet-stream',
                        file_size=drive_file.file_size,
                        drive_file_id=drive_file.drive_file_id,
                        drive_view_link=drive_file.web_view_link,
                        drive_download_link=drive_file.web_content_link,
                        slip_reference=''
                    )

            elif domain == 'finance' and target_id and not data['defer_attachment']:
                from apps.finance.models import FinancialObligation, ObligationAttachment
                obl = FinancialObligation.objects.filter(id=target_id, user=request.user).first()
                if not obl:
                    raise ValueError('Financial obligation no longer exists or does not belong to user.')
                if not ObligationAttachment.objects.filter(obligation=obl, drive_file_id=drive_file.drive_file_id,
                                                           payment_history_id=data['payment_history_id'] or None).exists():
                    file_type_choice = data.get('category', 'OTHER')
                    ObligationAttachment.objects.create(
                        user=request.user,
                        obligation=obl,
                        payment_history_id=data['payment_history_id'] or None,
                        file_name=drive_file.file_name,
                        file_size=drive_file.file_size,
                        file_type=file_type_choice,
                        drive_file_id=drive_file.drive_file_id,
                        drive_view_link=drive_file.web_view_link,
                        drive_download_link=drive_file.web_content_link
                    )

            elif domain == 'note' and target_id:
                import uuid as uuid_lib
                from apps.workspace.models import Note

                try:
                    note_uuid = uuid_lib.UUID(str(target_id))
                except (ValueError, AttributeError, TypeError):
                    raise ValueError('Invalid note target ID.')

                note = Note.objects.filter(id=note_uuid, user=request.user).first()
                if not note:
                    raise ValueError('Note no longer exists or does not belong to user.')

                # Inline blocks (image/audio/file) are the single source of truth for
                # note media. Only opt-in legacy callers duplicate into note.attachments.
                if request.data.get('legacy_attachment') is True:
                    attachments = note.attachments if isinstance(note.attachments, list) else []
                    if not any(isinstance(a, dict) and a.get('drive_file_id') == drive_file.drive_file_id for a in attachments):
                        attachment_entry = {
                            'id': str(uuid_lib.uuid4()),
                            'file_name': drive_file.file_name,
                            'file_type': drive_file.file_type or 'application/octet-stream',
                            'file_size': drive_file.file_size,
                            'drive_file_id': drive_file.drive_file_id,
                            'drive_view_link': drive_file.web_view_link,
                            'uploaded_at': timezone.now().isoformat()
                        }
                        attachments.append(attachment_entry)
                        note.attachments = attachments
                        note.save(update_fields=['attachments'])

            elif domain == 'workspace' and target_id:
                import uuid as uuid_lib
                from apps.workspace.models import ProjectAttachment, TaskDocument, WorkspaceProject

                try:
                    target_uuid = uuid_lib.UUID(str(target_id))
                except (ValueError, AttributeError, TypeError):
                    raise ValueError('Invalid workspace target ID.')

                project = WorkspaceProject.objects.filter(id=target_uuid, user=request.user).first()
                if project:
                    if not ProjectAttachment.objects.filter(project=project, drive_file_id=drive_file.drive_file_id).exists():
                        ProjectAttachment.objects.create(
                            user=request.user,
                            project=project,
                            task=None,
                            file_name=drive_file.file_name,
                            file_type=drive_file.file_type or 'application/octet-stream',
                            file_size=drive_file.file_size,
                            category=data.get('category', 'DOCUMENT'),
                            drive_file_id=drive_file.drive_file_id,
                            drive_view_link=drive_file.web_view_link,
                            drive_download_link=drive_file.web_content_link
                        )
                else:
                    task = TaskDocument.objects.filter(id=target_uuid, user=request.user).select_related('project').first()
                    if not task:
                        raise ValueError('Workspace target no longer exists or does not belong to user.')
                    task.file_url = drive_file.web_view_link or drive_file.web_content_link
                    task.save(update_fields=['file_url'])
                    # Always register the attachment, even for tasks without a project
                    if not ProjectAttachment.objects.filter(task=task, drive_file_id=drive_file.drive_file_id).exists():
                        ProjectAttachment.objects.create(
                            user=request.user,
                            project=task.project,
                            task=task,
                            file_name=drive_file.file_name,
                            file_type=drive_file.file_type or 'application/octet-stream',
                            file_size=drive_file.file_size,
                            category=data.get('category', 'DOCUMENT'),
                            drive_file_id=drive_file.drive_file_id,
                            drive_view_link=drive_file.web_view_link,
                            drive_download_link=drive_file.web_content_link
                        )

            return Response(
                DriveFileSerializer(drive_file).data,
                status=status.HTTP_201_CREATED
            )
        except (ValueError, signing.BadSignature) as e:
            transaction.set_rollback(True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            transaction.set_rollback(True)
            logger.exception("Error completing upload")
            return Response(
                {'error': f"Failed to register uploaded file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriveFileByDriveIdView(APIView):
    """
    Idempotent DELETE of the authenticated user's Drive file by its Google Drive file id.
    Deletes the remote file from Google Drive and the local metadata record.
    Also provides GET to check if the file is registered in the database.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, drive_file_id):
        drive_file = DriveFile.objects.filter(
            drive_file_id=drive_file_id,
            user=request.user
        ).first()
        if not drive_file:
            return Response({'error': 'File not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DriveFileSerializer(drive_file).data, status=status.HTTP_200_OK)

    def delete(self, request, drive_file_id):
        # BOLA protection: If the file belongs to another user, do not touch their file or remote Drive
        if DriveFile.objects.filter(drive_file_id=drive_file_id).exclude(user=request.user).exists():
            return Response(status=status.HTTP_204_NO_CONTENT)

        row = DriveFile.objects.filter(user=request.user, drive_file_id=drive_file_id).first()
        if not row:
            # Unknown IDs must never allow deletion of arbitrary files accessible to the app.
            upload_token = request.data.get('upload_token')
            if not upload_token:
                return Response(status=status.HTTP_204_NO_CONTENT)
            try:
                proof = signing.loads(upload_token, salt='drive-upload', max_age=86400)
                connection = request.user.google_drive_connection
                if proof['user_id'] != str(request.user.pk) or proof['google_email'] != connection.google_email:
                    raise ValueError('Upload owner does not match.')
                token = services.refresh_access_token_if_needed(connection)
                meta = requests.get(f'{services.GOOGLE_DRIVE_FILES_URL}/{drive_file_id}',
                    headers={'Authorization': f'Bearer {token}'}, params={'fields': 'appProperties'}, timeout=15)
                if meta.status_code == 404:
                    return Response(status=status.HTTP_204_NO_CONTENT)
                if meta.status_code != 200 or meta.json().get('appProperties', {}).get('plos_upload') != proof['nonce']:
                    raise ValueError('File does not belong to this upload session.')
            except (ValueError, signing.BadSignature, requests.RequestException) as exc:
                return Response({'error': str(exc)}, status=400)

        try:
            success = services.delete_file_from_drive_by_id(request.user, drive_file_id)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        if not success:
            return Response(
                {'error': 'Failed to delete file from Google Drive.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriveFileStreamView(APIView):
    """
    Authenticated proxy that streams raw file bytes from Google Drive (alt=media).
    Required for inline <img> / <audio> rendering because Drive web_view_link
    returns an HTML preview page instead of the binary content.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, drive_file_id):
        drive_file = DriveFile.objects.filter(
            drive_file_id=drive_file_id,
            user=request.user
        ).first()
        if not drive_file:
            return Response({'error': 'File not found.'}, status=status.HTTP_404_NOT_FOUND)

        stream = services.stream_file_from_drive(request.user, drive_file)
        if stream is None:
            return Response(
                {'error': 'Could not stream file from Google Drive.'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        iterator, content_type = stream
        response = StreamingHttpResponse(iterator, content_type=content_type)
        safe_name = drive_file.file_name.replace('"', '')
        response['Content-Disposition'] = f'inline; filename="{safe_name}"'
        return response


class DisconnectGoogleDriveView(APIView):
    """
    Revokes authorization token and disconnects Google Drive.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        services.revoke_and_disconnect(request.user)
        return Response({'message': 'Google Drive disconnected successfully.'})


class DriveFileListView(APIView):
    """
    Lists files uploaded to Google Drive by the current user.
    Can be filtered by ?domain=ledger or ?target_id=<id>.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        domain = request.query_params.get('domain')
        target_id = request.query_params.get('target_id')

        qs = DriveFile.objects.filter(user=request.user)
        if domain:
            qs = qs.filter(domain=domain)
        if target_id:
            qs = qs.filter(target_id=target_id)

        # Keep the array response for legacy clients; the file manager opts into pagination.
        if request.query_params.get('page') is not None:
            from .maintenance import describe
            try:
                page = max(1, int(request.query_params['page']))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid page.'}, status=400)
            count = qs.count()
            rows = list(qs[(page - 1) * 20:page * 20])
            return Response({'count': count, 'page': page, 'page_size': 20,
                'results': [dict(DriveFileSerializer(row).data, **describe(request.user, row)) for row in rows]})
        return Response(DriveFileSerializer(qs, many=True).data)


class DriveFileDetailView(APIView):
    """
    Deletes a file from Google Drive and removes its database record.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        drive_file = DriveFile.objects.filter(id=pk, user=request.user).first()
        if not drive_file:
            return Response({'error': 'File not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            success = services.delete_file_from_drive(request.user, drive_file)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        if not success:
            return Response(
                {'error': 'Failed to delete file from Google Drive. Metadata has been preserved.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriveOrganizationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from .maintenance import preview
        row = DriveFile.objects.filter(user=request.user, pk=pk).first()
        if not row:
            return Response({'error': 'File not found.'}, status=404)
        try:
            return Response(preview(request.user, row))
        except (ValueError, requests.RequestException) as exc:
            return Response({'error': str(exc)}, status=400)

    def post(self, request, pk):
        from .maintenance import apply_move
        row = DriveFile.objects.filter(user=request.user, pk=pk).first()
        if not row:
            return Response({'error': 'File not found.'}, status=404)
        try:
            row = apply_move(request.user, row, request.data.get('move_token', ''))
            return Response(DriveFileSerializer(row).data)
        except (ValueError, signing.BadSignature, requests.RequestException) as exc:
            return Response({'error': str(exc)}, status=409)
