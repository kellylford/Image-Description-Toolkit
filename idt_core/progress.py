"""
Progress reporting designed to be heard, not seen.

Screen readers read the raw text of terminal output. That means:
  - No ANSI escape sequences (no colors, no cursor movement, no spinners)
  - No unicode art that reads as noise ("⠏ processing…" → "weird character processing")
  - Numbers and words that make sense when spoken: "3 of 47  64%  morning.jpg: done"
  - Errors on their own line so the reader announces them clearly

quiet=True silences everything except fatal errors — good for piping to other tools.
"""
from __future__ import annotations

import sys
from typing import Optional, TextIO


class Progress:
    def __init__(self, total: int, quiet: bool = False, out: TextIO = sys.stdout):
        self.total = total
        self.current = 0
        self.quiet = quiet
        self._out = out

    def start(self, label: str = "") -> None:
        if self.quiet:
            return
        msg = f"Starting: {self.total} image{'s' if self.total != 1 else ''} to describe"
        if label:
            msg += f"  ({label})"
        print(msg, file=self._out, flush=True)

    def update(self, name: str, success: bool = True, error: Optional[str] = None) -> None:
        self.current += 1
        if self.quiet:
            return
        pct = int(self.current / self.total * 100) if self.total else 0
        status = "done" if success else "error"
        print(f"{self.current} of {self.total}  {pct}%  {name}: {status}", file=self._out, flush=True)
        if not success and error:
            print(f"  Error: {error}", file=self._out, flush=True)

    def skip(self, name: str, reason: str = "") -> None:
        self.current += 1
        if self.quiet:
            return
        msg = f"{self.current} of {self.total}  {name}: skipped"
        if reason:
            msg += f" ({reason})"
        print(msg, file=self._out, flush=True)

    def message(self, text: str) -> None:
        if not self.quiet:
            print(text, file=self._out, flush=True)

    def summary(self, described: int, errors: int = 0, skipped: int = 0) -> None:
        if self.quiet:
            return
        parts = [f"{described} described"]
        if errors:
            parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        if skipped:
            parts.append(f"{skipped} skipped")
        print(f"\nDone. {', '.join(parts)}.", file=self._out, flush=True)
