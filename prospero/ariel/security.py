"""
Reusable security building blocks, exposed as `ariel.security` so consumers
of this module can apply the same best practices elsewhere in their app
without reinventing them.
"""

import hmac
import hashlib
import re
import secrets
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_\-.:]+$")

__all__ = [
    "generate_key",
    "generate_token",
    "validate_identifier",
    "secure_compare",
    "mask_secret",
    "hash_password",
    "verify_password",
]


def generate_key() -> str:
    """Generate a new Fernet-compatible key, e.g. for ARIEL_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode()


def generate_token(length: int = 32) -> str:
    """Cryptographically secure random URL-safe token (API keys, CSRF tokens, etc.)."""
    return secrets.token_urlsafe(length)


def validate_identifier(
    value: str, field_name: str = "identifier", max_length: int = 100
) -> str:
    """Restrict namespace/key-style identifiers to a safe character set and length.

    Raises ValueError on anything suspicious. This is defense-in-depth --
    SQLAlchemy already parameterizes queries so this isn't preventing SQL
    injection, but it stops malformed/oversized/control-character input from
    ever reaching the database.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds max length of {max_length}")
    if not _IDENTIFIER_RE.match(value):
        raise ValueError(
            f"{field_name} contains invalid characters; only letters, digits, "
            "'_', '-', '.', ':' are allowed"
        )
    return value


def secure_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison -- use for comparing tokens/API keys/HMACs."""
    return hmac.compare_digest(a.encode(), b.encode())


def mask_secret(value: str, visible: int = 4) -> str:
    """Mask a secret for safe logging, e.g. 'sk_live_abcd1234' -> 'sk_l********1234'."""
    if not value:
        return value
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * (len(value) - visible * 2)}{value[-visible:]}"


def hash_password(password: str, iterations: int = 390_000) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 (no extra native dependency).
    Returns a self-describing string: 'pbkdf2_sha256$iterations$salt$hash'."""
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash produced by hash_password()."""
    try:
        algo, iterations_s, salt_hex, hash_hex = hashed.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(derived, expected)
