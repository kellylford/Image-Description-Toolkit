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

## 3. The same two problems in ImageDescriber

Asked to fix "this sort of issue" in the other apps. The CLI has no UI to fix,
so this is ImageDescriber. It had both problems and one more.

### 31 accessibility calls that had never done anything

`dialogs_wx.py` has a helper:

```python
def set_accessible_name(widget, name):
    if hasattr(widget, 'SetAccessibleName'):
        widget.SetAccessibleName(name)
```

**wxPython has no `SetAccessibleName`.** Nor `SetAccessibleDescription`. The
guard was always False, so all 31 calls did nothing — on Windows as much as on
macOS. Provider pickers, model pickers, the follow-up question box, the
processing-options tabs, the whole HTML gallery dialog: every one of them
*looked* carefully labelled in the source and was announced as nothing.

Fixed by making the helper set the name wx actually has (`SetName`, which is
what NVDA and Narrator read) plus the NSAccessibility label. The description
helper now sets the macOS accessibility help, which is the nearest real thing;
Windows has no wx-level equivalent, so it stays a no-op there and says so.

### Naming the rest

`apply_accessible_names(window)` walks a window tree and publishes every wx
name to NSAccessibility, skipping wx's own class-name defaults ("listBox",
"text") because announcing those is worse than silence. One call at the end of
the main window's construction covers it; `wx.StaticText` is left alone so its
own text is still what gets read.

For dialogs the call is installed once, as a hook on `Show`/`ShowModal`, rather
than at the end of each dialog's `__init__`. There are nineteen dialog classes;
the call has to land after the controls exist and before the dialog appears;
and the twentieth dialog somebody adds would not have it. The hook gets the
timing right by construction and cannot be forgotten.

Controls that carried no name at all were given one: the prompt editor's five
fields, the Configure dialog's generic per-setting editor (named for the
setting it is editing, since the visible label just says "Value:"), the
viewer's description pane, and two panes in the image detail dialog.

### A paste that could not work on macOS

ImageDescriber's chat window queues a clipboard image on Ctrl+V, from an
`EVT_CHAR_HOOK`. On macOS that hook never runs: the main window's Edit menu
owns Cmd+V, and Cocoa gives the key equivalent to the focused text control
before any key event reaches the dialog. Pasting a screenshot into a chat
silently did nothing there.

There is no way to win that key back — nor should the app try, since Cmd+V in a
text field must paste text. So the command got a **Paste Image button**, which
is reachable on both platforms and more discoverable with a screen reader than
a key nobody documented. The Ctrl+V path stays for Windows; both now go through
one method.

### Accelerators

| Command | Was | Now | Why |
|---|---|---|---|
| Edit Prompts | `Ctrl+P` | `Ctrl+Shift+P` | **Print**, on both platforms — the clearest Windows conflict in the app |
| Export HTML Gallery | `Ctrl+Shift+G` | `Ctrl+Shift+H` | Cmd+Shift+G is Find Previous, and this app has a Find |
| Exit | `Ctrl+Q` | `Ctrl+Q` on Windows only | the macOS application menu already supplies Cmd+Q for the same item |
| Undo / Redo | *absent* | `Ctrl+Z` / `Ctrl+Shift+Z` (mac) or `Ctrl+Y` (win) | Cmd+Z did nothing in any text field |
| Update Image List | `F5` | `F5` on Windows, `Cmd+R` on macOS | F5 is a hardware key on a Mac |
| Rename Item | *none* | `F2` on Windows | the Windows rename key, never bound |
| Save Workspace As | *none* | `Ctrl+Shift+S` | a standard that was going spare |
| Close Window | *absent* | `Cmd+W`, macOS only | the system offers it regardless |
| User Guide | *none* | `F1` on Windows, `Cmd+?` on macOS | the Help menu had no help key |

Left alone after checking: `Ctrl+T` (chat), `Ctrl+I` (statistics — Cmd+I is Get
Info, which is what it does), `Ctrl+U` (load from URL), `Ctrl+L` (load
directory), `Ctrl+Shift+A/D/U` (filters). Each shadows a convention that only
exists in apps with rich text or a font panel, which this is not.

The Edit menu's Cut/Copy/Paste/Select All already routed to the focused control
via `FindFocus()`, so those needed nothing beyond Undo and Redo joining them.

### One bug found by adding to a path

Adding Cmd+W meant binding a second menu item to the close handler, which is
when the existing one turned out to be wrong: File > Exit was bound straight to
`on_close`, the `EVT_CLOSE` handler, which ends with

```python
if event.CanVeto():
    event.Veto()
```

A menu item delivers a `wx.CommandEvent`, which has no `CanVeto`. So choosing
Exit and then cancelling the unsaved-changes prompt raised `AttributeError`
inside the handler — swallowed, the way wx always swallows them — and took the
"cancelled but cannot veto, force the close" fallback with it. Both items now
go through `Close()`, which posts a real close event.

## Files changed

- `shared/mac_accessibility.py` — new. NSAccessibility naming via ctypes:
  `set_accessible_name`, `set_accessible_help`, `apply_accessible_names` (the
  tree walk) and `install_dialog_naming` (the Show/ShowModal hook). Deliberately
  wx-free — it takes the wx module as an argument where it needs one — so the
  selection logic can be tested without wx or a display.
- `chatapp/chat_app_wx.py` — naming applied to every control; Edit menu; the
  standard-id wiring; contextual edit-command routing; regenerated shortcut
  help; the dialog hook installed at startup.
- `imagedescriber/imagedescriber_wx.py` — Undo/Redo, the accelerator moves, the
  window-tree naming call and the dialog hook.
- `imagedescriber/dialogs_wx.py` — the two dead helpers made real, which is what
  revives 31 call sites.
- `imagedescriber/chat_window_wx.py` — Paste Image button, clipboard logic
  extracted, provider and model pickers named.
- `imagedescriber/prompt_editor_dialog.py`, `configure_dialog.py`,
  `viewer_components.py` — names for controls that had none.
- `chatapp/chatapp.spec`, `imagedescriber/imagedescriber_wx.spec` —
  `shared.mac_accessibility` added to hiddenimports. Without it the frozen
  macOS builds go straight back to unlabelled controls.
- `pytest_tests/unit/test_menu_shortcuts.py` — was
  `test_chat_app_shortcuts.py`; now parametrised over both apps.
- `pytest_tests/unit/test_mac_accessibility.py` — new, no wx required.
- `pytest_tests/unit/test_chat_app_smoke.py` — VoiceOver naming, accelerator
  uniqueness, and edit-routing tests.

## Testing

**Ran: 1288 passed, 286 skipped, 1 pre-existing failure** (`test_entry_points ::
test_imagedescriber_launches`, which fails because wxPython is not installed in
this machine's project venv — unrelated to these changes).

The 27 `test_menu_shortcuts.py` and 12 `test_mac_accessibility.py` tests are
source-level or stub-driven on purpose: no wx, no display, so they run on the
Windows CI box, which is the only place a Mac-only mistake would otherwise go
unnoticed. `IS_MACOS` is patched *on* rather than skipped around, so the naming
logic is exercised on every platform.

**Verified non-vacuous** against the pre-fix sources:

- IDT Chat, six checks: Ctrl+M reserved, Ctrl+Shift+W reserved, Ctrl+Q
  double-bound, no standard Edit ids, Ctrl+C not `wx.ID_COPY`, no
  application-menu ids.
- ImageDescriber, six checks: Ctrl+P on Print, no Undo/Redo ids, Ctrl+Q
  double-bound, no help key, Ctrl+Shift+S missing, F5 not per-platform.

All twelve failed on the old code and pass on the new.

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
- **Windows.** Not run at all this session. What reaches it: the Edit menu
  routing in IDT Chat (new, and the fix for Ctrl+C there too), Undo/Redo and the
  moved accelerators in ImageDescriber, `F2` for rename, `Ctrl+Shift+S` for
  Save As, and — the big one — 31 `set_accessible_name()` calls in
  `dialogs_wx.py` that now do something on Windows for the first time. That
  last one is worth a pass with NVDA before release: those dialogs have never
  been heard with real names.
- **The ImageDescriber dialog hook against real wx.** `install_dialog_naming`
  patches `wx.Dialog.Show`/`ShowModal`; it is covered by stub-driven tests, and
  the wx-level behaviour has not been exercised because no `wx.App` would start
  here.
