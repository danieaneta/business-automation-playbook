"""A tiny idempotent JSON-backed store.

Stands in for a real CRM / database in the demos. The point it demonstrates is **idempotency**:
re-running a pipeline must not create duplicate records. Every upsert is keyed, so processing
the same lead twice updates one record instead of creating two.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JsonStore:
    """Key-addressed record store persisted to a JSON file.

    Not concurrent-safe — it exists to make the demos runnable and to prove idempotent upserts,
    not to be a production datastore.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._records: Dict[str, Dict[str, Any]] = {}
        if self.path.exists():
            self._records = json.loads(self.path.read_text(encoding="utf-8"))

    def upsert(self, key: str, record: Dict[str, Any]) -> bool:
        """Insert or update ``record`` under ``key``. Returns True if newly created."""
        is_new = key not in self._records
        self._records[key] = record
        self._flush()
        return is_new

    def get(self, key: str) -> Dict[str, Any] | None:
        return self._records.get(key)

    def all(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._records, indent=2, default=str), encoding="utf-8")
