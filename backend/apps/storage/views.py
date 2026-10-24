import logging
from datetime import timedelta
from django.utils import timezone
from django.core import signing
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
                origin=origin
            )
            return Response(upload_session)
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
            drive_file = services.complete_resumable_upload(
                user=request.user,
                drive_file_id=data['drive_file_id'],
                domain=data['domain'],
                target_id=data.get('target_id', ''),
                file_name=data['file_name'],
                file_type=data.get('file_type', ''),
                file_size=data.get('file_size', 0)
            )

            # Domain-specific attachment hooks
            domain = data['domain']
            target_id = data.get('target_id', '')

            if domain == 'ledger' and target_id:
                from apps.ledger.models import Transaction, TransactionAttachment
                tx = Transaction.objects.filter(id=target_id, account__user=request.user).first()
                if not tx:
                    return Response(
                        {'error': f"Ledger transaction '{target_id}' not found or does not belong to user."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
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

            elif domain == 'finance' and target_id:
                from apps.finance.models import FinancialObligation, ObligationAttachment
                obl = FinancialObligation.objects.filter(id=target_id, user=request.user).first()
                if not obl:
                    return Response(
                        {'error': f"Financial obligation '{target_id}' not found or does not belong to user."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                file_type_choice = data.get('category', 'OTHER')
                ObligationAttachment.objects.create(
                    user=request.user,
                    obligation=obl,
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
                    return Response(
                        {'error': f"Invalid note target id '{target_id}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                note = Note.objects.filter(id=note_uuid, user=request.user).first()
                if not note:
                    return Response(
                        {'error': f"Note '{target_id}' not found or does not belong to user."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                attachment_entry = {
                    'id': str(uuid_lib.uuid4()),
                    'file_name': drive_file.file_name,
                    'file_type': drive_file.file_type or 'application/octet-stream',
                    'file_size': drive_file.file_size,
                    'drive_file_id': drive_file.drive_file_id,
                    'drive_view_link': drive_file.web_view_link,
                    'uploaded_at': timezone.now().isoformat()
                }
                attachments = note.attachments if isinstance(note.attachments, list) else []
                attachments.append(attachment_entry)
                note.attachments = attachments
                note.save(update_fields=['attachments'])

            elif domain == 'workspace' and target_id:
                import uuid as uuid_lib
                from apps.workspace.models import ProjectAttachment, TaskDocument, WorkspaceProject

                try:
                    target_uuid = uuid_lib.UUID(str(target_id))
                except (ValueError, AttributeError, TypeError):
                    return Response(
                        {'error': f"Invalid workspace target id '{target_id}'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                project = WorkspaceProject.objects.filter(id=target_uuid, user=request.user).first()
                if project:
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
                        return Response(
                            {'error': f"Workspace target '{target_id}' not found or does not belong to user."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    task.file_url = drive_file.web_view_link or drive_file.web_content_link
                    task.save(update_fields=['file_url'])
                    # Always register the attachment, even for tasks without a project
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
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Error completing upload")
            return Response(
                {'error': f"Failed to register uploaded file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

        services.delete_file_from_drive(request.user, drive_file)
        return Response(status=status.HTTP_204_NO_CONTENT)
