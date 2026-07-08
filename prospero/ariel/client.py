import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from .database import SessionLocal
from .models import DynamicStore, DynamicLog

logger = logging.getLogger(__name__)


class ArielClient:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def set(self, namespace: str, key: str, value: Any) -> bool:
        try:
            with self.session_factory.begin() as session:
                stmt = insert(DynamicStore).values(
                    namespace=namespace, key=key, value=value
                )

                # Native SQLite Upsert prevents double-querying the database
                do_update_stmt = stmt.on_conflict_do_update(
                    index_elements=["namespace", "key"],
                    set_=dict(value=stmt.excluded.value),
                )
                session.execute(do_update_stmt)
                return True
        except SQLAlchemyError as e:
            logger.error(f"Database fault during 'set': {e}")
            return False

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        try:
            with self.session_factory() as session:
                record = session.get(DynamicStore, (namespace, key))
                return record.value if record else default
        except SQLAlchemyError as e:
            logger.error(f"Database fault during 'get': {e}")
            return default

    def delete(self, namespace: str, key: str) -> bool:
        try:
            with self.session_factory.begin() as session:
                record = session.get(DynamicStore, (namespace, key))
                if record:
                    session.delete(record)
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Database fault during 'delete': {e}")
            return False

    def log(
        self,
        category: str,
        level: str,
        message: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            with self.session_factory.begin() as session:
                new_log = DynamicLog(
                    category=category, level=level, message=message, meta=meta
                )
                session.add(new_log)
                return True
        except SQLAlchemyError as e:
            logger.error(f"Database fault during 'log': {e}")
            return False

    def log_batch(self, logs_data: List[Dict[str, Any]]) -> bool:
        if not logs_data:
            return True

        try:
            with self.session_factory.begin() as session:
                session.execute(insert(DynamicLog), logs_data)
                return True
        except SQLAlchemyError as e:
            logger.error(f"Database fault during 'log_batch': {e}")
            return False
