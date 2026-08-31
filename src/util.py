"""Small cross-cutting helpers."""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any


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


def to_jsonable(obj: Any) -> Any:
    """Recursively convert numpy/pandas values into strict-JSON-safe Python.

    Two things bite here and both produce a 500 at the API boundary rather than a helpful
    error: numpy scalars are not JSON types, and ``NaN``/``inf`` are not valid JSON at all
    (Python's ``json`` emits them anyway unless ``allow_nan=False``, and strict clients
    reject the result). Non-finite values become ``None`` — a missing number, which is what
    they mean: an undefined ratio, an AUC on a degenerate slice, an empty bucket.

    Keys beginning with ``_`` are dropped: by convention those hold heavy intermediates
    (the cost-curve frame) that belong in plots, not in payloads.
    """
    import numpy as np
    import pandas as pd

    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return [to_jsonable(r) for r in obj.to_dict(orient="records")]
    if isinstance(obj, pd.Series):
        return to_jsonable(obj.to_dict())
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if obj is pd.NaT or (obj is not None and obj is pd.NA):
        return None
    return obj
