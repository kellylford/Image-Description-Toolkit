# Session summary — 9/24/2026: Claude Code provider (Claude on a subscription)

## Goal

Let IDT describe images and chat using a Claude Pro/Max **subscription**
instead of an API key, working like every other provider across the CLI,
ImageDescriber and IDT Chat.

## Approach

Claude Code (`claude` CLI) is scriptable with `claude -p` and bills the signed-in
claude.ai subscription. New provider key: `claude-code` (label "Claude Code").

Measured on real photos (Haiku, Max plan), per image:

| Version | Turns | Input tokens | API-equivalent cost |
|---|---|---|---|
| Default `claude -p` + Read tool | 3 | ~17,700 | ~$0.022 |
| Short `--system-prompt`, image inline via stream-json, no tools | 1 | 1,876 | $0.003–0.0055 |

The second form is what shipped: an image costs what it costs through the API.
The remaining cost is the description itself (~260–730 output tokens).

Decisions:

- **Billing guard.** Nothing runs unless `claude auth status` reports
  `authMethod: claude.ai`. `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
  `ANTHROPIC_BASE_URL` and `CLAUDECODE` are removed from the child environment.
  `--bare` is never used — bare mode accepts only API-key auth.
- **Chat history as a transcript.** In `--input-format stream-json` the CLI
  answers every user line as a new turn and ignores assistant lines (verified),
  so prior turns are sent as one labelled transcript with a system-prompt note.
  Each turn is still a fresh unsaved session, so the engine keeps owning
  edits/retries/compaction.
- **Stop works.** `run_claude()` is a generator; closing it kills the process.
- **GUI label ≠ key.** Dialogs read the provider back with `.lower()`, which
  turns "Claude Code" into "claude code". Replaced with
  `ai_providers.provider_key()` at every picker read. Display names moved into
  `registry.display_name()` so titles say "Claude Code", not "Claude-Code".
- **Hidden when the CLI is missing**, like MLX off Apple Silicon: installing it
  happens outside the app, so offering it could only fail.
- **Not included:** PDF attachments (unverified through stream-json), chat web
  search (engine-executed tools can't be called back from the CLI),
  temperature.

## Files

New:
- `idt_core/providers/claude_code.py` — CLI discovery, subscription check, `run_claude()` runner, `ClaudeCodeProvider` (describe)
- `idt_core/chat/claude_code.py` — `ClaudeCodeChatProvider`, transcript formatter
- `pytest_tests/unit/test_claude_code_provider.py` (28 tests, fake CLI subprocess)
- `pytest_tests/unit/test_claude_code_dialogs.py` (8 wx tests driving the real dialogs)

Changed:
- `idt_core/providers/registry.py` — `claude-code` capabilities + aliases; `display_name` field and function
- `idt_core/providers/catalog.py` — curated tables for `claude-code`
- `idt_core/chat/providers.py` — lazy factory branch; `idt_core/chat/tokens.py` — context window
- `cli/main.py` — `--provider claude-code` for describe/download/video/watch, `idt chat`, `idt models`; chat default model; temperature warning
- `cli/guide.py` — guideme offers Claude Code and checks sign-in instead of an API key
- `imagedescriber/ai_providers.py` — `ClaudeCodeProvider` (GUI), picker entry, `provider_key()`
- `imagedescriber/dialogs_wx.py`, `chat_window_wx.py`, `prompt_editor_dialog.py`, `configure_dialog.py`, `imagedescriber_wx.py`, `batch_progress_dialog.py`, `data_models.py` — picker reads, model lists, error hints, display names
- `chatapp/chat_app_wx.py` — provider list and model list
- `idt/idt.spec`, `imagedescriber/imagedescriber_wx.spec`, `chatapp/chatapp.spec` — hidden imports
- `pytest_tests/unit/test_provider_contract.py` (fault-injection driver), `test_provider_picker_platform.py` (label/key test replaced)
- Docs: `CLAUDE.md`, `README.md`, `docs/DEVELOPER_GUIDE.md`, `docs/USER_GUIDE.md` (new provider section)

## Test results

- Full suite: 1756 passed, 43 skipped (before the dialog tests were added); new dialog tests 8/8.
- Live, against the real subscription (dev mode): 20 HEIC photos via `idt describe` — 20/20, 0 errors, 1 turn each; 2-turn chat with streaming, history recall and Stop.
- Live, ImageDescriber's provider class in dev mode: HEIC converted and described, token usage reported.
- Frozen builds (Windows x64): all three built; both new modules confirmed in each PYZ.
  - `idt.exe`: `version`; `models --provider claude-code` listed 3 models; `describe` of 2 JPG + 1 HEIC → 3/3, 0 errors, log shows tokens; one-shot `chat` answered.
  - `ImageDescriber.exe` and `IDTChat.exe`: launched and opened their main windows (not driven further).

## Found along the way (not fixed here)

- `idt describe` fails when workspace path + long filename exceed Windows' 260-character limit (`photo-…_singular_display_fullPicture.heic.json.tmp`). Spun off as a separate task.
- The main checkout's `idt/.winenv` holds only PyInstaller (no Pillow, SDKs, …), so `build_idt.bat` there produces an exe that fails every command with "Pillow is required". The worktree build used a fresh venv from `idt/requirements.txt`.

## Not tested

- macOS (builds, GUI, Keychain-free auth path). The CLI lookup covers `~/.local/bin/claude`, but nothing ran on a Mac.
- The GUI apps driven by hand end to end with a live subscription (dialogs were driven by tests; the describe/chat paths underneath were run live from the CLI).
- A plan actually running out of usage mid-batch — the error text is surfaced, but the exact wording Claude Code uses was not observed.
