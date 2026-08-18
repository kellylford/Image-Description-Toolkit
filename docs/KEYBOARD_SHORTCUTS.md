# Keyboard Shortcuts

Every shortcut in **IDT Chat** and **ImageDescriber**, on both platforms.

These apps are built for keyboard and screen reader use, so a shortcut that
quietly does the wrong thing is a real defect rather than a rough edge. This
file is the reference; `pytest_tests/unit/test_menu_shortcuts.py` and
`pytest_tests/unit/test_mnemonics.py` are what keep it true.

*Last verified against the source: 8/18/2026.*

## How the two platforms differ

There are two separate shortcut systems, and a single source string feeds both.

**Accelerators** are the `Ctrl+` chords spelled after a tab in a menu label
(`"&New Chat\tCtrl+N"`). wx maps every one of them to **Command** on macOS, so
one string has to clear both platforms' conventions at once. Where the right
answer differs, the app picks per platform at build time — those rows are
marked below.

**Mnemonics** are the `&` in a label (`"&File"`, `"&Send"`). On **Windows**
they are the Alt keys: Alt+F opens the File menu, Alt+S presses Send. On
**macOS** there is no Alt-mnemonic system at all — but wxOSX turns a `&` in a
*button* label into a **Command** key equivalent on the NSButton, and AppKit
offers those to the key window before the menu bar. Both apps call
`clear_command_key_equivalents` at startup to take those chords back, which is
why the Alt letters below are Windows-only and cost nothing on a Mac.

Two things collide on Windows, and both have shipped broken:

1. **A control outranks the menu bar.** wx runs a frame's child panel through
   `IsDialogMessage` before the frame ever sees `WM_SYSCHAR`, so a mnemonic on
   a panel control answers Alt+letter *first* and the menu never opens.
2. **A repeated letter is not a shortcut.** Two items in one menu — or two
   controls in one window — on the same letter makes Alt+letter cycle the
   highlight and wait for Enter.

So in a window with a menu bar, the menu titles own their letters and nothing
in the window may take one; and no letter is used twice anywhere in the same
window, menu, or dialog.

---

# IDT Chat (`chatapp/chat_app_wx.py`)

## Accelerators

| Command | Windows | macOS | Notes |
| --- | --- | --- | --- |
| **File** |
| New Chat | `Ctrl+N` | `Cmd+N` | |
| Delete Chat | — | — | Contextual `Delete`; see below |
| Export Conversation… | `Ctrl+Shift+E` | `Cmd+Shift+E` | Not `Cmd+E` — that is "use selection for find" on macOS |
| Settings… | `Ctrl+,` | `Cmd+,` | macOS supplies the key via the application menu (`wx.ID_PREFERENCES`) |
| API Keys… | — | — | |
| Close Window | — | `Cmd+W` | macOS only; with one window it is the same as quitting |
| Exit | `Ctrl+Q` | `Cmd+Q` | macOS supplies the key via the application menu (`wx.ID_EXIT`) |
| **Edit** |
| Undo | `Ctrl+Z` | `Cmd+Z` | |
| Redo | `Ctrl+Y` | `Cmd+Shift+Z` | Per platform |
| Cut | `Ctrl+X` | `Cmd+X` | |
| Copy | `Ctrl+C` | `Cmd+C` | Standard Copy; falls back to the transcript message |
| Paste | `Ctrl+V` | `Cmd+V` | |
| Select All | `Ctrl+A` | `Cmd+A` | |
| Copy Message | — | — | Copy already does this when the transcript has focus |
| Copy Whole Conversation | `Ctrl+Shift+C` | `Cmd+Shift+C` | |
| **Chat** |
| Send Message | `Ctrl+Return` | `Cmd+Return` | Works from anywhere in the window |
| Stop Response | `Ctrl+.` | `Cmd+.` | Also stops speech |
| Regenerate Response | `Ctrl+R` | `Cmd+R` | |
| Attach Files… | `Ctrl+Shift+A` | `Cmd+Shift+A` | |
| Paste Image | `Ctrl+Shift+V` | `Cmd+Shift+V` | |
| Change Model… | `Ctrl+Shift+M` | `Cmd+Shift+M` | Not `Cmd+M` — that minimises on macOS |
| Set System Prompt… | `Ctrl+Shift+P` | `Cmd+Shift+P` | |
| Use Web Search | `Ctrl+Shift+K` | `Cmd+Shift+K` | Check item. Not `Cmd+Shift+W` — close-window family on macOS |
| **View** |
| Read Last Response | `Ctrl+Shift+R` | `Cmd+Shift+R` | |
| Token Usage | `Ctrl+T` | `Cmd+T` | |
| Announce full / summary / silent | — | — | Radio items |
| **Help** |
| Keyboard Shortcuts | `F1` | `Cmd+?` | `F1` is also honoured on macOS |
| About | — | — | |

## Contextual keys

Handled in `on_char_hook`, which can see focus. None of these are menu
accelerators, because a menu accelerator is application-wide — binding plain
`Delete` would take the key away from every text field in the window.

| Key | Where | Does |
| --- | --- | --- |
| `Enter` | Message box | Send |
| `Shift+Enter` | Message box | New line |
| `Enter` | Conversation list | Open that conversation |
| `Enter` | Transcript | Read the message again |
| `Delete` | Conversation list | Delete that conversation |
| `Delete` | Attachments list | Remove that attachment |

## Alt mnemonics (Windows only)

| Alt key | Goes to |
| --- | --- |
| `Alt+F` | File menu |
| `Alt+E` | Edit menu |
| `Alt+C` | **Chat menu** |
| `Alt+V` | View menu |
| `Alt+H` | Help menu |
| `Alt+O` | Conversati**o**ns list |
| `Alt+I` | Conversation h**i**story (transcript) |
| `Alt+M` | Selected **m**essage |
| `Alt+Y` | **Y**our message (the input box) |
| `Alt+N` | Attachme**n**ts list |
| `Alt+S` | **S**end button |
| `Alt+T` | S**t**op button |
| `Alt+A` | **A**ttach Files button |
| `Alt+R` | **R**emove Attachment button |

Within an open menu:

| Menu | Letters |
| --- | --- |
| File | **N**ew Chat, **D**elete Chat, **E**xport Conversation, **S**ettings, API **K**eys, **C**lose Window *(macOS)*, E**x**it |
| Edit | **U**ndo, **R**edo, Cu**t**, **C**opy, **P**aste, Select **A**ll, Copy **M**essage, Copy W**h**ole Conversation |
| Chat | **S**end Message, S**t**op Response, **R**egenerate, **A**ttach Files, **P**aste Image, Change **M**odel, Set S**y**stem Prompt, Use **W**eb Search |
| View | **R**ead Last Response, **T**oken Usage. The three Announce radio items carry no mnemonic — arrow keys only |
| Help | **K**eyboard Shortcuts, **A**bout |

> **Fixed 8/18/2026.** `Atta&chments` and `&Conversations` both claimed C and
> beat the `&Chat` menu to it, so Alt+C moved focus to the attachments list
> instead of opening the menu. `Conversation &history` took Alt+H from `&Help`
> the same way. The three labels now use O, I and N.

---

# ImageDescriber (`imagedescriber/imagedescriber_wx.py`)

## Accelerators

| Command | Windows | macOS | Notes |
| --- | --- | --- | --- |
| **File** |
| New Workspace | `Ctrl+N` | `Cmd+N` | |
| Open Workspace (.idtw)… | `Ctrl+O` | `Cmd+O` | |
| Save Workspace | `Ctrl+S` | `Cmd+S` | |
| Save Workspace As… | `Ctrl+Shift+S` | `Cmd+Shift+S` | |
| Load Directory | `Ctrl+L` | `Cmd+L` | |
| Refresh Folder from Disk… | `Ctrl+Shift+R` | `Cmd+Shift+R` | |
| Load Images From URL… | `Ctrl+U` | `Cmd+U` | |
| Import Workflow (to Workspace)… | — | — | |
| Export Descriptions… | — | — | |
| Embed Descriptions into Images… | — | — | |
| Export HTML Gallery… | `Ctrl+Shift+H` | `Cmd+Shift+H` | |
| Workspace Statistics… | `Ctrl+I` | `Cmd+I` | |
| Open Workflow Result (Viewer Mode)… | — | — | |
| Close Window | — | `Cmd+W` | macOS only |
| Exit | `Ctrl+Q` | `Cmd+Q` | macOS supplies the key via the application menu |
| **Edit** |
| Undo | `Ctrl+Z` | `Cmd+Z` | |
| Redo | `Ctrl+Y` | `Cmd+Shift+Z` | Per platform |
| Cut | `Ctrl+X` | `Cmd+X` | |
| Copy | `Ctrl+C` | `Cmd+C` | |
| Paste | `Ctrl+V` | `Cmd+V` | Outside a text field the char hook takes it first and pastes an *image* — see below |
| Select All | `Ctrl+A` | `Cmd+A` | |
| **Process** |
| Process Current Image | `P` | `P` | Bare letter — see [Contextual keys](#contextual-keys-1) |
| Process Undescribed in Selected Folder | — | — | |
| Redescribe All in Selected Folder | — | — | |
| Process Undescribed Images (Entire Workspace) | — | — | |
| Redescribe All Images (Entire Workspace) | — | — | |
| Show Batch Progress | — | — | |
| Stop All Processing | `Ctrl+.` | `Cmd+.` | |
| Update Image List | `F5` | `Cmd+R` | Per platform — `F5` is a hardware key on a Mac |
| Refresh AI Models | — | — | |
| Chat with AI Model | `Ctrl+T` | `Cmd+T` | Also bare `C` |
| Convert HEIC Files… | — | — | |
| Extract Video Frames… | — | — | |
| Describe Video with AI… | — | — | |
| Rename Item | `F2` | `F2` | The *menu accelerator* is Windows-only, because `F2` is a hardware key on a Mac. The char hook honours the key on both. Also bare `R` |
| **Descriptions** |
| Add Manual Description | `M` | `M` | Bare letter |
| Ask Followup Question | `F` | `F` | Bare letter |
| Edit Description… | — | — | |
| Delete Description | — | — | |
| Copy Description | — | — | |
| Copy Image Path | — | — | |
| Copy Image | — | — | |
| Copy Image + Description | — | — | |
| Show All Descriptions… | — | — | |
| **View** |
| Application Mode ▸ | — | — | Submenu |
| Filter: All Items | `Ctrl+Shift+A` | `Cmd+Shift+A` | |
| Filter: Described Only | `Ctrl+Shift+D` | `Cmd+Shift+D` | |
| Filter: Undescribed Only | `Ctrl+Shift+U` | `Cmd+Shift+U` | |
| Filter: Videos Only | — | — | |
| Filter: Chats Only | — | — | |
| Show Image Previews | — | — | |
| Find Images… | `Ctrl+F` | `Cmd+F` | |
| **Tools** |
| Edit Prompts… | `Ctrl+Shift+P` | `Cmd+Shift+P` | Not `Ctrl+P` — that is Print on both platforms |
| Configure Settings… | `Ctrl+Shift+C` | — | Windows label |
| Preferences… | — | `Cmd+,` | macOS label; the application menu supplies the key |
| Install Ollama… | — | — | |
| Install FFmpeg (for video GPS)… | — | — | |
| Export Configuration… | — | — | |
| Import Configuration… | — | — | |
| AI Info ▸ Ollama Models… | — | — | Submenu |
| AI Info ▸ OpenAI Usage Dashboard… | — | — | |
| AI Info ▸ Claude Usage Dashboard… | — | — | |
| AI Info ▸ MLX Community Models… | — | — | |
| **Help** |
| User Guide… | `F1` | `Cmd+?` | Per platform |
| Report an Issue… | — | — | |
| Check for Updates… | — | — | |
| Automatically Check for Updates | — | — | Check item |
| About | — | — | |

## Alt mnemonics (Windows only)

The menu bar is `Alt+F` File, `Alt+E` Edit, `Alt+P` Process, `Alt+D`
Descriptions, `Alt+V` View, `Alt+T` Tools, `Alt+H` Help. Within an open menu:

| Menu | Letters |
| --- | --- |
| File | **N**ew, **O**pen, **S**ave, Save Workspace **A**s, **L**oad Directory, Refresh **F**older, **U**RL, **I**mport Workflow, **E**xport Descriptions, Em**b**ed, **H**TML Gallery, S**t**atistics, **W**orkflow Result, **C**lose Window *(macOS)*, E**x**it |
| Edit | **U**ndo, **R**edo, Cu**t**, **C**opy, **P**aste, Select **A**ll |
| Process | **C**urrent Image, Selected **F**older, Selected Fo**l**der (redescribe), **U**ndescribed, **R**edescribe All, **B**atch Progress, S**t**op All, Update **I**mage List, **M**odels, Chat **w**ith AI Model, **H**EIC, **V**ideo Frames, **A**I (describe video), Re**n**ame Item |
| Descriptions | **M**anual, **F**ollowup, **E**dit, **D**elete, **C**opy, **P**ath, **I**mage, Descrip**t**ion (image + description), **S**how All |
| View | **M**ode, **A**ll Items, **D**escribed, **U**ndescribed, **V**ideos, **C**hats, **I**mage Previews, **F**ind Images |
| Tools | **P**rompts, **C**onfigure Settings *(Windows)* / P**r**eferences *(macOS)*, **O**llama, **F**Fmpeg, E**x**port Config, **I**mport Config, AI I**n**fo |
| Help | **U**ser Guide, **R**eport an Issue, Up**d**ates, Chec**k** automatically, **A**bout |

> **Fixed 8/18/2026.** Nine letters were claimed twice and so did nothing on
> the first press: `&Cut`/`&Copy` on C, `&Save Workspace`/`Workspace
> &Statistics` on S, four pairs in Process (C, U, V, R), `&Delete
> Description`/`Copy Image + &Description` on D, `Show &Image
> Previews`/`Find &Images` on I, `&Import Configuration`/`AI &Info` on I, and
> `&Ollama Models`/`&OpenAI Usage` on O.

## Contextual keys

`ImageDescriberFrame.on_key_press` is bound to `EVT_CHAR_HOOK`, so these run
**before** any menu accelerator. They are suppressed while a text field has
focus (`_is_text_entry_focused`), and live everywhere else — which in practice
means the workspace tree and the description list.

| Key | Runs | Same as |
| --- | --- | --- |
| `P` | Process the current image | Process ▸ Process Current Image |
| `R` | Rename the selected item | Process ▸ Rename Item |
| `M` | Add a manual description | Descriptions ▸ Add Manual Description |
| `C` | Open the chat window | Process ▸ Chat with AI Model |
| `F` | Ask a followup question | Descriptions ▸ Ask Followup Question |
| `Z` | Auto-rename | *no menu item* |
| `F2` | Rename the selected item | Process ▸ Rename Item |
| `Ctrl+S` | Save the workspace | File ▸ Save Workspace |
| `Ctrl+V` | Paste an image from the clipboard | *no menu item* — **not** Edit ▸ Paste |

Three of these are worth knowing about when changing this code:

- **They are not platform-gated.** The Process menu drops the `F2` accelerator
  on macOS because F2 is a hardware key there, but the char hook does not, so
  `F2` still renames on a Mac. Same for the bare letters.
- **They outrank the menu.** `Ctrl+S` and `Ctrl+V` are claimed twice — by the
  Edit/File accelerator and by the hook — and the hook wins. `Ctrl+S` reaches
  the same handler either way, so it makes no difference. `Ctrl+V` does not:
  outside a text field it pastes a clipboard *image* into the workspace rather
  than performing Edit ▸ Paste.
- **They take the letter away from type-ahead.** A `wx.TreeCtrl` and a
  `wx.ListBox` both jump to the next item starting with the letter you type.
  While the tree has focus, `C` opens the chat window instead of jumping to
  the first item beginning with C. That is a deliberate Qt6-parity feature
  (the handler says so), not an accident — but it is a real cost for keyboard
  and screen reader users, and it is the reason to think twice before adding
  another bare letter here.

## Main-window controls

ImageDescriber's tree, list and buttons carry **no** mnemonics, so there are no
`Alt+letter` jumps into the window itself — only `Tab` and the menus. Same for
its in-app chat window (`chat_window_wx.py`) and the viewer
(`viewer_components.py`). This is a gap rather than a conflict: adding them
later means picking from the letters the menu bar does not already own
(anything outside F, E, P, D, V, T, H).

---

# Dialogs

Dialogs have no menu bar, so their controls own the whole Alt namespace.
`test_mnemonics.py` checks every `wx.Dialog` subclass in
`chatapp/chat_app_wx.py`, `imagedescriber/dialogs_wx.py` and
`imagedescriber/download_dialog.py` for a repeated letter.

Two shapes defeat a naive check, and both had shipped:

- **A widget built in a loop.** `ApiKeysDialog` creates one `&Remove` button
  per provider — one source string, three live buttons, all on Alt+R. The
  button carries no mnemonic now; Tab and its accessible name identify it.
- **A notebook tab.** `ProcessingOptionsDialog` had the tab `&General` and,
  on that very page, the checkbox `&Geocode…` — the `&` goes straight to the
  native tab control, so both answered Alt+G. The checkbox is `Ge&ocode` now.
  Its two pages draw from one namespace even though only one is visible.

`VideoExtractionDialog`, `RescanFolderDialog` and `ApiKeyDialog` carry no
mnemonics at all, so they are Tab-only where their siblings offer Alt jumps.
That is a gap rather than a conflict, and every letter in each is free.

---

# Adding a shortcut

An accelerator has to clear both platforms, because wx maps `Ctrl+` to
Command. Chords that are already spoken for:

| Chord | Already means |
| --- | --- |
| `Cmd+M` | Minimise window (macOS; wx puts it on the automatic Window menu) |
| `Cmd+W`, `Cmd+Shift+W` | Close window (macOS) |
| `Cmd+H` | Hide application (macOS) |
| `Cmd+Q`, `Cmd+,` | Quit, Settings — supplied by the macOS application menu |
| `Ctrl+P` / `Cmd+P` | Print, on both, and pressed reflexively |
| `Ctrl+Space` | Input-source switcher and Spotlight |
| `Ctrl+X/C/V/Z/A` | The focused control's editing keys — never repurpose them |
| `F1`, `F2`, `F5` | Windows keys; hardware keys on a Mac, so choose per platform |

`wx.ID_PREFERENCES`, `wx.ID_ABOUT` and `wx.ID_EXIT` are wiring, not
decoration: on macOS those items reach a handler only through the standard id,
and they must not repeat the accelerator the application menu already
supplies.

A mnemonic has to clear the window it lives in. In a frame with a menu bar,
start from the letters the menu titles do not own; then check no sibling
control and no item in the same menu already uses it.

Both rules are enforced by tests, which run without a display:

```bash
python -m pytest pytest_tests/unit/test_menu_shortcuts.py pytest_tests/unit/test_mnemonics.py -q
```
