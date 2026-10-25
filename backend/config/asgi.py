"""
ASGI config for config project.

Routes HTTP to Django and WebSocket traffic to the interactive SSH terminal
consumer (daphne + channels).

No AllowedHostsOriginValidator: in production the app is reached through a
Cloudflare Pages reverse proxy whose Origin header (the Pages domain) never
matches the backend container Host. The terminal consumer authenticates the
JWT access token itself and enforces per-asset ownership (BOLA), which is
the real security boundary for this route.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import re_path  # noqa: E402

from apps.workspace.consumers import SshTerminalConsumer  # noqa: E402

UUID_RE = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': URLRouter([
        # Leading/trailing slash optional: proxies may strip or add them.
        re_path(rf'^/?ws/workspace/ssh/(?P<asset_id>{UUID_RE})/?$', SshTerminalConsumer.as_asgi()),
    ]),
})
