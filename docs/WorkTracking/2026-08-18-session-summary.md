# 8/18/2026 — Alt mnemonics on Windows

Reported: in IDT Chat on Windows, **Alt+C moved focus to the attachments list
instead of opening the Chat menu.**

## Root cause

wx runs a frame's child panel through `IsDialogMessage` before the frame
handles `WM_SYSCHAR`. A mnemonic on a panel control therefore answers
Alt+letter **before the menu bar does** — so on Windows the menu titles and
every `&` in the window share one namespace, and the window wins.

`Atta&chments` claimed Alt+C, so `&Chat` was unreachable. `&Conversations`
claimed it too, so the two also fought each other, and `Conversation &history`
took Alt+H from `&Help` the same way.

This is the exact mirror of the Cmd+A bug fixed in April: there, wxOSX turned
a `&` in a button label into a Command key equivalent that outranked the menu
bar. Same shape — a control beating the menu — on the other platform.

## Why the tests were green

`test_menu_shortcuts.py` covered accelerators (`Ctrl+` chords) thoroughly, and
covered the macOS Command-equivalent trap. Nothing in it looked at what a `&`
does on **Windows**. Its `_mnemonic_controls()` helper even collects button
labels — but only to assert the app calls `clear_command_key_equivalents()`,
which is a macOS concern. So a letter could be claimed twice, or taken from
the menu bar, with every test passing.

## Changed

**Fixes** — all of them one-character label moves; no accelerator changed.

| File | What |
| --- | --- |
| `chatapp/chat_app_wx.py` | `Attachme&nts` (N), `Conversati&ons` (O), `Conversation h&istory` (I). `_build_ui` now documents that F/E/C/V/H belong to the menu bar. |
| `imagedescriber/imagedescriber_wx.py` | Nine letters claimed twice inside a menu: `Cu&t`, `Workspace S&tatistics`, `Update &Image List`, `Chat &with AI Model`, `Describe Video with &AI`, `Re&name Item`, `Copy Image + Descrip&tion`, `&Find Images`, `AI I&nfo`, `Op&enAI Usage Dashboard`, `P&references`. |
| `imagedescriber/dialogs_wx.py` | Three dialogs with a repeated letter: `Oldest onl&y`, `All &descriptions combined`, `Embed into &original files`, `c&ustom prompt`. |
| `chatapp/chat_app_wx.py` | `ApiKeysDialog` builds one `&Remove` button per provider — one string, three live buttons on Alt+R. Mnemonic dropped; Tab and the accessible name identify it. |
| `imagedescriber/dialogs_wx.py` | `ProcessingOptionsDialog` had the tab `&General` and the checkbox `&Geocode…` on that page both on Alt+G. Now `Ge&ocode`. |

**Documentation**

- **New `docs/KEYBOARD_SHORTCUTS.md`** — every accelerator and every Alt
  mnemonic in both GUIs, on both platforms, plus the chords the operating
  systems have already claimed and the rules a new shortcut must clear.
- `docs/USER_GUIDE.md` Appendix D had two accelerators that never matched the
  source: Export HTML Gallery is `Ctrl+Shift+H` (listed as `Ctrl+Shift+G`) and
  Edit Prompts is `Ctrl+Shift+P` (listed as `Ctrl+P`, which is Print and was
  deliberately vacated). Corrected in all six places, and the appendix now
  points at the full reference.
- `CLAUDE.md` and `CHANGELOG.md` updated.

**Tests** — two layers, because each catches what the other cannot.

- `pytest_tests/unit/test_mnemonics.py` (21 tests, source-level, no display):
  no control takes a menu bar letter; no two controls in a window share one;
  no menu repeats one; no dialog repeats one. Parameterised over every
  `wx.Dialog` subclass in three files.
- `pytest_tests/gui/test_alt_mnemonics_windows.py` (6 tests, Windows-only,
  builds the real frames): reads `GetLabel()` off live widgets, so it sees
  labels the app writes at runtime. That matters here — the attachments label
  is rewritten by `_refresh_attachments`, so the mnemonic users actually met
  came from there, not from the constructor, and an AST-based check alone
  would have missed it.

## Validation workflow

A 22-agent workflow re-checked all **184 shortcuts** against the source —
six surfaces (both menu bars, the chat window, ImageDescriber's menus, and
every dialog), each finding adversarially verified by a second agent told to
refute it. 16 candidate defects, 6 confirmed, 10 refuted.

What it caught that neither test layer did:

- **Two live collisions**, both shapes a source scan cannot see: a widget
  built in a **loop** (`ApiKeysDialog`'s three `&Remove` buttons), and a
  **notebook tab title** (`&General` vs the `&Geocode` checkbox on that page).
  Fixed, and `test_mnemonics.py` now understands both — it counts looped
  widgets as multiple claims and reads `AddPage` titles. Its label-identity
  rule had to be tightened too: it collapsed `&General` and `&Geocode…` into
  one control because they share a prefix.
- **Nine undocumented single-key shortcuts** in ImageDescriber's
  `on_key_press` char hook: bare `P R M C F Z`, `F2`, `Ctrl+S`, `Ctrl+V`. The
  doc claimed to list every shortcut and did not. Now documented, with the
  three consequences that fall out of them (see below).

The 10 refuted were mostly style ("this menu item has no mnemonic") or claims
that dissolved on a second read.

## Verified

- Both new test files fail as intended when the bug is reintroduced. Restoring
  `Atta&chments` produced 3 failures naming the menu it steals:
  `'Atta&chments: none' takes Alt+C from the '&Chat' menu`.
- Live probe of both frames: IDT Chat has menu bar F/E/C/V/H and controls
  O/I/M/Y/N/S/T/A/R — disjoint, no repeats. ImageDescriber has 7 menus, no
  repeated letter in any menu or submenu, and no control mnemonics at all.
- Full suite: **1679 passed, 0 failed, 34 skipped.** Three tests were failing
  before this session and are fixed here (below); none of the three had
  anything to do with mnemonics.

## The three failing tests

All three failed for the same underlying reason — they read the *developer's*
environment instead of pinning it — which is why they were green on CI and red
on this machine.

- `test_chat_app_smoke.py::test_streaming_does_not_announce_each_chunk` was
  the real one. `ChatFrame` calls `SpeechSettings.load()`, which reads the
  running user's own config; `_finish_turn` deliberately skips `_announce`
  when speech is enabled and `speaker.speak()` succeeds, so a reply is not
  read twice. With read-aloud turned on there were no announcements to count.
  The `frame` fixture now pins `speech_settings.enabled = False`, and two new
  tests cover the branch that was previously left to ambient config: speech-on
  suppresses the announcement, and a speech engine that *fails* still
  announces.
- The two `test_ai_providers_model_listing.py` failures were missing SDKs
  (`anthropic`, `openai`), not defects — the providers return `[]` by design
  without them, which reads as a sorting regression. Both now
  `pytest.importorskip` the SDK, so they skip honestly here and run for real
  on CI where the requirements are installed.

## Flagged, not changed

`on_key_press` binds bare letters that **take type-ahead away from the
workspace tree and the description list**. Both controls jump to the next item
starting with the letter you type; while either has focus, `C` opens the chat
window instead. The handler says it is matching Qt6 behaviour, so it is
deliberate — but it is a real cost for keyboard and screen reader users, and
worth a decision rather than a silent fix. Documented in
`KEYBOARD_SHORTCUTS.md`; no behaviour changed.

Two smaller ones in the same handler, also documented rather than changed:
`F2` and the bare letters are not platform-gated, so `F2` renames on macOS
even though the menu accelerator is Windows-only; and `Ctrl+V` outside a text
field pastes a clipboard *image* rather than performing Edit > Paste.

## Not done

- **No build, no exe smoke test.** These are label-string changes with no
  import or path implications, but the frozen apps were not rebuilt.
- **Not tested on macOS.** Alt mnemonics do not exist there, so the change is
  a no-op by construction — but that is reasoning, not a run.
- **No key was physically pressed.** The runtime tests read what the window
  claims, not what Windows dispatches. `wx.UIActionSimulator` was not used:
  verifying a menu opened means driving a modal menu loop, which is exactly
  the kind of test that passes vacuously.
- **ImageDescriber's main window, chat window and viewer still carry no
  mnemonics at all.** That is a gap, not a conflict, and was left alone.
  Adding them means picking outside F/E/P/D/V/T/H.
