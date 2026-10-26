"""
ASGI config for config project.

Routes HTTP to Django and WebSocket traffic to the interactive SSH terminal
consumer (daphne + channels).
"""
import os
from urllib.parse import urlparse

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from channels.security.websocket import WebsocketDenier  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.conf import settings  # noqa: E402
from django.urls import re_path  # noqa: E402

from apps.workspace.consumers import SshTerminalConsumer  # noqa: E402

UUID_RE = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'


def _get_allowed_ws_origins():
    origins = set()
    for o in getattr(settings, 'CORS_ALLOWED_ORIGINS', []):
        origins.add(o.lower().rstrip('/'))
    for o in getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
        origins.add(o.lower().rstrip('/'))

    for port in ('5173', '3000', '8000', '80', '443'):
        origins.add(f"http://localhost:{port}")
        origins.add(f"http://127.0.0.1:{port}")
        origins.add(f"https://localhost:{port}")
        origins.add(f"https://127.0.0.1:{port}")
        origins.add(f"ws://localhost:{port}")
        origins.add(f"ws://127.0.0.1:{port}")
        origins.add(f"wss://localhost:{port}")
        origins.add(f"wss://127.0.0.1:{port}")

    env_ws = os.getenv('WS_ALLOWED_ORIGINS', '')
    if env_ws:
        for o in env_ws.split(','):
            if o.strip():
                origins.add(o.strip().lower().rstrip('/'))
    return origins


class WebSocketOriginValidatorMiddleware:
    """
    Validates WebSocket Origin header against allowed frontend origins.
    Rejects unauthorized external origins to prevent Cross-Site WebSocket Hijacking (CSWSH).
    Allows non-browser clients where Origin is omitted.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get('type') == 'websocket':
            origin = None
            for name, value in scope.get('headers', []):
                if name.lower() == b'origin':
                    try:
                        origin = value.decode('latin-1').strip().lower().rstrip('/')
                    except UnicodeDecodeError:
                        pass
                    break

            if origin:
                allowed_origins = _get_allowed_ws_origins()
                parsed = urlparse(origin)
                normalized_origin = f"{parsed.scheme}://{parsed.netloc}".lower()
                target_host = (parsed.hostname or '').lower()
                allowed_hosts = [h.lower() for h in getattr(settings, 'ALLOWED_HOSTS', []) if h != '*']

                is_allowed = (
                    origin in allowed_origins
                    or normalized_origin in allowed_origins
                    or (target_host and target_host in allowed_hosts)
                )

                if not is_allowed:
                    denier = WebsocketDenier()
                    return await denier(scope, receive, send)

        return await self.inner(scope, receive, send)


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': WebSocketOriginValidatorMiddleware(
        URLRouter([
            # Leading/trailing slash optional: proxies may strip or add them.
            re_path(rf'^/?ws/workspace/ssh/(?P<asset_id>{UUID_RE})/?$', SshTerminalConsumer.as_asgi()),
        ])
    ),
})
