import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when token encryption or decryption fails."""
    pass


def _get_fernet() -> Fernet:
    """
    Derives a deterministic 32-byte URL-safe base64 key from SECRET_KEY.
    """
    raw_key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    urlsafe_key = base64.urlsafe_b64encode(raw_key)
    return Fernet(urlsafe_key)


def encrypt_token(plaintext: str) -> str:
    """
    Encrypts a plaintext secret/token at rest using Fernet.
    Never returns plaintext on failure.
    """
    if not plaintext:
        return ''
    try:
        f = _get_fernet()
        return f.encrypt(plaintext.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encrypting secret: {e}")
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypts an encrypted secret/token.
    Never returns ciphertext on failure.
    """
    if not ciphertext:
        return ''
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except InvalidToken as e:
        logger.error(f"Invalid token during decryption: {e}")
        raise EncryptionError(f"Decryption failed: {e}") from e
    except Exception as e:
        logger.error(f"Error decrypting secret: {e}")
        raise EncryptionError(f"Decryption failed: {e}") from e
