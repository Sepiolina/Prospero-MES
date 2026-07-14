# ariel/encryption.py
import os
import logging
import uuid
import base64
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

import keyring
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

logger = logging.getLogger(__name__)

__all__ = ["EncryptionManager", "InvalidToken", "encryption_manager"]


def _unscramble(scrambled_b64: str, key: int = 0x5A) -> str:
    decoded_bytes = base64.b64decode(scrambled_b64)
    return "".join(chr(b ^ key) for b in decoded_bytes)


SERVICE_NAME: str = _unscramble("KzAnJiY6KyMmKy8tJQ==")
ACCOUNT_NAME: str = _unscramble("DiY0KTA4YTMvJyY6MTA2OyVfJQ==")


def get_robust_machine_id() -> str:
    try:
        if sys.platform == "win32":
            cmd = ["wmic", "csproduct", "get", "uuid"]
            output = subprocess.check_output(cmd).decode()
            return output.split("\n")[1].strip()
        elif sys.platform == "darwin":
            cmd = ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]
            output = subprocess.check_output(cmd).decode()
            for line in output.split("\n"):
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2].strip()
        else:
            for path in [
                "/sys/class/dmi/id/product_uuid",
                "/etc/machine-id",
                "/proc/cpuinfo",
            ]:
                p = Path(path)
                if p.exists():
                    if "cpuinfo" in path:
                        for line in p.read_text().split("\n"):
                            if "Serial" in line:
                                return line.split(":")[-1].strip()
                    else:
                        return p.read_text().strip()
    except Exception:
        pass

    return str(uuid.getnode())


class EncryptionManager:
    def __init__(
        self,
        env_var: str = "ARIEL_ENCRYPTION_KEY",
        fallback_key_path: str = "static/.ariel.key-fallback",
    ) -> None:
        self._fernet: MultiFernet = self._load(env_var, fallback_key_path)

    def _load(self, env_var: str, fallback_key_path: str) -> MultiFernet:
        raw_env: Optional[str] = os.environ.get(env_var)
        if raw_env:
            keys: List[str] = [k.strip() for k in raw_env.split(",") if k.strip()]
            logger.info("Ariel encryption keys loaded from environment variable.")
            return self._build(keys)

        try:
            stored_key: Optional[str] = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
            if stored_key:
                logger.info(
                    "Encryption key successfully retrieved from OS secure storage."
                )
                return self._build([stored_key])
        except Exception as e:
            logger.warning("OS Secure Keyring unavailable, falling back: %s", e)
            stored_key = None

        path: Path = Path(fallback_key_path)
        machine_salt: bytes = get_robust_machine_id().encode()

        if path.exists():
            try:
                obfuscated_bytes: bytes = path.read_bytes()
                key_bytes: bytes = bytes(
                    b ^ machine_salt[i % len(machine_salt)]
                    for i, b in enumerate(obfuscated_bytes)
                )
                logger.warning("Loaded fallback machine-bound key file.")
                return self._build([key_bytes.decode().strip()])
            except Exception as e:
                logger.error("Failed to read fallback key file: %s", e)

        new_key_bytes: bytes = Fernet.generate_key()
        new_key_str: str = new_key_bytes.decode()

        try:
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, new_key_str)
            logger.info("Generated new key and saved to OS secure storage.")
        except Exception as e:
            logger.error("Could not write new key to OS Keyring: %s", e)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            obfuscated_bytes = bytes(
                b ^ machine_salt[i % len(machine_salt)]
                for i, b in enumerate(new_key_bytes)
            )
            path.write_bytes(obfuscated_bytes)

            if os.name == "posix":
                os.chmod(path, 0o600)  # Owner Read/Write only[cite: 1]

            logger.warning("Fallback machine-bound file created at '%s'.", path)
        except Exception as e:
            logger.critical("Critical security initialization failure: %s", e)

        return self._build([new_key_str])

    @staticmethod
    def _build(keys: List[str]) -> MultiFernet:
        fernets: List[Fernet] = [
            Fernet(k.encode() if isinstance(k, str) else k) for k in keys
        ]
        return MultiFernet(fernets)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            logger.error("Failed to decrypt value: Token is invalid or key mismatch.")
            raise

    def rotate_reencrypt(self, ciphertext: str) -> str:
        plaintext: str = self.decrypt(ciphertext)
        return self.encrypt(plaintext)


encryption_manager = EncryptionManager()
