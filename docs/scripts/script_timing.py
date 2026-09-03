"""Measure the pitch script's runtime from its own word counts.

The pitch is capped at five minutes, so "is it short enough?" is a question with an
answer rather than a feeling. This reads the narration out of ``docs/pitch-script.md``
— every ``> `` blockquote line under ``# THE SCRIPT`` — and prints per-beat and total
runtime at a few speaking rates.

Run it after any edit to the script::

    python docs/scripts/script_timing.py

Exits non-zero if the total runs past five minutes at the target rate, so a script that
has quietly grown fails loudly instead of on camera.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "pitch-script.md"

#: Rehearsed technical delivery. Slower than conversation because the numbers need room.
TARGET_WPM = 150
#: The submission's hard cap.
LIMIT_SECONDS = 5 * 60


def beats(markdown: str) -> list[tuple[str, int]]:
    """Return ``(beat title, spoken word count)`` for each beat of the script."""
    body = markdown.split("# THE SCRIPT", 1)[1].split("## If you are running long", 1)[0]
    out: list[tuple[str, int]] = []
    for chunk in re.split(r"\n## ", body):
        title = chunk.split("\n", 1)[0].strip()
        spoken = " ".join(line[2:] for line in chunk.splitlines() if line.startswith("> "))
        # Markdown emphasis and inline code are read aloud as plain words.
        words = len(re.sub(r"[*`_]", "", spoken).split())
        if words:
            out.append((title, words))
    return out


def fmt(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def main() -> int:
    if not SCRIPT.exists():
        print(f"no script at {SCRIPT}", file=sys.stderr)
        return 2

    measured = beats(SCRIPT.read_text(encoding="utf-8"))
    total = sum(words for _, words in measured)

    print(f"{'beat':<52} {'words':>6} {'@' + str(TARGET_WPM) + 'wpm':>10}")
    print("-" * 70)
    for title, words in measured:
        label = re.sub(r"[^\x20-\x7e]", "", title).strip(" ·")[:50]
        print(f"{label:<52} {words:>6} {fmt(words / TARGET_WPM * 60):>10}")
    print("-" * 70)
    print(f"{'TOTAL':<52} {total:>6} {fmt(total / TARGET_WPM * 60):>10}")
    print()
    for wpm in (140, 150, 160, 170):
        mark = "  <- target" if wpm == TARGET_WPM else ""
        print(f"  at {wpm} wpm -> {fmt(total / wpm * 60)}{mark}")

    seconds = total / TARGET_WPM * 60
    if seconds > LIMIT_SECONDS:
        over = seconds - LIMIT_SECONDS
        print(f"\nOVER by {fmt(over)} at {TARGET_WPM} wpm — use the cut list in the script.")
        return 1
    print(f"\nUnder the five-minute cap by {fmt(LIMIT_SECONDS - seconds)} at {TARGET_WPM} wpm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
