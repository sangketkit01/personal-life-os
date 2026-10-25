"""
Interactive SSH terminal WebSocket consumer.

Auth: the same JWT access token the REST API uses (HttpOnly cookie by
default, `?token=` query fallback for cross-origin dev setups), including
the UserDeviceSession revocation check. BOLA: the consumer closes with
4403 unless the asset belongs to the authenticated user.

Zero-Disk Policy: SSH credentials are decrypted in memory and handed to
paramiko directly - nothing touches the filesystem.
"""
import asyncio
import json
import logging

import jwt
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.accounts.services import log_activity
from apps.accounts.tokens import decode_token
from .models import InfrastructureAsset
from .ssh_service import open_ssh_client

logger = logging.getLogger(__name__)

WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403
WS_CLOSE_SSH_FAILED = 1011


class SshTerminalConsumer(AsyncWebsocketConsumer):
    """Bridges the browser xterm.js terminal to a paramiko PTY shell."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.asset = None
        self.ssh_client = None
        self.channel = None
        self._reader_task = None

    # ----- lifecycle -----

    async def connect(self):
        user = await self._authenticate_from_cookie()
        if user is None:
            await self.close(code=WS_CLOSE_UNAUTHORIZED)
            return

        asset_id = self.scope['url_route']['kwargs'].get('asset_id')
        asset = await self._get_owned_asset(asset_id, user)
        if asset is None:
            await self.close(code=WS_CLOSE_FORBIDDEN)
            return

        self.user = user
        self.asset = asset

        try:
            self.ssh_client, self.channel = await asyncio.to_thread(self._open_pty)
        except Exception as exc:
            logger.warning('SSH terminal open failed for asset %s: %s', asset_id, exc)
            await self.close(code=WS_CLOSE_SSH_FAILED)
            return

        await self.accept()
        await self._log('SSH_SESSION_START', f'Interactive SSH session opened to {asset.name}')
        self._reader_task = asyncio.create_task(self._stream_output())

    async def disconnect(self, close_code):
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._reader_task = None
        if self.channel is not None or self.ssh_client is not None:
            await asyncio.to_thread(self._close_ssh)
        if self.user is not None and self.asset is not None:
            await self._log('SSH_SESSION_END', f'Interactive SSH session closed for {self.asset.name}')

    async def receive(self, text_data=None, bytes_data=None):
        if self.channel is None:
            return
        try:
            payload = json.loads(text_data or '{}')
        except json.JSONDecodeError:
            return

        msg_type = payload.get('type')
        if msg_type == 'input':
            data = str(payload.get('data', ''))
            if data:
                await asyncio.to_thread(self.channel.send, data.encode('utf-8'))
        elif msg_type == 'resize':
            try:
                cols = max(2, min(int(payload.get('cols', 120)), 500))
                rows = max(1, min(int(payload.get('rows', 32)), 200))
            except (TypeError, ValueError):
                return
            await asyncio.to_thread(self.channel.resize_pty, cols, rows)

    # ----- helpers -----

    def _open_pty(self):
        client = open_ssh_client(self.asset)
        channel = client.invoke_shell(term='xterm-256color', width=120, height=32)
        return client, channel

    def _close_ssh(self):
        for closer in (lambda: self.channel.close(), lambda: self.ssh_client.close()):
            try:
                closer()
            except Exception:
                pass
        self.channel = None
        self.ssh_client = None

    async def _stream_output(self):
        """Pump PTY output to the browser until the shell closes."""
        try:
            while True:
                data = await asyncio.to_thread(self.channel.recv, 4096)
                if not data:
                    break
                await self.send(text_data=json.dumps({
                    'type': 'output',
                    'data': data.decode('utf-8', errors='replace')
                }))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug('SSH output stream ended for %s: %s', self.asset.name, exc)
        try:
            await self.send(text_data=json.dumps({'type': 'closed'}))
        except Exception:
            pass

    def _cookie_token(self):
        for name, value in self.scope.get('headers', []):
            if name == b'cookie':
                cookies = {}
                for part in value.decode('latin-1').split(';'):
                    if '=' in part:
                        key, val = part.split('=', 1)
                        cookies[key.strip()] = val.strip()
                return cookies.get('access_token')
        return None

    def _query_token(self):
        try:
            from urllib.parse import parse_qs
            params = parse_qs(self.scope.get('query_string', b'').decode('latin-1'))
            values = params.get('token', [])
            return values[0] if values else None
        except Exception:
            return None

    @database_sync_to_async
    def _authenticate_from_cookie(self):
        from django.contrib.auth import get_user_model
        from apps.accounts.models import UserDeviceSession

        token = self._cookie_token() or self._query_token()
        if not token:
            return None
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            return None
        if payload.get('token_type') != 'access':
            return None

        user_id = payload.get('user_id')
        if not user_id:
            return None

        session_id = payload.get('session_id')
        if session_id:
            session = UserDeviceSession.objects.select_related('user').filter(
                id=session_id,
                user_id=user_id,
                is_revoked=False,
                user__is_active=True
            ).first()
            return session.user if session else None

        user_model = get_user_model()
        try:
            return user_model.objects.get(id=user_id, is_active=True)
        except user_model.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_owned_asset(self, asset_id, user):
        try:
            return InfrastructureAsset.objects.get(id=asset_id, user=user)
        except (InfrastructureAsset.DoesNotExist, ValueError, TypeError):
            return None

    @database_sync_to_async
    def _log(self, action, description):
        try:
            log_activity(self.user, 'WORKSPACE', action, description)
        except Exception:
            pass
