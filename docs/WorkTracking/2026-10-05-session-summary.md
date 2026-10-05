# 2026-10-05: follow-ups to 4.6.1, and describing while extracting

Four PRs merged to main, built across two machines: this Windows session, and a
Mac session over Remote Control. Each machine reviewed the other's PRs. Nothing
has been released since 4.6.1.

| PR | Issue(s) | What |
|---|---|---|
| #348 | #346 items 1, 4, 5; #349 | The embed choice belongs to each batch worker; resume keeps it; the Stopping line is matched exactly; CodeQL asserts |
| #347 (Mac) | #345; #346 items 2, 3 | Quitting during extraction keeps finished videos (each is recorded and checkpointed as it finishes); non-vetoable close; a cancelled close restores the batch's window |
| #350 | #344 | A batch with videos describes while it extracts |

## #344: describe while extracting (#350)

**Before:** extract every video → save → describe. A 1,340-video library described
nothing for 25+ minutes.

**Now:** save → describe the images at once, while a thread extracts the videos.
Each video's frames join the describe queue as soon as it finishes.

### Decisions
- **A pipeline,** not "photos first": photos first still leaves a long wait once
  the photos run out.
- **`BatchProcessingWorker` keeps one open queue** (`add_files`, `close_queue`),
  rather than starting a second worker per video. One run, one progress window,
  one completion.
- **The run's cancel event lives until extraction ends,** not only until
  describing starts. Stop, halt and close all go through it, each with exactly
  one announcement (`cancel.announced`). `cancel.describing` tells a stop before
  describing from one after.
- **Frames are queued only while `batch_state` is still the run's own object.**
  Stop and completion clear it; a halt keeps it, so a late video is resumable.
- **`batch_state["videos"]`** lets resume extract the videos the batch never reached.
- **Progress window:** extraction has its own row, kept separate from the
  describe progress. The selection is restored by row label, not index. The
  title changes once, when extraction ends.

### Files
- `imagedescriber/imagedescriber_wx.py`: `_extract_then_launch` rewritten, plus
  `_launch_batch(extraction=…)`. Also changed: `on_stop_batch`,
  `on_workflow_complete` (with a closing case), `on_close` (cancelled close of a
  describing run), `resume_batch_processing`, `prompt_resume_batch`,
  `on_worker_progress` and `on_pause_batch`.
- `imagedescriber/workers_wx.py`: the open queue, a pause/stop re-check after
  waiting, and `evt.waited` / `evt.more_coming`.
- `imagedescriber/batch_progress_dialog.py`: `begin_extraction`,
  `set_extraction`, `end_extraction`, `stop_extraction` and `_row_label`.
- `pytest_tests/unit/test_batch_stop_restart.py`: tests updated for the new
  order, plus about 20 new tests.
- `CHANGELOG.md` and `docs/USER_GUIDE.md`.

## Test results
- **Full suite:** 1,993 passed, 47 skipped (Windows). CI passed on Windows and macOS.
- **#350 review:** two independent review rounds. Every finding was fixed, each
  with a test that fails without its fix.
- **Real Windows runs:**
  - **#347:** quitting during the second of four real videos kept the first
    video's 7 frames. The same script without the fix kept nothing. An msw probe
    with a real `Destroy()` and `MainLoop` showed a video finishing 0–3 s into the
    close is kept, and one at 7 s is re-extracted (5 s wait, as designed).
  - **#350:** 3 real videos plus photos, real OpenCV, with only the AI call stubbed.
    9 descriptions were done before the last video finished extracting; everything
    ended up described and saved, with `batch_state` cleared.
- **One-off flaky failure:** `test_model_refresh` under `-n 4`, filed as a
  separate task.

## Not tested
- JAWS and NVDA behaviour of the progress window during describe-plus-extract:
  the arrow position as rows come and go, title announcements, and the Stop and
  cancelled-close messages.
- A real Mac run against the iPhone library on the SMB share, with VoiceOver.
- A real provider during the pipeline (the AI call was stubbed); a real
  sign-out halt during extraction.
- A built executable: the dev-mode code paths were tested, the PyInstaller build
  only by CI.
