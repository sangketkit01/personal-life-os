import datetime
import hashlib
import jwt
import uuid
from django.conf import settings


def hash_token(token: str) -> str:
    """Generate SHA256 hash for database storage instead of storing raw tokens."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def get_client_ip(request) -> str:
    """Extract real client IP address from request headers, strictly validated."""
    import ipaddress
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        raw_ip = x_forwarded_for.split(',')[0].strip()
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip
        except ValueError:
            pass
    remote_addr = request.META.get('REMOTE_ADDR', '')
    if remote_addr:
        try:
            ipaddress.ip_address(remote_addr)
            return remote_addr
        except ValueError:
            pass
    return '127.0.0.1'


def get_device_name(request) -> str:
    """Parse device name and browser info from User-Agent."""
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown Device')
    ua_lower = user_agent.lower()
    
    os_name = "Desktop"
    if "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"

    browser = "Browser"
    if "edg" in ua_lower:
        browser = "Edge"
    elif "chrome" in ua_lower:
        browser = "Chrome"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari"
    elif "firefox" in ua_lower:
        browser = "Firefox"

    return f"{browser} on {os_name}"


def generate_access_token(user) -> str:
    """Create 15-minute Access Token."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'token_type': 'access',
        'user_id': str(user.id),
        'username': user.username,
        'iat': now,
        'exp': now + datetime.timedelta(minutes=15)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user, session_id: uuid.UUID) -> str:
    """Create 7-day Refresh Token with unique JTI."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'token_type': 'refresh',
        'jti': str(uuid.uuid4()),
        'user_id': str(user.id),
        'session_id': str(session_id),
        'iat': now,
        'exp': now + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decode and validate JWT token claims."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
