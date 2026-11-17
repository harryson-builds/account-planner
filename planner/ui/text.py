"""Escape untrusted CSV fields before Streamlit markdown."""

from __future__ import annotations

import html
import re

_MD = re.compile(r"([\\`*_{}\[\]()#+\-.!|])")


def plain(value: object) -> str:
    text = "" if value is None else str(value)
    return html.escape(_MD.sub(r"\\\1", text), quote=True)
