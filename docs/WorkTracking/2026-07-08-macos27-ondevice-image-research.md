# Research: macOS 27 on-device image description for ImageDescriber

**Date:** 7/8/2026
**Author:** Claude (dev lead) + Kelly
**Status:** Findings only — no code written this session (Kelly chose "document findings").
**Machine tested:** macOS 27.0 (build `26A5378j` — a **beta seed**), Apple Silicon (arm64), Python 3.14.6.

---

## TL;DR

macOS 27 (WWDC 2026) adds **on-device image input** to Apple's built-in Foundation Models
(Apple Intelligence). This is directly useful for IDT: a **free, offline, private, no-API-key,
no-model-download** image-description provider.

**The catch:** Apple's official Python SDK (`apple-fm-sdk`) **crashes** on the image path on this
machine. But Apple's built-in `/usr/bin/fm` CLI — which ships with macOS 27 — **works**, and its
`fm serve` mode speaks the **OpenAI Chat Completions API including base64 images**, which IDT's
existing `OpenAIProvider` already emits verbatim.

**Recommended integration (when we build it):** treat `fm serve` as a local model server, like
Ollama — reuse IDT's existing OpenAI-compatible client. This avoids the broken SDK, needs no Swift
build/PyInstaller native bundling, and requires only the OS's `fm` binary.

---

## What's new in macOS 27 (from web research)

- On-device Foundation Models now accept **image + text** prompts and return text (AFM 3, ~20B
  sparse / 1–4B active params). Fully on-device.
- Apple shipped an official **Python SDK** (`pip install apple-fm-sdk`) exposing
  `SystemLanguageModel`, `LanguageModelSession`, `ImageAttachment(path, label=None)`.
- Apple ships a built-in CLI, **`/usr/bin/fm`** (`respond`, `chat`, `serve`, `available`,
  `token-count`, `schema`, `quota-usage`).
- `fm serve` starts a **local OpenAI-compatible Chat Completions server** (models: `system` =
  on-device, `pcc` = Private Cloud Compute).
- Requirements: Apple Silicon, macOS 27+ (image input is new in 27), Apple Intelligence enabled.
  Intel Macs unsupported. Apple published **no third-party benchmarks**; the on-device model is
  small, so quality trails cloud Claude/GPT-4o and large MLX models — position it as the
  free/private/offline option, not the top-quality one.

Sources: [WWDC26 FM framework](https://developer.apple.com/videos/play/wwdc2026/241/) ·
[apple/python-apple-fm-sdk](https://github.com/apple/python-apple-fm-sdk) ·
[fm CLI + Python SDK (WWDC26 334)](https://developer.apple.com/videos/play/wwdc2026/334/) ·
[3rd-gen AFM](https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models)

---

## What was tested on this machine (empirical)

| # | Test | Result |
|---|------|--------|
| 1 | `sw_vers` / `uname -m` | macOS 27.0 (`26A5378j`), arm64 ✅ |
| 2 | `pip install apple-fm-sdk` into `imagedescriber/.venv` | installs (v0.2.1); **builds from source** — compiles a Swift dylib via `swift build` ✅ |
| 3 | `SystemLanguageModel().is_available()` | `(True, None)` ✅ |
| 4 | SDK **text** generation | ✅ "Hello, I'm Apple's foundation model." |
| 5 | SDK **image** generation (`ImageAttachment` + `respond`) | ❌ **SIGSEGV** |
| 6 | `/usr/bin/fm respond --model system --image coffee_desk.jpg --text ...` | ✅ "An illustration of a coffee cup, a pen, and a notebook on a wooden surface." |
| 7 | `/usr/bin/fm serve` + OpenAI `chat/completions` with base64 `image_url` | ✅ "The image depicts a cartoon illustration of a notebook, a pen, and a cup of coffee on a wooden surface." (253→27 tokens, 5.5s) |

### The SDK image crash (test 5) — root cause
- Crash: `EXC_BAD_ACCESS / KERN_INVALID_ADDRESS at 0x0` (null-pointer deref) inside the SDK's
  bundled `libFoundationModels.dylib`, in Swift `ComposedPrompt.add(attachmentFromPath:label:)`,
  called from `prompt.py:167` → `FMComposedPromptAddAttachment`.
- **Not our toolchain.** The SDK's `build_backend.py` enables image code only when
  `xcrun --sdk macosx --show-sdk-version >= 27` (adds `-DFM_HAS_MACOS_27_SDK`). Built correctly
  against **Xcode 27** (`/Applications/Xcode-beta.app`, Swift 6.4, SDK 27.0) — a clean manual
  `swift build` reproduces the same crash. (The dylib's `sdk 26.0` Mach-O stamp is a red herring —
  it just reflects `Package.swift`'s `.macOS(.v26)` pin, not the SDK used.)
- **Not the input.** Reproduced with the shipped JPEG, a freshly written 64×64 PNG, and an explicit
  `label`. ctypes `argtypes`/`restype` on the binding are correct.
- **Likely cause:** a bug in `apple-fm-sdk` 0.2.1's image binding, probably specific to Python 3.14
  and/or this macOS 27 **beta seed**. Worth re-testing when the SDK updates or on a release build of
  macOS 27.

### Why `fm serve` is the winner (test 7)
- Endpoint: `http://127.0.0.1:<port>/v1/chat/completions`, model `system`, no auth.
- Accepts the standard `messages` array with a `text` part and an `image_url` part carrying a
  `data:image/jpeg;base64,...` URL — **byte-for-byte the format IDT's `OpenAIProvider` already
  builds** (`imagedescriber/ai_providers.py`, `OpenAIProvider.describe_image`, ~line 636, which
  already resizes to ≤1600px and re-encodes JPEG q85). HEIC is therefore already handled upstream.
- Behaves like Ollama (a localhost model server) — a pattern IDT already supports end to end.
- No Swift build, no ctypes, no PyInstaller native bundling, no Xcode-27-to-ship requirement.

---

## Recommended design (for a future implementation session)

Add a provider keyed `apple` / display "Apple Intelligence (on-device)". Mirror how IDT talks to
Ollama, reusing the OpenAI-compatible client.

- **GUI layer** (`imagedescriber/ai_providers.py`): new `AIProvider` subclass whose
  `describe_image()` POSTs to the local `fm serve` endpoint using the same base64 `image_url`
  payload as `OpenAIProvider` (factor out the shared payload builder). `is_available()` =
  `platform.system()=="Darwin"` AND `shutil.which("fm")` (or `/usr/bin/fm`) present AND
  `fm available` reports ready. Register singleton + entries in `get_available_providers()` /
  `get_all_providers()`.
- **CLI layer** (`idt_core/providers/`): analogous `BaseProvider` subclass reusing
  `openai_provider.py`'s request shape against the local endpoint; add a branch in
  `cli/main.py:_make_provider` (and the duplicate in `cli/guide.py`).
- **Server lifecycle** — decide one of:
  - **(a) Require the user to run `fm serve`** (simplest; exactly the Ollama model — IDT just
    connects to a configured host/port).
  - **(b) IDT auto-spawns `fm serve`** on a free port, health-checks `/v1/models`, and shuts it
    down on exit (more seamless; more code + failure modes).
- **GUI selection surfaces** (hardcoded `wx.Choice` lists — not registry-driven): add the option +
  a `populate_models*` branch (single model id `system`, optionally `pcc`) in
  `imagedescriber/dialogs_wx.py` (~882, ~478, `populate_models` ~568, `populate_models_for_provider`
  ~1003, hint text ~288/299) and `imagedescriber/chat_window_wx.py` (~122, ~217, ~1303). No API-key
  dialog entry needed.
- **No new build/bundling** for the CLI path — it shells out to the OS `fm`. (If we ever revive the
  Python-SDK path, that's when Xcode 27 + `collect_all('apple_fm_sdk')` become necessary.)

### Approach rejected
- **`apple-fm-sdk` Python package** (the original approved plan): broken image path on this machine
  (SIGSEGV). Revisit only after an SDK fix.
- **`fm respond` subprocess per image**: works (test 6) and is simplest, but cold-spawns a process
  per image, gives no token counts, and needs explicit HEIC→JPEG. Acceptable fallback if we want to
  avoid any server lifecycle; `fm serve` is preferred for warm-model throughput + code reuse.

---

## What was NOT tested / open questions
- Release (non-beta) build of macOS 27 — the SDK crash may be beta-specific.
- The SDK image path on Python 3.11–3.13 (only 3.14 was available here). Could isolate whether it's
  a 3.14 binding issue.
- `fm respond`/`fm serve` with HEIC input directly (IDT converts to JPEG first anyway, so moot for
  the recommended path).
- `pcc` (Private Cloud Compute) model quality/latency for images.
- Concurrency/throughput of `fm serve` under batch load; quota behavior (`fm quota-usage`).
- Whether `fm` is guaranteed present on all macOS 27 installs vs. gated on Apple Intelligence being
  enabled/downloaded.

## Environment changes made this session (all reverted)
- Installed then **uninstalled** `apple-fm-sdk` in `imagedescriber/.venv`. Its build bumped
  `setuptools` to 83.0.0 (torch prefers <82); verified `torch`, `mlx_vlm`, `wx` still import fine.
- No repo files modified.
