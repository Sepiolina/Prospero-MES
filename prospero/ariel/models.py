from datetime import datetime
import json
import logging
from typing import Any, Dict, Optional
from sqlalchemy import String, DateTime, JSON, Integer, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base, engine
from .encryption import encryption_manager

logger = logging.getLogger(__name__)


class EncryptedJSON(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect) -> Optional[str]:
        if value is None:
            return None
        serialized = json.dumps(value, default=str)
        return encryption_manager.encrypt(serialized)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[Any]:
        if value is None:
            return None
        try:
            decrypted = encryption_manager.decrypt(value)
        except Exception:
            logger.error("Could not decrypt stored value; returning None.")
            return None
        return json.loads(decrypted)


class EncryptedString(TypeDecorator):
    """Stores a plain string, encrypted at rest."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return encryption_manager.encrypt(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        try:
            return encryption_manager.decrypt(value)
        except Exception:
            logger.error("Could not decrypt stored value; returning None.")
            return None


class DynamicStore(Base):
    """A universal key-value store using namespaces.

    `namespace`/`key` are left unencrypted (they're structural identifiers
    used for primary-key lookups); `value` is encrypted at rest.
    """

    __tablename__ = "dynamic_store"

    namespace: Mapped[str] = mapped_column(String(50), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(EncryptedJSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class DynamicLog(Base):
    """A universal append-only time-series log.

    `category`/`level` stay unencrypted (used for indexed filtering);
    `message` and `meta` are encrypted at rest since logs commonly end up
    containing sensitive details.
    """

    __tablename__ = "dynamic_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    category: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(10), index=True)
    message: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(EncryptedJSON, nullable=True)


Base.metadata.create_all(engine)
