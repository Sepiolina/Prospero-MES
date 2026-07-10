import time
import threading
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["InMemoryStore", "remember"]


class InMemoryStore:
    def __init__(self):
        self._data: Dict[Tuple[str, str], Tuple[Any, Optional[float]]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def set(
        self, namespace: str, key: str, value: Any, ttl: Optional[float] = None
    ) -> bool:
        """Store a value. `ttl` is optional seconds-until-expiry."""
        expires_at = self._now() + ttl if ttl is not None else None
        with self._lock:
            self._data[(namespace, key)] = (value, expires_at)
        return True

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._data.get((namespace, key))
            if entry is None:
                return default
            value, expires_at = entry
            if expires_at is not None and self._now() >= expires_at:
                del self._data[(namespace, key)]
                return default
            return value

    def delete(self, namespace: str, key: str) -> bool:
        with self._lock:
            return self._data.pop((namespace, key), None) is not None

    def clear(self, namespace: Optional[str] = None) -> int:
        """Clear everything, or everything within one namespace. Returns count removed."""
        with self._lock:
            if namespace is None:
                count = len(self._data)
                self._data.clear()
                return count
            to_remove = [k for k in self._data if k[0] == namespace]
            for k in to_remove:
                del self._data[k]
            return len(to_remove)

    def cleanup(self) -> int:
        """Manually purge expired entries (expiry is normally lazy, on access).
        Call this periodically if you have many TTL'd keys that are rarely read."""
        now = self._now()
        with self._lock:
            expired = [
                k
                for k, (_, exp) in self._data.items()
                if exp is not None and now >= exp
            ]
            for k in expired:
                del self._data[k]
            return len(expired)

    def keys(self, namespace: Optional[str] = None) -> List[Tuple[str, str]]:
        with self._lock:
            if namespace is None:
                return list(self._data.keys())
            return [k for k in self._data if k[0] == namespace]

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


# Process-wide default instance, exposed as `ariel.remember`
remember = InMemoryStore()
