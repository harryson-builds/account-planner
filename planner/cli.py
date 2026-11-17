"""Launch the Streamlit app bound to localhost."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    app = Path(__file__).resolve().parent / "app.py"
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app),
                "--server.address",
                "127.0.0.1",
                "--server.port",
                "8517",
                "--browser.gatherUsageStats",
                "false",
            ]
        )
    )


if __name__ == "__main__":
    main()
