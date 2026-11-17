"""Repository paths. Import this first from Streamlit pages so `planner` is on sys.path."""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEMO_DIR = PACKAGE_DIR / "demo"
TEMPLATE_DIR = PACKAGE_DIR / "templates"
SCENARIO_DIR = PACKAGE_DIR / "config" / "scenarios"
VAR_DIR = REPO_ROOT / "var"
DEFAULT_DB = VAR_DIR / "planner.sqlite"
EXPORT_DIR = REPO_ROOT / "exports"


def ensure_runtime_dirs() -> None:
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
