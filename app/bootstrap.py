"""
Make the repo root importable regardless of which script Streamlit runs.

Streamlit's multipage app runs each ``app/pages/*.py`` file as its own
top-level script, so plain relative imports of the ``credit``/``data``/
``database`` packages don't resolve unless the repo root is on ``sys.path``.
Every entry script (``streamlit_app.py`` and each page) calls
``ensure_repo_root()`` as its very first import-time action, before
importing anything from this project.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "credit").is_dir() and (parent / "database").is_dir():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return parent
    raise RuntimeError("Could not locate the credit-monitor repo root from app/bootstrap.py")
