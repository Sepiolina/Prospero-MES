from typing import Any, Dict, Optional
from .database import SessionLocal
from .models import DynamicStore, DynamicLog


class ArielClient:
    """The main interface for reading/writing state and logs."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def set(self, namespace: str, key: str, value: Any):
        with self.session_factory() as session:
            record = session.get(DynamicStore, (namespace, key))
            if record:
                record.value = value
            else:
                record = DynamicStore(namespace=namespace, key=key, value=value)
                session.add(record)
            session.commit()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self.session_factory() as session:
            record = session.get(DynamicStore, (namespace, key))
            return record.value if record else default

    def delete(self, namespace: str, key: str) -> bool:
        with self.session_factory() as session:
            record = session.get(DynamicStore, (namespace, key))
            if record:
                session.delete(record)
                session.commit()
                return True
            return False

    # --- LOGGING METHODS ---

    def log(
        self,
        category: str,
        level: str,
        message: str,
        meta: Optional[Dict[str, Any]] = None,
    ):
        """Append a new record to the telemetry log."""
        with self.session_factory() as session:
            new_log = DynamicLog(
                category=category, level=level, message=message, meta=meta
            )
            session.add(new_log)
            session.commit()
