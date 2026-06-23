"""
Per-run log files written inside the .idtw bundle's logs/ directory.

Both the CLI (via WorkspacePipeline) and the GUI (via BatchProcessingWorker)
call open_run_log() at the start of a describe run and close_run_log() at the
end.  The result is a per-run log file inside the bundle that you can read
after the fact or tail while it runs.

Format matches the old WorkflowLogger:  LEVEL - message - (timestamp)
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

_FMT = "%(levelname)s - %(message)s - (%(asctime)s)"
_DATE = "%Y-%m-%d %H:%M:%S"


def open_run_log(logs_dir: Path, *, label: str = "run") -> logging.Logger:
    """
    Create run_YYYYMMDD_HHMMSS.log in logs_dir and return a Logger.
    The caller is responsible for calling close_run_log() when the run ends.
    """
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"{label}_{stamp}.log"

    log = logging.getLogger(f"idt.run.{stamp}")
    log.setLevel(logging.DEBUG)
    log.propagate = False

    h = logging.FileHandler(str(log_path), encoding="utf-8")
    h.setLevel(logging.DEBUG)
    h.setFormatter(logging.Formatter(_FMT, datefmt=_DATE))
    log.addHandler(h)

    log.info(f"Log: {log_path}")
    return log


def close_run_log(log: logging.Logger) -> None:
    """Flush and close all file handlers on this logger."""
    for h in list(log.handlers):
        try:
            h.flush()
            h.close()
        except Exception:
            pass
        log.removeHandler(h)
