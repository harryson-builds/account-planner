#!/usr/bin/env python3
"""Copy the GitHub-safe planner tree into an empty directory (no git history)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

KEEP_FILES = [
    "pyproject.toml",
    ".gitignore",
    "README.md",
    ".streamlit/config.toml",
    ".github/workflows/test.yml",
]

KEEP_DIRS = [
    "planner",
]

SKIP_DIR_NAMES = {"__pycache__", ".pytest_cache", "var"}


def copy_tree(src: Path, dest: Path) -> None:
    if src.name in SKIP_DIR_NAMES:
        return
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            copy_tree(child, dest / child.name)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python3 planner/scripts/pack_github.py /path/to/empty-dir")
        raise SystemExit(2)
    dest = Path(sys.argv[1]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        print(f"refusing to write into non-empty directory {dest}")
        raise SystemExit(1)
    for rel in KEEP_FILES:
        src = ROOT / rel
        if src.exists():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    for rel in KEEP_DIRS:
        copy_tree(ROOT / rel, dest / rel)
    print(f"packed {dest}")
    print("Next: cd there, git init, confirm git log is a single commit with no employer or token files, then push a NEW empty GitHub repo.")


if __name__ == "__main__":
    main()
