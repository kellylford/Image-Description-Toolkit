#!/usr/bin/env python3
"""
IDT Hook Guard — enforces pre/post verification protocol in GitHub Copilot agent sessions.

Receives JSON on stdin from VS Code Copilot hooks, outputs JSON decisions on stdout.

Events handled:
  PreToolUse  — warns when editing core Python files without pre-change verification
  Stop        — warns if edits were made but post-change verification is missing
"""

import json
import sys
import os
import argparse
from pathlib import Path

# --- Paths -------------------------------------------------------------------

# State files live in .idt_session/ to avoid polluting the root
WORKSPACE = Path(__file__).parent.parent
SESSION_DIR = WORKSPACE / ".idt_session"

FLAG_EDITS_MADE = SESSION_DIR / "edits_made"        # Written when core files are edited
FLAG_PRECHECK_DONE = SESSION_DIR / "precheck_done"  # Written when /pre-change finishes
FLAG_VERIFIED = SESSION_DIR / "verified"            # Written when /post-change finishes

# Core files where editing without pre-change verification is risky
GUARDED_FILES = {
    "imagedescriber_wx.py",
    "workflow.py",
    "image_describer.py",
    "idt_cli.py",
    "ai_providers.py",
    "workers_wx.py",
    "config_loader.py",
}

# Edit tools whose inputs contain file paths
EDIT_TOOLS = {
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "create_file",
    "edit_notebook_file",
}


# --- Helpers -----------------------------------------------------------------

def _session_flag_exists(flag: Path) -> bool:
    return flag.exists()


def _write_flag(flag: Path, content: str = "") -> None:
    SESSION_DIR.mkdir(exist_ok=True)
    flag.write_text(content, encoding="utf-8")


def _is_guarded_file(tool_input: dict) -> bool:
    """Return True if the tool is editing a guarded core file."""
    path_value = (
        tool_input.get("filePath", "")
        or tool_input.get("file_path", "")
        or tool_input.get("path", "")
        or ""
    )
    # multi_replace_string_in_file has replacements array, each with filePath
    if "replacements" in tool_input:
        paths = [r.get("filePath", "") for r in tool_input.get("replacements", [])]
    else:
        paths = [path_value]

    for p in paths:
        if Path(p).name in GUARDED_FILES:
            return True
    return False


def _files_being_edited(tool_input: dict) -> list[str]:
    """Collect filenames being edited for the flag message."""
    if "replacements" in tool_input:
        return list({Path(r.get("filePath", "")).name
                     for r in tool_input.get("replacements", [])})
    path = (
        tool_input.get("filePath", "")
        or tool_input.get("file_path", "")
        or tool_input.get("path", "")
        or ""
    )
    return [Path(path).name] if path else []


# --- Event handlers ----------------------------------------------------------

def handle_pre_tool_use(hook_input: dict) -> dict:
    """
    Before an edit tool runs on a guarded file:
      - Record that edits are happening (for the Stop handler)
      - Ask for user confirmation if pre-change check wasn't done
    """
    tool_name = hook_input.get("tool_name", "")

    if tool_name not in EDIT_TOOLS:
        # Not an edit tool — allow unconditionally
        return {"continue": True}

    tool_input = hook_input.get("tool_input", {})
    if not _is_guarded_file(tool_input):
        # Editing a non-guarded file — allow
        return {"continue": True}

    # It's a guarded file — mark that edits are in progress
    edited = _files_being_edited(tool_input)
    _write_flag(FLAG_EDITS_MADE, "\n".join(edited))

    if _session_flag_exists(FLAG_PRECHECK_DONE):
        # Pre-change was done — allow the edit
        return {"continue": True}

    # Pre-change hasn't been run — ask for confirmation
    files_str = ", ".join(edited) if edited else "a core file"
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"⚠️  IDT Guard: You're editing {files_str} without running "
                f"/pre-change verification first.\n\n"
                f"Run '/pre-change [describe your change]' to complete the checklist, "
                f"or confirm to proceed without it (not recommended for core files)."
            ),
        }
    }


def handle_stop(hook_input: dict) -> dict:  # noqa: ARG001
    """
    When the session ends:
      - If edits were made but post-change wasn't run, inject a warning into the session.
    """
    if not _session_flag_exists(FLAG_EDITS_MADE):
        # No guarded files were edited — clean session
        return {"continue": True}

    if _session_flag_exists(FLAG_VERIFIED):
        # Post-change was completed — clean
        return {"continue": True}

    # Edits happened but no post-change verification
    edited_names = ""
    try:
        edited_names = FLAG_EDITS_MADE.read_text(encoding="utf-8").strip()
    except OSError:
        pass

    files_note = f" ({edited_names})" if edited_names else ""
    return {
        "continue": True,
        "systemMessage": (
            f"⚠️  IDT Guard: Core files were edited{files_note} this session but "
            f"/post-change verification was not completed.\n\n"
            f"Before this task is truly done:\n"
            f"  1. Run '/post-change [list modified files]'\n"
            f"  2. Verify py_compile passes\n"
            f"  3. Test in dev mode (python imagedescriber_wx.py)\n"
            f"  4. Build exe if required\n"
            f"  5. Check logs for errors\n\n"
            f"Claiming 'done' without testing has caused 8-hour debugging sessions."
        ),
    }


# --- Entry point -------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="IDT Hook Guard")
    parser.add_argument("--event",
                        choices=["PreToolUse", "Stop"],
                        help="The hook event type (used by VS Code hooks)")
    parser.add_argument("--mark-precheck", action="store_true",
                        help="Mark pre-change verification as completed for this session")
    parser.add_argument("--mark-verified", action="store_true",
                        help="Mark post-change verification as completed for this session")
    parser.add_argument("--reset", action="store_true",
                        help="Clear all session flags (start of new task)")
    args = parser.parse_args()

    # Standalone flag-writing commands (called by prompts)
    if args.mark_precheck:
        _write_flag(FLAG_PRECHECK_DONE, "done")
        print("✓ Pre-change verification recorded.")
        return
    if args.mark_verified:
        _write_flag(FLAG_VERIFIED, "done")
        print("✓ Post-change verification recorded.")
        return
    if args.reset:
        for flag in (FLAG_EDITS_MADE, FLAG_PRECHECK_DONE, FLAG_VERIFIED):
            if flag.exists():
                flag.unlink()
        print("✓ Session flags cleared.")
        return

    if not args.event:
        parser.print_help()
        return

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        hook_input = {}

    # Route to handler
    if args.event == "PreToolUse":
        result = handle_pre_tool_use(hook_input)
    elif args.event == "Stop":
        result = handle_stop(hook_input)
    else:
        result = {"continue": True}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
