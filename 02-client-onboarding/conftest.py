"""Pytest path setup for this blueprint.

Puts the blueprint dir (for the `src` package) and the repo root (for `shared`) on sys.path so
tests can `from src.engine import ...` and `from shared.retry import ...`.
"""

import sys
from pathlib import Path

BLUEPRINT_DIR = Path(__file__).resolve().parent
REPO_ROOT = BLUEPRINT_DIR.parent
for p in (str(BLUEPRINT_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
