"""
Encryption-at-rest support for Ariel.

Design notes
------------
- Encryption is applied at the *field* level (via SQLAlchemy TypeDecorators
  in models.py) rather than at the whole-database-file level (e.g. SQLCipher).
  This avoids a native-library dependency and keeps behavior portable, while
  still ensuring that sensitive payloads never touch disk in plaintext.
- `namespace` / `key` / `category` / `level` columns are intentionally left
  unencrypted because they are structural identifiers used for lookups and
  indexing (encrypting them would require deterministic/blind-index
  encryption, which is unnecessary here since they aren't expected to hold
  secrets). The actual payloads (`value`, `message`, `meta`) ARE encrypted.
- Key resolution order:
    1. `ARIEL_ENCRYPTION_KEY` env var (recommended for production; can be a
       comma-separated list of keys to support zero-downtime key rotation --
       the first key is used for new encryption, all keys are tried for
       decryption).
    2. A local key file (path from `ARIEL_KEY_PATH`, default
       `static/.ariel.key`), used if it already exists.
    3. If neither is present, a new key is generated and written to that
       file with `0600` permissions, and a loud warning is logged. This
       keeps local/dev usage frictionless without silently being insecure.
"""

import os
import stat
import logging
from pathlib import Path
from typing import List

from cryptography.fernet import Fernet, MultiFernet, InvalidToken

logger = logging.getLogger(__name__)

__all__ = ["EncryptionManager", "InvalidToken", "encryption_manager"]


class EncryptionManager:
    def __init__(
        self,
        env_var: str = "ARIEL_ENCRYPTION_KEY",
        key_path_env: str = "ARIEL_KEY_PATH",
        default_key_path: str = "static/.ariel.key",
    ):
        self._fernet = self._load(env_var, key_path_env, default_key_path)

    # -- key loading -------------------------------------------------
    def _load(
        self, env_var: str, key_path_env: str, default_key_path: str
    ) -> MultiFernet:
        raw = os.environ.get(env_var)
        if raw:
            keys = [k.strip() for k in raw.split(",") if k.strip()]
            logger.info(
                "Ariel encryption key(s) loaded from %s environment variable.", env_var
            )
            return self._build(keys)

        key_path = Path(os.environ.get(key_path_env, default_key_path))

        if key_path.exists():
            key_bytes = key_path.read_bytes().strip()
            logger.warning(
                "Ariel encryption key loaded from local file '%s'. For production "
                "deployments, set the %s environment variable instead and store the "
                "key in a proper secrets manager (Vault, AWS/GCP secret manager, etc.).",
                key_path,
                env_var,
            )
            return self._build([key_bytes.decode()])

        # No key anywhere -- generate one for dev convenience, but be loud about it.
        key_path.parent.mkdir(parents=True, exist_ok=True)
        new_key = Fernet.generate_key()
        key_path.write_bytes(new_key)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600, owner read/write only
        logger.warning(
            "No Ariel encryption key found. Generated a new one at '%s' (permissions "
            "set to 600). BACK THIS FILE UP SECURELY -- losing it means all encrypted "
            "data becomes permanently unreadable. Do not commit it to version control. "
            "For production, set %s explicitly instead of relying on this file.",
            key_path,
            env_var,
        )
        return self._build([new_key.decode()])

    @staticmethod
    def _build(keys: List[str]) -> MultiFernet:
        fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
        return MultiFernet(fernets)

    # -- public API ----------------------------------------------------
    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            logger.error(
                "Failed to decrypt an Ariel-stored value: token is invalid or was "
                "encrypted with a different key than the ones currently configured."
            )
            raise

    def rotate_reencrypt(self, ciphertext: str) -> str:
        """Decrypt with any configured key, re-encrypt with the primary (first) key.
        Useful for background key-rotation jobs."""
        plaintext = self.decrypt(ciphertext)
        return self.encrypt(plaintext)


# Module-level singleton used by the custom SQLAlchemy types in models.py
encryption_manager = EncryptionManager()
