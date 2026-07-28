"""The console title must track the stage the CLI is actually in.

`idt guideme` sets the title to "IDT - Setup Wizard" in main()'s dispatcher,
then calls cmd_describe() directly. cmd_describe sets its own title, but only
after the queue is built -- i.e. after video extraction and the existence check
have finished. On a large library that is many minutes during which the window
still reads "Setup Wizard", which looks like a hung wizard rather than work in
progress.

Observed 2026-07-28: a 30-video / 143-still run sat on "Setup Wizard" for 17+
minutes of frame extraction while producing zero descriptions, with the worker
process pinned at ~150% CPU.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MAIN = (_ROOT / "cli" / "main.py").read_text(encoding="utf-8", errors="replace")


def _fn(name: str) -> str:
    """Source of one top-level function."""
    m = re.search(rf"^def {name}\(.*?(?=^def )", _MAIN, re.MULTILINE | re.DOTALL)
    assert m, f"could not locate {name} in cli/main.py"
    return m.group(0)


def test_extraction_loop_updates_the_title():
    """Extraction is the longest pre-describe stage; it must report progress."""
    body = _fn("_extract_videos_into_workspace")
    assert "_set_console_title" in body, (
        "video extraction runs for minutes without touching the title, so a "
        "guideme run reads 'Setup Wizard' the whole time"
    )
    # Inside the per-video loop, not only once before it.
    loop = body.split("for ", 1)[-1]
    assert "_set_console_title" in loop, (
        "the title should advance per video, not just once before the loop"
    )


def test_extraction_title_names_the_stage_and_counts():
    body = _fn("_extract_videos_into_workspace")
    assert "Extracting Video Frames" in body
    assert re.search(r"\{_?n\w*\} of \{len\(videos\)\}", body), (
        "extraction title should show progress through the video list"
    )


def test_describe_marks_the_preparing_stage():
    """The existence check walks the library; on a share that is slow."""
    body = _fn("cmd_describe")
    assert "IDT - Preparing" in body, (
        "the gap between extraction and the first description left the previous "
        "stage's title up"
    )
    # It must come before the describing title, or it would overwrite progress.
    assert body.index("IDT - Preparing") < body.index("IDT - Describing Images")


def test_describe_reports_progress_and_completion():
    body = _fn("cmd_describe")
    assert "Describing Images (0%, 0 of" in body
    assert "Image Description Complete" in body


def test_every_long_stage_sets_a_title():
    """Guard against a new long-running stage shipping without one."""
    for fn_name, marker in (
        ("_extract_videos_into_workspace", "Extracting Video Frames"),
        ("cmd_describe", "Describing Images"),
    ):
        assert marker in _fn(fn_name), f"{fn_name} should set a '{marker}' title"


def test_guideme_still_gets_its_own_startup_title():
    """The wizard title is correct while the wizard is actually prompting."""
    assert '"guideme":  "IDT - Setup Wizard"' in _MAIN or \
           '"guideme": "IDT - Setup Wizard"' in _MAIN
