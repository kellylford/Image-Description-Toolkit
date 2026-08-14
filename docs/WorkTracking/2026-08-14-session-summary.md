# Session Summary — 2026-08-14

## Goal

Evaluate IDT Chat as a *full* AI chat app, file a tracking issue, and implement
the gaps in priority order ([#265](https://github.com/kellylford/Image-Description-Toolkit/issues/265)).
Scope note: ImageDescriber's in-app chat stays a basic image-Q&A surface; it
picks up shared-engine improvements only. Advanced features (web search,
thinking) are for the standalone app and `idt chat`.

## What shipped

### 1. Ollama options dict (`idt_core/chat/providers.py`)
- `OllamaChatProvider.chat` now sends `options={num_ctx, temperature, num_predict}`.
  Previously the entire request was `model + messages + stream=True`, so
  `--temperature` / `--max-tokens` were **silent no-ops for Ollama**, and the
  server truncated long chats at its own default (~4,096) while the budgeter
  assumed 32k.
- `num_ctx` is sized from the conversation estimate + reply headroom, rounded
  to 2,048, floored at 4,096, capped at the model's trained context length
  (32,768 fallback when unknown). With tools on it floors at 32,768 per
  Ollama's search-agent guidance.
- New shared discovery `model_context_length()` in `idt_core/providers/ollama.py`
  (SDK first, then raw REST `/api/show` because **some ollama-python releases
  drop `model_info` entirely** — confirmed live: SDK returned `[]`, REST
  returned `gemma4.context_length: 262144`). Cached per process; failures not
  cached. `tokens.context_window_for` now consults it, so the budgeter uses the
  real window. ImageDescriber's token gauge (`chat_window_wx.py`) now calls the
  shared function instead of its private copy.

### 2. Text-file attachments (all providers)
- `.txt .log .md .csv .html/.htm .css .js .py .json .xml .yaml/.yml` are
  accepted and **inlined into the prompt** by the formatters
  (`merge_text_attachments` in `chat/providers.py`), so they work with every
  model — including text-only Ollama models. Never uploaded; Claude's encoder
  is guarded so a text file can no longer be encoded as an image block.
- Registry (`providers/registry.py`): `TEXT_ATTACHMENT_MIME_TYPES`,
  `is_text_media_type()`, `max_text_bytes` (1 MB sanity cap, ours not the
  API's), a "Text files" wildcard group, `accepted_extensions()` (rejection
  messages now list ".jpg, .txt" instead of "jpeg, plain, x-python").
  `supports_documents` now means real uploads (PDF) only.
- Token estimator counts text attachments by `stat` size (no reads in the
  budget loops). A deleted file becomes a note in the replayed turn, not a
  failed request.
- MLX deliberately unchanged (one-image vision path).

### 3. Chat-appropriate Ollama model listing
- New `OllamaProvider.list_chat_models()` filters on the `completion`
  capability (fails open); describe keeps the vision filter (issue #227
  behavior preserved and pinned by a test). New shared
  `model_capabilities()` probe with its own cache.
- The chat app's picker and `idt chat`'s default-model selection use it.
  Live verification: `nemotron-3.5-lightning` and `glm-5.2:cloud` (text-only)
  now appear; embedding-only models are excluded.

### 4. Tool calling + Ollama web search
- Engine-level: `ChatOptions(web_search=True)` offers `web_search`/`web_fetch`
  tools (Ollama only; ignored elsewhere). New `idt_core/chat/tools.py` calls
  `https://ollama.com/api/web_search|web_fetch` via **stdlib urllib** (no new
  frozen-build dependency), truncates results, and returns errors *as tool
  results* so a failed search never fails the turn.
- Key: pseudo-provider `"ollama.com"` in `idt_core/keys.py` →
  `OLLAMA_API_KEY` env or `api_keys` config. Distinct from the ollama chat
  provider, which still needs no key.
- Provider tool loop in `OllamaChatProvider.chat`: bounded at 5 rounds, final
  round withholds tools so the model must answer; usage summed across rounds;
  tool exchange goes back as `role=tool` messages.
- New events `ChatToolCall` (with `describe()` for status bars/screen readers)
  and `ChatToolResult`. UI: chat app gets Chat → "Use Web Search"
  (Ctrl+Shift+W, checkable, Ollama-only, vetoes without a key, warns when the
  model lacks the `tools` capability); CLI gets `--web-search`.
- Tool notes join the *streaming display* only — never the saved message
  (pinned by test).

### 5. Thinking mode
- `ChatOptions(thinking=None|True|False)`: auto mode sends `think=True` only
  when `/api/show` reports the `thinking` capability (**fails closed** —
  a wrong True is an API error, a wrong None just leaves tags in the text).
- Thinking streams as `ChatThinking` events, is never committed to history,
  and is never narrated: the app shows status "Model is thinking…", the CLI
  prints one `[thinking…]` note (or streams it to stderr with
  `--show-thinking`). Flags: `--think` / `--no-think`.

### Bug fixed along the way (pre-existing, latent)
- `idt_core/keys.py::_from_config` assumed `load_json_config` returns a dict;
  the idt_core loader returns `(config, path, source)`. **Anyone whose
  Claude/OpenAI key existed only in the config file crashed resolution with
  "'tuple' object has no attribute 'get'".** Masked in tests because the
  fixture stubs the loader with a dict; now unpacked properly and pinned with
  a test feeding the real tuple shape.
- Fixed `test_chat_app_smoke._bound_handler_names` to read only the handler
  argument of `Bind(event, handler, source)` — it treated the source widget as
  a handler name.

## Files changed
`idt_core/chat/{providers,engine,events,tokens,attachments,messages,tools*,__init__}.py`
(`tools.py` is new), `idt_core/providers/{base,ollama,registry}.py`,
`idt_core/keys.py`, `chatapp/chat_app_wx.py`, `cli/main.py`,
`imagedescriber/chat_window_wx.py`, all three `.spec` files
(added `idt_core.chat.tools` to hiddenimports — it is imported lazily, which
PyInstaller's static analysis can miss).

Tests: `test_ollama_context_length.py` (new), `test_chat_web_tools.py` (new),
plus additions to `test_chat_providers.py`, `test_chat_attachments.py`,
`test_ollama_vision_filter.py`, `test_api_key_resolution.py`.

## Test results
- Unit suite: **1143 passed, 1 skipped** (excluding `test_shell_script_safety`
  and `test_build_orchestrators`, which fail identically on a clean tree —
  Windows bash stub mangles UTF-16; environmental, unrelated).
- Live dev-mode verification against local Ollama:
  - Chat listing includes text-only models; describe listing unchanged.
  - Context discovery: gemma4:31b → 262,144; nemotron → 1,048,576
    (via the REST fallback; SDK returned empty `model_info`).
  - `idt chat` one-shot with minicpm-v4.6: `[thinking…]` on stderr, clean
    answer on stdout.
  - Text attachment: model correctly read an attached .txt ("PELICAN" test).
  - `--web-search` without a key: upfront warning, model's search attempt got
    the explanatory result, turn still completed. `--no-think`: no thinking.

## NOT tested
- Web search **with** a real `OLLAMA_API_KEY` (none set on this machine) —
  the executor's success path is covered by mocked tests only.
- Frozen builds (no exe was built this session; spec files updated but a
  Windows build + smoke test is still owed before release).
- The chat app GUI interactively (constructor/handler smoke tests only).
- MLX paths (Windows machine).
- Claude/OpenAI live turns (no keys in env this session).

## Round 2 (same day): shared key management in the OS credential store

- **`idt_core/keys.py` credential-store backend** — Windows Credential
  Manager via ctypes/advapi32, macOS Keychain via the `security` CLI; stdlib
  only (no `keyring` dependency to carry through the specs). New
  `set_api_key` / `delete_api_key` / `key_source` / `credential_store_name`.
  Resolution order is now env → **credential store** → config file → legacy
  files. Blobs are written UTF-16LE (cmdkey convention) and read with a NUL
  heuristic so hand-added UTF-8 entries still work. Store entries live under
  service "Image Description Toolkit"; tests point `_CRED_SERVICE` at a
  scratch name and run a **real** roundtrip on Windows.
- **IDT Chat: File → API Keys…** — new `ApiKeysDialog` sets Claude / OpenAI /
  ollama.com keys for the *whole toolkit*. Never displays stored keys; shows
  where each key comes from (env / store / config / legacy), with per-provider
  Remove buttons that explain when an env var still overrides.
- **ImageDescriber settings** — the API Keys tab now lists the three canonical
  providers (including Ollama Web Search, previously missing) with a status
  line instead of leaking key prefixes/suffixes as before. Saving writes to
  the credential store and **migrates the plaintext copy out of the config
  file**; delete removes from both. Edit no longer pre-fills the current key.
- **`ai_providers.py` unification** — the GUI describe providers now consult
  `idt_core.keys.resolve_api_key` first, so store-saved keys reach them.
  Precedence note: this puts env ahead of config in the GUI, matching chat
  and the CLI (the old GUI-only order had config winning).
- **`tool_result_summary` fix** — a failed `web_fetch` was summarised as
  "Page retrieved"; non-JSON results (errors, missing-key message) now
  surface as the status line.
- **Machine setup** — set `OLLAMA_API_KEY` (User scope) from Kelly's key
  file; running shells predate it, so only new processes see it. With the key
  in-process, verified the real web-search success path end to end:
  `[Searching the web: …] [Found 1 result(s)]` and a correct, current answer.

Round-2 NOT tested: the macOS Keychain path against a real Mac (command
shapes pinned by tests only); the describer configure dialog interactively.

## Round 3 (same day): read responses aloud + full-text transcript items

- **Speech via ClaudeSpeak's routers, bundled verbatim** — `shared/speech/`
  now carries `speak-engine.ps1`/`speak-voices.ps1` (Windows: JAWS COM →
  NVDA controller DLL → OneCore → SAPI) from TheWorkBench main, and
  `speak-engine.sh`/`speak-voices.sh` (macOS: VoiceOver AppleScript `output`
  → `say`) from the `claudespeak-macos` branch (a7a1286, verified on Apple
  silicon). One IDT adaptation: `speak-engine.sh`'s config reader falls back
  to `plutil` when `jq` is absent, since jq does not ship with macOS.
- **`shared/speech_engine.py`** — the harness: `SpeechSettings` (persisted at
  `~/.idt/chat_speech.json`), engine/voice enumeration (bundled PS probe on
  Windows; native `say -v '?'` parse on macOS — no jq needed to enumerate),
  `strip_for_speech` markdown cleanup (code blocks become "Code block
  omitted", links keep text), and a `Speaker` running the router as a
  detached hidden process, killing the previous one before the next
  (ClaudeSpeak's pid model held in-process). Rate is a preset
  (default/slow/normal/fast/fastest) resolved to each engine's own scale;
  **screen-reader routes never get voice or rate**, by design.
- **IDT Chat: File → Settings…** — new tabbed `SettingsDialog`, Speech tab:
  auto-read on/off, engine picker (Automatic / detected screen readers /
  every OneCore, SAPI, or macOS voice), rate preset (disabled for screen
  readers with an explanatory note). Engines are probed in a background
  thread at startup so the dialog opens instantly.
- **Wiring** — on `ChatFinished`, if auto-read is on the response is spoken
  and the focus-flip announcement is suppressed (no double-speaking);
  sending a new message, Ctrl+., and closing the window all stop speech.
- **Transcript accessibility fix (user request)** — history-list items now
  carry the **full** message text instead of a 120-character preview, so a
  screen reader arrowing the list hears whole responses (visual clipping by
  width is fine) — same convention as ImageDescriber's description lists.
- `chatapp.spec`: `shared/speech/*` added to datas, `shared.speech_engine`
  to hiddenimports.
- Verified live on Windows: `SPOKE VIA: sapi` in the engine's route log from
  an end-to-end run through the bundled scripts. JAWS route is exercised
  daily on this machine by ClaudeSpeak itself (same script, same config
  shape). Tests: 1187 passed, 1 skipped.
- Round-3 NOT tested: macOS routes from inside IDT (scripts verified in
  TheWorkBench, harness command-line pinned by tests only); the Settings
  dialog interactively with a screen reader; NVDA route (no NVDA running).

## Follow-ups (still open on #265)
- BMP/TIFF images (transcode-on-attach like HEIC, or declare for Ollama).
- PDF for OpenAI; PDF text extraction for Ollama.
- Settings dialog (temperature/host/context), conversation rename,
  cross-chat search, context-window gauge in the standalone app.
- Consider announcing tool activity via the screen-reader announcement
  mechanism (currently status bar + transcript note only).
