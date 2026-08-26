"""Small cross-cutting helpers."""
from __future__ import annotations

import sys


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
