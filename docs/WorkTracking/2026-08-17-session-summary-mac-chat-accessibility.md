# 2026-08-17 — IDT Chat on macOS: VoiceOver names, and shortcuts that collide

Two reports, both macOS, both about the standalone chat app:

1. Tabbing to any edit box or list box announces the *contents* but never the
   *name*. The labels are there — exploring with VoiceOver finds them — but
   nothing connects them to the control.
2. The shortcuts look like they are fighting platform standards, "cmd+a or
   ctrl+a for select all with attachments".

Both turned out to be real, and the second was worse than reported.

## 1. Nothing was named, because wx cannot name anything on macOS

`_set_accessible_name()` did two things: `SetName()`, and — for text controls
only — a custom `wx.Accessible` subclass. Neither reaches VoiceOver.

Measured directly against the Objective-C runtime on wxPython 4.3.1 /
wxWidgets 3.3.3, Apple Silicon:

| Control | `accessibilityLabel` before | Native class |
|---|---|---|
| `wx.TextCtrl` (single line) | `nil` | `wxNSTextField` |
| `wx.TextCtrl` (multi-line) | `nil` | `wxNSTextScrollView` → `wxNSTextView` |
| `wx.ListBox` | `nil` | `NSScrollView` → `wxNSTableView` |
| `wx.Choice` | `nil` | `wxNSPopUpButton` |
| `wx.Button` | `"Send"` | `wxNSButton` |
| `wx.CheckBox` | `"Read aloud"` | `wxNSButton` |

Buttons and checkboxes were fine all along — AppKit derives their accessible
name from the button title — which is exactly why the gap was easy to miss.
Everything a user tabs *into* was anonymous.

`SetAccessible()` is not a partial fix on macOS, it is nothing: it raises
`NotImplementedError`, which the existing code caught and ignored. The comment
above `_NamedAccessible` claiming "SetName() does not reach NSAccessibility for
text controls on macOS, so the name has to come from an overridden GetName" was
half right about the problem and wrong about the remedy.

**Fix:** new `shared/mac_accessibility.py` sets the name on the native view
through NSAccessibility, using ctypes — PyObjC is not a project dependency and
adding one to the frozen bundles for three selector calls is a bad trade. Every
entry point is a no-op off macOS, so Windows keeps `SetName` + `wx.Accessible`
exactly as it was.

One detail that matters: `GetHandle()` is not always the view VoiceOver lands
on. A multi-line `wx.TextCtrl` is a scroll view wrapping a text view, and a
`wx.ListBox` is a scroll view wrapping a table view. Labelling the scroll view
leaves the *focused* element anonymous, so the label goes on the `documentView`
when there is one. Verified by reading the label back for all six control types.

Also named for the first time: the provider and model pickers, the speech
engine and rate pickers, and the API key fields — all `wx.Choice` or
`wx.TextCtrl`, all previously relying on `name=`, which reaches nothing here.

## 2. The shortcuts

The report was about Select All. The cause was bigger: **the app had no Edit
menu with standard ids**, and on macOS that is not a cosmetic omission. Cocoa
dispatches `cut:` / `copy:` / `paste:` / `selectAll:` / `undo:` through menu
items. With no such items, Cmd+A, Cmd+V, Cmd+X and Cmd+Z do nothing in any
text field in the app — including the API key box, so a key could not be
pasted in.

And what the app *did* bind was worse: `Ctrl+C` meant "copy the selected
transcript message", application-wide, on both platforms. A selection in the
message box could not be copied out of it. That is a Windows bug too; it was
simply never noticed there because Cmd/Ctrl+C at least did *something*.

### Measured, not assumed

Firing the real `NSMenuItem` actions (what a key equivalent does) rather than
synthesising keystrokes:

- With a **text control** focused, a standard-id Edit item is handled natively
  and the wx handler never runs — paste into a frame control and into a *modal
  dialog's* field both worked, which is the API-keys case.
- With a **list** focused, nothing native claims `copy:`, so wx falls back to
  sending the command event and the handler does run.

That second line is what makes contextual Copy work for free: Cmd+C is a normal
Copy in a text box, and "copy the message I am on" in the transcript. The
handler still routes explicitly, because on Windows the accelerator reaches the
frame first and there is no native fallback to rely on.

Dumping the native menu also settled two guesses:

- **Cmd+M really is taken.** wx builds an automatic Window menu with Minimize
  on Cmd+M. `Ctrl+M` for Change Model was shadowing it.
- **Cmd+Q was bound twice.** The application menu's Quit *and* File > Exit both
  carried it. The application menu reaches `wx.ID_EXIT` / `wx.ID_ABOUT` /
  `wx.ID_PREFERENCES` handlers on its own (verified by firing those items), so
  the items now use those ids and stop spelling the accelerator out on macOS.
  wx does not *move* them out of File/Help — they appear in both places — but
  only one item answers to the chord.

### What changed

| Command | Was | Now | Why |
|---|---|---|---|
| Copy | `Ctrl+C` → copy selected message | `Ctrl+C` → `wx.ID_COPY`, falls back to the message | Cmd/Ctrl+C belongs to the focused control |
| Copy whole conversation | `Ctrl+Shift+C` | unchanged | |
| Copy message | `Ctrl+C` | no accelerator | Copy already does it on the transcript |
| Undo / Redo / Cut / Paste / Select All | *absent* | `Ctrl+Z` / `Ctrl+Shift+Z` (mac) or `Ctrl+Y` (win) / `Ctrl+X` / `Ctrl+V` / `Ctrl+A` | without these macOS has no text editing keys at all |
| Change model | `Ctrl+M` | `Ctrl+Shift+M` | Cmd+M is Minimize |
| Web search | `Ctrl+Shift+W` | `Ctrl+Shift+K` | Cmd+W / Cmd+Shift+W are Close |
| Export | `Ctrl+E` | `Ctrl+Shift+E` | Cmd+E is "use selection for find" |
| Settings | none | `Ctrl+,` on Windows; application menu on macOS | Cmd+, is already Settings there |
| Exit | `Ctrl+Q` | `Ctrl+Q` on Windows; application menu on macOS | Cmd+Q was bound twice |
| Close window | *absent* | `Ctrl+W`, macOS only | the system offers Cmd+W regardless |
| Keyboard shortcuts | `F1` | `F1` on Windows, `Cmd+?` on macOS (F1 still honoured) | F1 is a hardware key on a Mac |

Kept deliberately: `Ctrl+T` (token usage) — Cmd+T is Show Fonts, which only
exists in apps with a font panel; `Ctrl+Shift+V` (paste image) — Cmd+Shift+V is
paste-and-match-style, which needs rich text this app does not have;
`Ctrl+Shift+P` — Cmd+Shift+P is Page Setup, and nothing here prints.

Help > Keyboard Shortcuts now says "Cmd" on macOS instead of "Ctrl", which was
simply wrong text being read aloud to the people most likely to be reading it.

## Files changed

- `shared/mac_accessibility.py` — new. NSAccessibility naming via ctypes.
- `chatapp/chat_app_wx.py` — naming applied to every control; Edit menu; the
  standard-id wiring; contextual edit-command routing; regenerated shortcut
  help.
- `chatapp/chatapp.spec` — `shared.mac_accessibility` added to hiddenimports.
  The `shared/*.py` glob copies it as data; without the hidden import the
  frozen macOS build goes straight back to unlabelled controls.
- `pytest_tests/unit/test_chat_app_shortcuts.py` — new, no wx required.
- `pytest_tests/unit/test_chat_app_smoke.py` — VoiceOver naming, accelerator
  uniqueness, and edit-routing tests.

## Testing

**Ran: 1261 passed, 282 skipped, 1 pre-existing failure** (`test_entry_points ::
test_imagedescriber_launches`, which fails because wxPython is not installed in
this machine's project venv — unrelated to this change).

The 13 new `test_chat_app_shortcuts.py` tests are source-level on purpose: no
wx, no display, so they run on the Windows CI box, which is the only place a
Mac-only mistake would otherwise go unnoticed. **Verified non-vacuous** — six of
them were run against the pre-fix source and all six failed for the right
reason (Ctrl+M reserved, Ctrl+Shift+W reserved, Ctrl+Q double-bound, no
standard Edit ids, Ctrl+C not `wx.ID_COPY`, no application-menu ids).

### Not tested

- **VoiceOver itself.** The names are asserted by reading back the same
  `accessibilityLabel` VoiceOver reads, on every control type, and that was
  measured live before and after. Nobody has yet tabbed through the window with
  VoiceOver speaking. That is the one thing worth doing before this ships.
- **The new wx-level tests did not execute in this session.** Part way through,
  `wx.App()` began hanging in `_BootstrapApp` for *every* wx process on this
  machine — before the code changes, and equally for scripts that touch none of
  this. It happened right after a probe fired the application menu's Quit item,
  so it looks like a wedged window-server/session state rather than anything in
  the app. A logout/login (or restarting the Dock) should clear it; if IDT Chat
  itself will not launch, that is the reason, not this change. The tests that
  need a `wx.App` are written and will run wherever one can start.
- **Windows.** Not run at all this session. The changes that reach it are the
  Edit menu routing (new, and the fix for Ctrl+C there too), the moved
  accelerators, and `wx.ID_PREFERENCES`/`ID_ABOUT`/`ID_EXIT` on the File and
  Help items — all worth a pass with NVDA before release.
- **A frozen build.** `chatapp.spec` changed; no macOS `.app` was built.
