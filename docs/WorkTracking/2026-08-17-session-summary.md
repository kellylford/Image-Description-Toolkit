# 2026-08-17 — MLX provider filtering (#271), and two issues filed

Follow-on from the 2026-08-16 model-catalog work. Two issues filed, one of
them fixed.

## Issue #271 — MLX offered where it cannot run

**Reported:** starting a chat in ImageDescriber on Windows listed MLX, which is
Apple Silicon only. IDT Chat did not list it, which is what made the difference
visible.

`MLXProvider.is_available()` was correct all along — it checks the platform
*and* whether `mlx_vlm` imports. Three ImageDescriber dialogs simply never
asked it:

| Dialog | Was |
|---|---|
| `ChatDialog` (`chat_window_wx.py:149`) | `['Ollama','OpenAI','Claude','MLX']` — the one reported |
| `ProcessingOptionsDialog` (`dialogs_wx.py:889`) | `["Ollama","OpenAI","Claude","MLX"]` |
| `FollowupQuestionDialog` (`dialogs_wx.py:415`) | Correct in the normal path; its *fallback* default reintroduced MLX whenever the caller's `try/except` fired |
| `PromptEditorDialog` (`prompt_editor_dialog.py:210`) | `["ollama","openai","claude"]` — wrong the **other** way: a Mac user who could run MLX was never offered it |

All four now route through one new `ai_providers.provider_picker_choices()`.

**Why it asks the providers rather than checking the platform:** the
PyInstaller specs can exclude `mlx_vlm` to keep the binary small, so a packaged
macOS build on Apple Silicon can still be unable to run it. A platform check
alone would offer a provider that raises the moment it is picked — the same
reasoning as IDT Chat's `_mlx_is_usable()`.

**Only the platform-gated provider is filtered.** Ollama stays listed when the
daemon is down and the cloud providers stay listed without an API key — those
are fixable setup steps the dialogs already explain, not reasons to make a
provider undiscoverable.

### Two further bugs the fix forced out

1. **`ProcessingOptionsDialog` selected the configured provider through a fixed
   `{'ollama': 0, ..., 'mlx': 3}` index map.** Shortening the list makes those
   indices point at the wrong entries, so removing MLX alone would have made
   *every* provider select the wrong one — worse than the reported bug.
   Selection is now looked up in the list actually built.
2. **`SetStringSelection()` fails silently** when the value isn't in the list.
   In the prompt editor that left the picker on nothing, and saving would have
   written an empty `default_provider` back to
   `image_describer_config.json`. Reachable whenever a config names a provider
   the machine cannot offer — one written on a Mac with MLX, opened on Windows.

### A test caught the change, correctly

`test_provider_registry.py::_picker_providers()` parsed the literal provider
list out of `chat_window_wx.py` with a regex. Replacing that literal with a
function call left the regex matching nothing — and its own "parsed as empty"
assertion fired rather than passing vacuously. The guard did exactly its job.

It now calls `provider_picker_choices()` directly, which is strictly better:
it checks what the dialog will actually show, platform filtering included,
instead of a regex's view of the source.

## Testing

New `pytest_tests/unit/test_provider_picker_platform.py` (15 tests). Two
choices worth recording:

- **Assertions compare against `is_available()`, not a hardcoded platform
  answer**, so the tests fail on whichever machine has the bug rather than
  encoding one platform's expectation.
- **The Mac path is simulated, not skipped.** This change exists *for* Mac
  users; a test that skips everywhere CI runs would never have exercised it.
  The helper and `MLXProvider.is_available` are patched so the MLX branch runs
  on any platform — verified it lists all 12 models and leaves the combo
  enabled. Without that, adding MLX to the picker without a matching
  `populate_model_combo()` branch would have shipped Mac users a provider with
  an empty model list, visible only to them.

A regression guard scans the three dialog files for a hardcoded list naming
MLX. **Verified non-vacuous** by re-inserting the old line into a copy and
confirming it fires.

**Suite: 1599 passed, 15 skipped, 0 failed.** All coverage floors green.

### Not tested

- **macOS.** Windows only. The Mac path is covered by simulation, which
  exercises the code but not the platform — nobody has run this on a Mac with
  `mlx_vlm` actually installed.
- **The GUI as a running application.** Dialogs were driven headlessly under a
  real `wx.App`, which is what caught the index-map bug, but nobody clicked
  through the window.

## Issues filed

- **[#270](https://github.com/kellylford/Image-Description-Toolkit/issues/270)** — web search for Claude and OpenAI. `ChatOptions.web_search` is already
  plumbed through but `engine.py:231` gates it on `provider_name == "ollama"`,
  so it is silently ignored elsewhere. Claude is straightforward
  (`web_search_20260209`, no beta header, but needs `pause_turn` handling and
  the result block's list-vs-object content shape). OpenAI needs a decision
  first: `web_search_options` works only on the `-search-preview` models, so
  either restrict-and-substitute the model or add a Responses API path.
- **[#271](https://github.com/kellylford/Image-Description-Toolkit/issues/271)** — the MLX bug above. Closed by `3805dba` and `3b76c10`.
