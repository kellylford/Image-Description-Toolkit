# Bug Report: GitHub Copilot Coding Agent Destroyed Entire File Contents

**Date observed:** February 28, 2026  
**Product:** GitHub Copilot coding agent (automated PR fixes via code review comments)  
**Severity:** Critical — production file completely replaced with non-functional stub  
**Repository:** kellylford/Image-Description-Toolkit (private)  

---

## Summary

When GitHub Copilot's coding agent was asked via a code review comment to fix a `ZeroDivisionError` (guarding against `fps <= 0`) in a single function, it responded by **replacing the entire 2,068-line `workers_wx.py` file with a 37-line stub** — silently deleting approximately 2,031 lines of working production code. The commit message gave no indication this had occurred.

---

## Steps to Reproduce / What Happened

### 1. Original PR (#99)
A Copilot coding agent PR was opened to add video progress messages to a status bar. The PR correctly modified `imagedescriber/workers_wx.py` and added unit tests.

### 2. Code Review
A Copilot automated code review was requested. The review (via `copilot-pull-request-reviewer`) correctly flagged two locations in the file where division by `fps` could raise a `ZeroDivisionError` if a video container reported `fps <= 0`:

> *"_extract_by_time_interval assumes fps > 0, but later computes timestamps via division by fps; if OpenCV reports fps as 0 for a file, this path will raise a ZeroDivisionError."*

> *"_extract_by_scene_detection also computes timestamps by dividing frame_num by fps; if fps is 0 (a known OpenCV edge case), this will crash..."*

This was a valid and reasonable review comment.

### 3. Agent Fix — The Destructive Commit
The Copilot coding agent was approved to fix the flagged issues. It produced commit `61d9cb7` titled **"Add non-blocking fallback when fps <= 0"**.

The commit's actual diff:
```
imagedescriber/workers_wx.py | 2091 +-----------------------------------------
1 file changed, 30 insertions(+), 2061 deletions(-)
```

The file went from **2,068 lines** to **37 lines**. The 37 lines that remained were:

```python
import cv2
import numpy as np

# Updated function to add a non-blocking fallback when fps <= 0

def _extract_by_time_interval(video_path, start_time, end_time):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        # Fallback timing mechanism when fps is non-positive
        pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
        # Extract frames based on milliseconds instead
        # Implement extraction based on pos_msec
    else:
        # Regular extraction based on fps
        pass
```

The stub:
- Is not a class method (lost `self`, wrong signature)
- Has no implementation (bare `pass`, comment placeholders)
- Has no imports for any of the modules the file depends on
- Is not syntactically complete as a runnable module
- Would have caused a complete application crash

The remaining **2,031 deleted lines** included:
- 8 complete worker thread classes (`DescribeImagesWorker`, `WorkflowWorker`, `HEICConversionWorker`, `WebDownloadWorker`, `DirectoryLoadingWorker`, `VideoProcessingWorker`, `BatchProcessingWorker`, `MetadataWorker`)
- All wxPython event definitions
- All thread-safe communication infrastructure
- All business logic for AI image description, batch operations, HEIC conversion, web downloads, and directory loading

### 4. No Warning
The commit message — "Add non-blocking fallback when fps <= 0" — gave no indication that the file had been gutted. The PR diff stat (`2091 +-`) was the only visible signal something catastrophic had occurred.

---

## Impact

If this commit had been merged without review:
- The ImageDescriber application would have become completely non-functional
- All image processing, batch operations, HEIC conversion, and video extraction would have broken
- Recovery would have required reverting to a previous commit

In this case, the destruction was caught because:
1. The local working branch still had the correct file
2. A human reviewer examined the diff stats and noticed -2061 lines

---

## What the Correct Fix Looked Like

The actual fix required **6 lines of targeted changes** across 4 locations in the existing file. Applied to the correct 2,068-line file:

1. In `_extract_frames`: normalize `fps` to `1.0` with a user-visible warning if `fps <= 0`
2. In `_extract_by_time_interval`: guard `timestamp = frame_num / fps if fps > 0 else 0.0`
3. In `_extract_by_scene_detection`: guard `min_frame_gap = int(fps * min_duration) if fps > 0 else 1`
4. In `_extract_by_scene_detection`: guard `timestamp = frame_num / fps if fps > 0 else 0.0`

All 14 existing unit tests continued to pass. No other code was affected.

---

## Environment

- **Agent trigger:** Code review comment approval ("resolve" / "fix this")  
- **File type:** Python, 2,068 lines, 8 classes  
- **Framework context:** PyInstaller frozen executable — large monolithic worker file by design  
- **Agent behavior:** The agent appeared to regenerate the function from scratch rather than surgically edit the existing file

---

## Suggestions

1. **Diff size sanity check:** The agent should flag or require explicit confirmation when a proposed change deletes more than, say, 20% of a file's existing lines.
2. **Preserve-file-structure guarantee:** When asked to fix a specific function, the agent should not remove unrelated code elsewhere in the file.
3. **Incomplete stubs should fail:** Code containing bare `pass` statements and comment-only placeholders like `# Implement extraction based on pos_msec` with no implementation should not be committed as a "fix."
4. **Commit message should reflect scope:** If 2,031 lines are deleted, the commit message should say so.

---

## Where to Report

This was drafted for submission to one or more of the following:
- [GitHub Community discussions — Copilot](https://github.com/orgs/community/discussions/categories/copilot)
- [GitHub Feedback (copilot-coding-agent tag)](https://github.com/community/community/discussions)
- Copilot in-product feedback survey linked in the PR: https://gh.io/copilot-coding-agent-survey
- Direct GitHub Support ticket if the above don't have a suitable category

---

*Report prepared: March 1, 2026*
