# Python Conventions

- **Version:** Python 3.10+.
- **Formatting:** Black (line length **100**), isort (profile = black). Run before every commit.
- **Types:** type hints on all function signatures and public returns.
- **Strings:** f-strings, not `%` or `.format()`.
- **Reproducibility:** every stochastic step takes an explicit `seed`/`random_state`. No unseeded `np.random`/`random`. This is graded.
- **Config:** read paths/keys from `.env` via `python-dotenv`; never hardcode secrets. Never commit `.env`.
- **Structure:** feature transforms are **pure functions** (no hidden global state) so offline == online.
- **Imports:** absolute imports within `src` (e.g., `from src.features import build_features`).
- **Docstrings:** one-line summary for every module/function; note units (₹, days, km) and whether a value is available at prediction time.
- **Errors:** fail loudly on data-schema surprises; never silently drop rows without logging a count.
- **Commits:** small; prefix `[data|features|model|rules|agent|rag|api|web|docs] short description`.
