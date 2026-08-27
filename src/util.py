"""Small cross-cutting helpers."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def load_env(path: str | Path = ".env") -> None:
    """Load ``KEY=VALUE`` pairs from a ``.env`` file into ``os.environ`` (no overwrite).

    Deliberately dependency-free (no python-dotenv required) and safe: existing env vars
    win, comments/blank lines are ignored. Secrets live only in the git-ignored ``.env``.
    """
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def enable_utf8_stdout() -> None:
    """Best-effort switch of stdout/stderr to UTF-8.

    Windows consoles default to cp1252, which cannot encode characters like ₹, τ or →
    and will raise ``UnicodeEncodeError`` mid-print. Reconfiguring to UTF-8 keeps our
    CLIs robust across terminals, pipes, and CI.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
