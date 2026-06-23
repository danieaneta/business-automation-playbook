"""CLI entry point — runs the ticket classify -> route -> SLA pipeline on the sample data.

    python run.py

Keeps imports working whether you run from the blueprint folder or the repo root by putting
both the blueprint dir (for the `src` package) and the repo root (for `shared`) on the path.
"""

import sys
from pathlib import Path

BLUEPRINT_DIR = Path(__file__).resolve().parent
REPO_ROOT = BLUEPRINT_DIR.parent
for p in (str(BLUEPRINT_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.pipeline import main  # noqa: E402

if __name__ == "__main__":
    main()
