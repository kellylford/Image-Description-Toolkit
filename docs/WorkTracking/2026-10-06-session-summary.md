# 2026-10-06: finishing #352, the flaky test, and a first vmtest run

All work happened in the Windows session. The Mac session was off. Nothing has
been released since 4.6.1.

| PR | Issue | What |
|---|---|---|
| #353 (Mac, finished from Windows) | #352, #337 | Fixes from the post-merge review of #350, and Apple refusals no longer halting a batch |
| #355 | #352 | The rest of #352, plus the "Failed: 3 vs 4 failed" miscount |
| #356 | (none) | The intermittent `test_model_refresh` failure |
| (not a PR) | #357 filed | Configure Settings opens before its own model refresh lands (pre-existing) |

## Decisions
- **A refusal halt doesn't requeue its images.** After 25 refusals in a row
  the batch stops, and the declined images stay failed. Requeued, they would
  have been declined again by the same prompt first, so every resume halted on
  them.
- **Yes to "resume?" doesn't block.** When the extraction thread is still
  letting go of a video, the run gets `resume_when_stopped` and the resume
  happens in `_finish_extraction`. A "Resuming once frame extraction stops"
  window shows meanwhile; its Stop is a real stop.
- **A failed start puts back what it replaced:** `cancel.prev_batch_state` and
  `prev_flags`, recorded before the run marks anything.
- **`_forget_older_batch` is the one place** where a new batch clears an older
  batch's pending flags. Launch, downloads and extracted frames all use it.
- **The test suite sets `IDT_SKIP_STARTUP_MODEL_REFRESH`.** ImageDescriber's
  startup refresh thread outlived the test that started it and changed the
  shared model catalog, which also hit the provider and CLI-models tests. It
  also called the real Claude and OpenAI APIs on a machine with keys. The chat
  dialog's tests make `catalog.is_stale` return False for the same reason.

## vmtest trial
- Installed the vmtest skill (`~/.claude/skills/vmtest`) and ran CI's
  ImageDescriber build (main eb0d1ba) in the ClaudeTesting VM:
  - deployed the build and a folder of 2 photos and 2 videos;
  - launched it and read its accessibility tree;
  - ran an `--autostart` batch with no AI provider in the VM.
- It found the "Failed: 3" over "4 failed" miscount, fixed in #355.
- It also found, for someone to listen to:
  - the image list has an empty accessible name;
  - the end-of-batch Warning opened behind the stay-on-top progress window.
- vmtest problems are filed in TheWorkBench with the VMTest label:
  - #151: one-file apps report no window and never get the foreground.
  - #152: open menus can't be driven.
  - #153: owned dialogs are only reachable by process id.
  - #154: wx's negative control ids need `-Target`.
  - #155: the skill should say the VM is disposable.

## Test results
- Full suite on main after #355: 2,043 passed, 47 skipped.
- Two consecutive full runs since #356 passed with no warnings.
- The reviews of #353, #355 and #356 each went to a ready-to-merge verdict.
  Every finding was fixed with a test that fails without it.
- Real Windows runs on #353's branch:
  - the pipeline: descriptions arrived before extraction ended;
  - quitting mid-extraction: the finished video kept its 7 frames.

## Not tested
- JAWS and NVDA on the progress window:
  - the waiting line;
  - the "Resuming…" and "Stopping" windows;
  - the gauge label "Progress: total not known yet";
  - selection staying put as rows change.
- A real halt during a long extraction, against a real provider.
- The Mac: the Apple Intelligence refusal path, and VoiceOver on the iPhone library.
- #355 in a built executable. CI built it; nobody ran it.
