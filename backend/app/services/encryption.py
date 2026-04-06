"""Shared encryption helpers for API keys and tokens (Fernet symmetric encryption)."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key.

    Raises ValueError if the key is missing or invalid.
    """
    if not settings.encryption_key:
        raise ValueError(
            "ENCRYPTION_KEY is required for token/key encryption. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(settings.encryption_key.encode())
    except Exception as exc:
        raise ValueError(f"Invalid ENCRYPTION_KEY (must be a valid Fernet key): {exc}") from exc


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext string for storage. Returns a Fernet ciphertext string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored ciphertext string. Returns the plaintext."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt — ENCRYPTION_KEY may have changed") from exc
