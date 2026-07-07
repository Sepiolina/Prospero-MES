from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import String, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base, engine


class DynamicStore(Base):
    """A universal key-value store using namespaces."""

    __tablename__ = "dynamic_store"

    namespace: Mapped[str] = mapped_column(String(50), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class DynamicLog(Base):
    """A universal append-only time-series log."""

    __tablename__ = "dynamic_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    category: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(10), index=True)
    message: Mapped[str] = mapped_column(String(255))
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)


Base.metadata.create_all(engine)
