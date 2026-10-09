"""
WorkspacePipeline stops a run when the provider has stopped working: ten images in a row
failing identically, or 25 in a row declined. Before this the CLI carried on through every
remaining image: a stuck Windows AI timed out on picture after picture, three minutes each,
with 10,700 still to go (10/7/2026).
"""
from pathlib import Path

import pytest

from idt_core.pipeline import (
    REFUSAL_STREAK, SAME_FAILURE_STREAK, RunOptions, WorkspacePipeline, normalise_failure_text,
)
from idt_core.providers.base import DescriptionResult
from idt_core.workspace import Workspace

pytestmark = pytest.mark.unit


class Declined(RuntimeError):
    per_image = True


class ScriptedProvider:
    """Each describe takes the next outcome: an exception to raise, or "ok"."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    provider_name = "scripted"
    model_name = "m"

    def describe(self, image_bytes, mime_type, prompt):
        self.calls += 1
        outcome = self.outcomes.pop(0) if self.outcomes else "ok"
        if isinstance(outcome, BaseException):
            raise outcome
        return DescriptionResult(text=f"described {self.calls}", provider="scripted", model="m")


def _workspace(tmp_path: Path, count: int) -> Workspace:
    from PIL import Image

    src = tmp_path / "Pics"
    src.mkdir()
    for n in range(count):
        Image.new("RGB", (8, 8), (n % 256, 0, 0)).save(src / f"{n:03}.jpg", "JPEG")
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)
    return ws


def _run(ws, provider):
    pipeline = WorkspacePipeline(ws, provider)
    events = list(pipeline.run(RunOptions(prompt_name="none", prompt_text="", extract_metadata=False)))
    return pipeline, events


def _timeout():
    return RuntimeError("Windows AI timed out: no description after 180 seconds.")


def test_ten_identical_failures_in_a_row_stop_the_run(tmp_path):
    ws = _workspace(tmp_path, 30)
    provider = ScriptedProvider([_timeout() for _ in range(30)])
    pipeline, events = _run(ws, provider)
    assert len(events) == SAME_FAILURE_STREAK == 10
    assert provider.calls == 10, "the other 20 images aren't tried"
    assert "10 pictures or videos in a row failed with the same error" in pipeline.halted
    assert "timed out" in pipeline.halted
    assert pipeline.not_tried == 20 and not pipeline.halted_by_refusals
    log = next((ws.path / "logs").glob("run_*.log")).read_text(encoding="utf-8")
    assert "run halted after 10 of 30 images" in log


def test_the_images_not_tried_are_described_by_the_next_run(tmp_path):
    ws = _workspace(tmp_path, 15)
    _run(ws, ScriptedProvider([_timeout() for _ in range(15)]))
    pipeline, events = _run(ws, ScriptedProvider([]))
    assert len(events) == 15 and all(e.success for e in events)
    assert pipeline.halted is None


def test_a_success_breaks_the_streak(tmp_path):
    ws = _workspace(tmp_path, 25)
    provider = ScriptedProvider([_timeout()] * 9 + ["ok"] + [_timeout()] * 9 + ["ok"] * 6)
    pipeline, events = _run(ws, provider)
    assert len(events) == 25 and pipeline.halted is None


def test_different_failures_dont_add_up(tmp_path):
    ws = _workspace(tmp_path, 20)
    outcomes = [RuntimeError(f"cannot read file {n}.jpg") for n in range(20)]
    pipeline, events = _run(ws, ScriptedProvider(outcomes))
    assert len(events) == 20 and pipeline.halted is None


def test_a_failure_on_the_last_image_is_not_called_a_halt(tmp_path):
    ws = _workspace(tmp_path, 10)
    pipeline, events = _run(ws, ScriptedProvider([_timeout() for _ in range(10)]))
    assert len(events) == 10
    assert pipeline.halted is None, "nothing was left to stop for"


def test_refusals_neither_count_nor_break_the_identical_failure_streak(tmp_path):
    ws = _workspace(tmp_path, 30)
    outcomes = [_timeout()] * 5 + [Declined("declined")] * 3 + [_timeout()] * 5 + ["ok"] * 17
    pipeline, events = _run(ws, ScriptedProvider(outcomes))
    assert len(events) == 13 and "same error" in pipeline.halted


def test_twenty_five_refusals_in_a_row_stop_the_run(tmp_path):
    ws = _workspace(tmp_path, 40)
    pipeline, events = _run(ws, ScriptedProvider([Declined(f"declined {n}") for n in range(40)]))
    assert len(events) == REFUSAL_STREAK == 25
    assert "scripted declined 25 images in a row" in pipeline.halted
    assert pipeline.halted_by_refusals and pipeline.not_tried == 15


def test_a_refusal_raised_from_another_error_counts_as_a_refusal(tmp_path):
    ws = _workspace(tmp_path, 30)

    def wrapped(n):
        try:
            raise Declined("declined")
        except Declined:
            try:
                raise RuntimeError(f"wrapper {n}")
            except RuntimeError as exc:
                return exc

    pipeline, events = _run(ws, ScriptedProvider([wrapped(n) for n in range(30)]))
    assert len(events) == 25 and "declined 25" in pipeline.halted


def test_object_addresses_and_request_ids_dont_make_failures_differ(tmp_path):
    a = "COMException 0x80004005 at <obj 0x7f12ab> request_id: abc123def"
    b = "COMException 0x80004005 at <obj 0x7f99cd> request_id: zzz999yyy"
    assert normalise_failure_text(a) == normalise_failure_text(b)
    assert normalise_failure_text("file req_0001.jpg") != normalise_failure_text("file req_0002.jpg")
    ws = _workspace(tmp_path, 12)
    outcomes = [RuntimeError(f"helper crashed at 0x{n:08x}") for n in range(12)]
    pipeline, events = _run(ws, ScriptedProvider(outcomes))
    assert len(events) == 10, "the addresses differ, the failure doesn't"


def test_the_same_message_from_different_error_types_isnt_the_same_failure(tmp_path):
    ws = _workspace(tmp_path, 12)
    outcomes = [RuntimeError("x") if n % 2 else ValueError("x") for n in range(12)]
    pipeline, events = _run(ws, ScriptedProvider(outcomes))
    assert len(events) == 12 and pipeline.halted is None


class SetupError(RuntimeError):
    setup = True


def test_a_setup_failure_stops_the_run_at_once(tmp_path):
    ws = _workspace(tmp_path, 5)
    pipeline, events = _run(ws, ScriptedProvider([SetupError("The Windows AI helper isn't installed.")]))
    assert len(events) == 1
    assert pipeline.halted == "The Windows AI helper isn't installed." and pipeline.not_tried == 4


def test_events_dont_keep_the_exception(tmp_path):
    """Its traceback would keep each failed image's bytes alive for a caller that keeps events."""
    ws = _workspace(tmp_path, 1)
    _, events = _run(ws, ScriptedProvider([_timeout()]))
    assert not hasattr(events[0], "exception")
    assert events[0].signature.startswith("RuntimeError: Windows AI timed out")


# ---------------------------------------------------------------------------
# What the command line says
# ---------------------------------------------------------------------------


def test_the_summary_says_stopped_and_counts_what_wasnt_tried():
    import io

    from idt_core.progress import Progress

    out = io.StringIO()
    Progress(total=30, out=out).summary(described=0, errors=10, not_tried=20)
    assert out.getvalue().strip() == "Stopped. 0 described, 10 errors, 20 not tried."
    out = io.StringIO()
    Progress(total=2, out=out).summary(described=2)
    assert out.getvalue().strip() == "Done. 2 described."


def _halted(tmp_path, outcomes, count):
    ws = _workspace(tmp_path, count)
    pipeline, _ = _run(ws, ScriptedProvider(outcomes))
    return ws, pipeline


def test_the_stop_message_names_the_command_that_carries_on(tmp_path, capsys):
    from cli.main import _report_halt

    ws, pipeline = _halted(tmp_path, [_timeout() for _ in range(12)], 12)
    _report_halt(pipeline, ws, redescribe=False)
    err = capsys.readouterr().err
    assert "Why it stopped: 10 pictures or videos in a row failed" in err
    assert f'run: idt describe "{ws.path}"' in err and "--redescribe" not in err


def test_after_a_redescribe_or_download_the_message_says_redescribe(tmp_path, capsys):
    from cli.main import _report_halt

    ws, pipeline = _halted(tmp_path, [_timeout() for _ in range(12)], 12)
    _report_halt(pipeline, ws, redescribe=True)
    err = capsys.readouterr().err
    assert f'idt describe "{ws.path}" --redescribe' in err
    assert "keep their earlier descriptions" in err


def test_watch_says_it_is_still_watching(tmp_path, capsys):
    from cli.main import _report_halt

    ws, pipeline = _halted(tmp_path, [_timeout() for _ in range(12)], 12)
    _report_halt(pipeline, ws, redescribe=False, watching=True)
    assert "Still watching for new images" in capsys.readouterr().err


def test_a_refusal_stop_says_the_same_prompt_will_be_declined_again(tmp_path, capsys):
    from cli.main import _report_halt

    ws, pipeline = _halted(tmp_path, [Declined("no") for _ in range(30)], 30)
    _report_halt(pipeline, ws, redescribe=False)
    assert "declined the same way" in capsys.readouterr().err


def test_a_long_failure_is_shortened_in_the_stop_message(tmp_path, capsys):
    from cli.main import _report_halt

    ws, pipeline = _halted(tmp_path, [RuntimeError("x" * 2000) for _ in range(12)], 12)
    _report_halt(pipeline, ws, redescribe=False)
    first_line = capsys.readouterr().err.strip().splitlines()[0]
    assert len(first_line) < 400 and first_line.endswith("…")


def test_no_message_when_the_run_finished(tmp_path, capsys):
    from cli.main import _report_halt

    ws, pipeline = _halted(tmp_path, [], 3)
    _report_halt(pipeline, ws, redescribe=False)
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# Frames of one video count once
# ---------------------------------------------------------------------------


def _with_frames(tmp_path, frames_per_video):
    """A workspace whose items are frames of the given videos, in that order."""
    ws = _workspace(tmp_path, sum(frames_per_video))
    items = sorted(ws.media_items(), key=lambda i: i.image)
    n = 0
    for v, count in enumerate(frames_per_video):
        for _ in range(count):
            items[n].item_type = "extracted_frame"
            items[n].parent_video = f"/videos/clip{v}.mov"
            ws.save_item(items[n])
            n += 1
    return ws


def test_one_videos_frames_failing_do_not_stop_the_run(tmp_path):
    """Windows AI failed at every size on all 15 frames of one screen recording while
    describing the frames around it (10/8/2026). That stopped every run at that video.
    Now the video counts once, and after three of its frames the rest are skipped."""
    ws = _with_frames(tmp_path, [15, 3])
    internal = lambda: RuntimeError("Windows couldn't describe this picture (InternalError).")
    provider = ScriptedProvider([internal() for _ in range(3)] + ["ok"] * 3)
    pipeline, events = _run(ws, provider)
    assert pipeline.halted is None
    assert len(events) == 18 and provider.calls == 6, "skipped frames are events too"
    assert pipeline.skipped == 12 == sum(e.skipped for e in events)
    assert not any(e.success for e in events if e.skipped)


def test_ten_videos_failing_in_a_row_still_stop_the_run(tmp_path):
    ws = _with_frames(tmp_path, [2] * 12)
    pipeline, events = _run(ws, ScriptedProvider([_timeout() for _ in range(24)]))
    assert pipeline.halted and len(events) == 19, "the 10th video's first frame"


def test_a_stuck_provider_stops_inside_long_videos(tmp_path):
    """A 30-minute video is 360 frames; three tried per video caps a stuck provider at
    about 30 timeouts, not 360 a video."""
    ws = _with_frames(tmp_path, [40] * 11)
    provider = ScriptedProvider([_timeout() for _ in range(440)])
    pipeline, events = _run(ws, provider)
    assert pipeline.halted and provider.calls == 3 * 9 + 1


def test_a_different_error_on_the_next_frame_starts_the_video_count_again(tmp_path):
    ws = _with_frames(tmp_path, [6])
    outcomes = [RuntimeError("a"), RuntimeError("a"), RuntimeError("b"), RuntimeError("b"),
                RuntimeError("b"), "ok"]
    pipeline, events = _run(ws, ScriptedProvider(outcomes))
    assert len(events) == 6 and pipeline.skipped == 1 and events[-1].skipped


def test_the_cli_says_why_frames_were_skipped(tmp_path, capsys):
    from cli.main import _report_halt

    ws = _with_frames(tmp_path, [6])
    pipeline, _ = _run(ws, ScriptedProvider([_timeout() for _ in range(6)]))
    _report_halt(pipeline, ws, redescribe=False)
    err = capsys.readouterr().err
    assert "3 video frame(s) were skipped" in err and "tries them again" in err
    _report_halt(pipeline, ws, redescribe=True)
    assert f'idt describe "{ws.path}" --redescribe' in capsys.readouterr().err


def test_the_progress_count_keeps_pace_with_skipped_frames(tmp_path):
    import io

    from idt_core.progress import Progress

    ws = _with_frames(tmp_path, [6])
    out = io.StringIO()
    progress = Progress(total=6, out=out)
    pipeline = WorkspacePipeline(ws, ScriptedProvider([_timeout() for _ in range(6)]))
    for event in pipeline.run(RunOptions(prompt_name="none", prompt_text="", extract_metadata=False)):
        if event.skipped:
            progress.skip(event.item.display_name, event.error)
        else:
            progress.update(event.item.display_name, success=event.success, error=event.error)
    lines = [line for line in out.getvalue().splitlines() if " of 6" in line]
    assert lines[-1].startswith("6 of 6") and "skipped" in lines[-1]


def test_failure_source():
    from idt_core.pipeline import failure_source, frame_video

    assert failure_source("x.jpg", "/v/clip.mov") == "/v/clip.mov"
    frame = "C:/w.idtw/derived/frames/iPhone/IMG_1/IMG_1_5.00s.jpg"
    assert failure_source(frame) == str(Path(frame).parent)
    upper = "C:/W.IDTW/Derived/Frames/IMG_1/IMG_1_5.00s.jpg"
    assert failure_source(upper) == str(Path(upper).parent)
    scratch = "C:/Users/k/Documents/idt/_scratch/derived/frames/IMG_1/IMG_1_5.00s.jpg"
    assert frame_video(scratch) == str(Path(scratch).parent)
    assert frame_video("C:/pics/a.jpg") is None
    # A folder of the user's own called derived/frames isn't a workspace's.
    assert frame_video("C:/Photos/derived/frames/a.jpg") is None
    # A workspace kept under such a folder: its own derived/frames is the one that counts.
    nested = "C:/proj/derived/frames/w.idtw/images/a.jpg"
    assert frame_video(nested) is None
    # A source subfolder called derived/frames inside a bundle: the bundle's own pair counts.
    inner = "C:/w.idtw/derived/frames/derived/frames/IMG/x.jpg"
    assert frame_video(inner) == str(Path(inner).parent)


# ---------------------------------------------------------------------------
# Declined pictures: remembered, and a video of them skipped
# ---------------------------------------------------------------------------


def test_a_video_whose_frames_are_declined_is_skipped_after_three(tmp_path):
    """Windows AI declined every frame of an iPhone screen recording of text."""
    ws = _with_frames(tmp_path, [15, 3])
    text = lambda: Declined("This picture has too much text for Windows to describe.")
    provider = ScriptedProvider([text() for _ in range(3)] + ["ok"] * 3)
    pipeline, events = _run(ws, provider)
    assert provider.calls == 6 and pipeline.skipped == 12 and pipeline.halted is None


def test_declined_pictures_are_not_asked_again_the_same_way(tmp_path):
    ws = _workspace(tmp_path, 4)
    first = ScriptedProvider([Declined("no"), "ok", Declined("no"), "ok"])
    _run(ws, first)
    second = ScriptedProvider([])
    pipeline, events = _run(ws, second)
    assert second.calls == 0 and events == [] and pipeline.previously_declined == 2


def test_redescribe_or_another_prompt_asks_again(tmp_path):
    ws = _workspace(tmp_path, 2)
    _run(ws, ScriptedProvider([Declined("no"), Declined("no")]))
    again = ScriptedProvider([])
    pipeline = WorkspacePipeline(ws, again)
    events = list(pipeline.run(RunOptions(prompt_name="other", prompt_text="", extract_metadata=False)))
    assert len(events) == 2 and again.calls == 2, "another prompt style is another question"
    (tmp_path / "two").mkdir()
    ws2 = _workspace(tmp_path / "two", 2)
    _run(ws2, ScriptedProvider([Declined("no"), Declined("no")]))
    redo = ScriptedProvider([])
    events = list(WorkspacePipeline(ws2, redo).run(RunOptions(
        prompt_name="none", prompt_text="", extract_metadata=False, redescribe=True)))
    assert redo.calls == 2


def test_a_picture_described_later_loses_its_declined_mark(tmp_path):
    ws = _workspace(tmp_path, 1)
    _run(ws, ScriptedProvider([Declined("no")]))
    item = ws.media_items()[0]
    assert item.extra.get("declined")
    list(WorkspacePipeline(ws, ScriptedProvider(["ok"])).run(RunOptions(
        prompt_name="none", prompt_text="", extract_metadata=False, redescribe=True)))
    assert "declined" not in Workspace.open(ws.path).media_items()[0].extra


def test_the_refusal_stop_counts_pictures_or_videos(tmp_path):
    """Declined frames of 10 videos are 10 refusals toward the 25, not 30."""
    ws = _with_frames(tmp_path, [3] * 30)
    pipeline, events = _run(ws, ScriptedProvider([Declined("no") for _ in range(90)]))
    assert pipeline.halted_by_refusals
    assert sum(1 for e in events if not e.skipped) == 3 * 24 + 1
