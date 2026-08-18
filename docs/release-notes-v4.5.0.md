# Image Description Toolkit v4.5.0

**Image Description Toolkit (IDT) writes text descriptions of your images, using AI, in bulk.**

Point it at a folder of photos and it produces a description of each one. Descriptions
can be written for alt text, for cataloging, for making an archive searchable, or for
anyone who needs to know what is in a picture without seeing it.

It runs entirely on your own machine if you want it to. No account, no subscription,
no uploading your photos anywhere.

---

## Download

| File | Platform | What it is |
|---|---|---|
| **`ImageDescriptionToolkitSetup-4.5.0-windows.exe`** | Windows 10/11, 64-bit | **Start here.** Installs all three applications. |
| **`IDT-4.5.0-macos-arm64.dmg`** | macOS, Apple Silicon | **Start here.** Contains all three. |
| `idt-4.5.0-windows-x64.exe` | Windows | Just the command-line tool, no installer |
| `ImageDescriber-4.5.0-windows-x64.exe` | Windows | Just the image GUI, no installer |
| `IDTChat-4.5.0-windows-x64.exe` | Windows | Just the chat client, no installer |
| `idt-4.5.0-macos-arm64.tar.gz` | macOS | Just the command-line tool |
| `SHA256SUMS.txt` | — | Checksums, if you want to verify your download |

No Python, no dependencies. The Windows installer is signed; the macOS build is signed
and notarized by Apple.

The standalone `.exe` files are for people who want one tool and no installer. Most
people want the installer, which puts all three on the Start menu.

---

## New in 4.5: IDT Chat, a chat client built for screen readers

**IDT Chat is new in this release, and it is not an image tool.** It is a
general-purpose chat client for Ollama, Claude and OpenAI that happens to ship with an
image toolkit, and it exists because mainstream chat applications are awkward to use
with a screen reader.

Three decisions shape it:

- **Streaming does not narrate.** Text accumulates silently and is announced once,
  complete, when the reply finishes. Reading a response token by token floods a screen
  reader and makes the app unusable; you can also choose to hear only a one-sentence
  summary, or nothing at all.
- **The conversation is a list, not a scrolling wall.** Each turn is one line naming
  who spoke, arrow keys move through it, and the full text of the highlighted turn
  appears in a pane you can select and copy from.
- **Everything has a key.** `Enter` sends, `Ctrl+Shift+A` attaches, `Ctrl+.` stops a
  reply in progress and silences it, `Ctrl+Shift+R` reads the last response again.

It also does the things a chat client should. Conversations save themselves after every
turn, so nothing is lost if it closes unexpectedly. You can switch model mid-conversation
without losing history, and each turn records which model produced it. Attachments cover
images for every provider and PDFs for Claude, and HEIC photos from an iPhone are
converted automatically because no provider reads HEIC. Token usage reports two numbers
that are genuinely different: what is in the model's context now, and what you have been
billed across the whole conversation.

On the Mac it can read replies aloud through a system voice; on Windows it can route
speech through JAWS or NVDA, or a Windows voice.

The same engine backs `idt chat` in the terminal, and conversations are stored as plain
JSON in `~/.idt/chats/` in the format ImageDescriber uses — so a conversation started in
one can be opened in the other.

**Full documentation:** [Part 7 of the User
Guide](https://kellylford.github.io/Image-Description-Toolkit/user-guide.html).

---

## New in 4.5: the model list is now your model list

Every place IDT offers you a Claude or OpenAI model, that list now comes from the
provider, using your own API key, rather than from a list built into the app.

This fixes a problem that was invisible until it bit you. The lists used to be written
into the code and updated by hand, which meant:

- A model released after your copy of IDT was built **did not appear at all**, no matter
  that your account could use it.
- A model the provider had retired **stayed on the list**, and only failed when you
  picked it and ran a job.

Now the pickers show what your account can actually use. On a real OpenAI account the
list went from 13 hardcoded entries to 45 — including several GPT-5.x models that
simply had no way to appear before.

Practical notes:

- **It does not slow anything down.** The list is cached for 24 hours and refreshed in
  the background, so pickers open instantly. `idt models` takes about a third of a
  second on a warm cache.
- **It still works offline and without an API key.** With no key, no network, or an
  unreachable provider, you get the built-in list exactly as before.
- **New models are labelled.** A model IDT has no details for shows as
  `new — details unknown`. It is fully usable; IDT just doesn't yet know its context
  window or price, so it budgets conservatively rather than guessing.
- **Your selected model is never silently changed.** If a provider withdraws the model
  you had chosen, it stays in the picker and is marked, rather than quietly moving you
  to a different one.
- `idt models --refresh` checks right now instead of waiting for the cache to expire.
- `idt models --all` shows everything the API reports. OpenAI's account list also
  contains speech, image-generation and embedding models, which cannot describe a
  picture; IDT hides those so the picker stays usable with a keyboard and screen reader.

**Also fixed in this release**

- `idt models` reported "no API key" for anyone whose key was stored in the Windows
  Credential Manager or in the config file, rather than in an environment variable.
  It now finds keys the same way every other command does.
- The batch and chat model pickers in ImageDescriber defaulted to `gpt-4o`, a legacy
  model, regardless of what you had configured.
- The context-window indicator in the chat window could disagree with the budget the
  app actually applied when trimming a long conversation.

---

## The three applications

IDT is three programs that share everything — the same AI providers, the same
settings, the same files on disk. Use whichever suits the moment; you can start work
in one and finish in another.

**ImageDescriber** — a desktop app. Load a folder, pick a model and a description
style, and watch descriptions appear. Review and edit them, browse your images, ask
follow-up questions about a picture in a chat window, and export when you're done.

**IDT Chat** — a standalone chat client for Ollama, Claude and OpenAI. **New in
4.5**, and described below.

**idt** — a command-line tool for doing the same thing to thousands of files without
supervision, or wiring IDT into a script.

---

## Getting started

### The desktop app

1. Install and launch **ImageDescriber**.
2. **File → Load Directory** (Ctrl+L) and choose a folder of images.
3. Pick a provider and a description style.
4. **Process → Process Undescribed Images (Entire Workspace)**. To do one folder
   at a time instead, use **Process → Process Undescribed in Selected Folder**.

That's the whole loop. If you have no AI provider set up yet, see below — start with
Ollama.

### The chat client

Launch **IDT Chat**, type a message, and press `Enter`. The first message asks which
provider and model you want. With Ollama running it needs no key and no setup.

### The command line

```
idt guideme
```

An interactive wizard that asks what you want, shows you the exact command it would
run, and offers to run it. Made to be read aloud — numbered choices, no spinners, no
ANSI escapes.

Once you know what you want:

```
idt describe ~/Pictures/Vacation/
```

---

## You need an AI provider

IDT does not include an AI model. Choose one:

| Provider | Cost | Runs where | Notes |
|---|---|---|---|
| **[Ollama](https://ollama.com)** | Free | Your machine | **Recommended to start.** Nothing leaves your computer. The Windows installer can set it up for you. |
| **Claude** (Anthropic) | Paid API | Cloud | Highest quality. Needs `ANTHROPIC_API_KEY`. |
| **OpenAI GPT** | Paid API | Cloud | Needs `OPENAI_API_KEY`. |
| **MLX** | Free | Your Mac | Apple Silicon only, and **ImageDescriber only** — see below. |

**Why MLX is in ImageDescriber but not IDT Chat.** MLX needs Apple's `mlx` and
`mlx-vlm` libraries, which are large: bundling them into IDT Chat would take it
from about 40 MB to around 350 MB. That is worth paying in ImageDescriber,
where describing a folder of photos locally is the whole point. It is worth
much less in a chat client, because Ollama now runs several models through MLX
on Apple Silicon itself — chatting with Ollama on a Mac already gets you the
Metal acceleration, without a second copy of the libraries. If you specifically
want to chat with an MLX model, ImageDescriber's own chat window offers it. IDT
Chat hides the option rather than listing one that would fail the moment you
picked it.

With Ollama you also need a vision model — `ollama pull minicpm-v4.6` gets you one.
8 GB of RAM is a realistic minimum for local models; cloud providers have no such
requirement.

---

## What it does

**Describes images in bulk.** JPEG, PNG, WebP, TIFF, HEIC/HEIF (iPhone photos), and
more. Point it at a folder and walk away.

**Describes video.** Extracts frames — at a fixed interval, or only where the scene
changes — and describes those.

**Description styles.** Several built in, from one-line alt text to detailed prose,
and you can write your own. The style is the prompt sent to the AI, and editing it is
a first-class feature rather than something buried in a config file.

**Tells the AI where and when the photo was taken.** If an image carries GPS
coordinates and a date, IDT can include them in the prompt, which measurably improves
descriptions. Optionally it will look up the city and state. Off by default; nothing
is sent anywhere unless you turn geocoding on.

**Writes descriptions into the image files.** `idt embed` copies your images and
writes the description into EXIF and XMP metadata, so it travels with the file and
shows up in Windows Explorer, Lightroom, Bridge, and Apple Photos. Your originals are
never modified.

**Downloads images from a web page** and describes them in one pass — useful for
generating alt text for a site.

**Exports** to HTML, CSV, or plain text.

**Chat about an image.** Ask follow-up questions about a specific picture in the
desktop app.

**Watches a folder** and describes new images as they land in it.

---

## Where your work is kept

Everything for a job lives in one folder you name, ending in `.idtw` — for example
`MyTrip.idtw`. It holds copies of your images, their descriptions, any chat sessions,
and anything generated along the way. Move it, back it up, or send it to someone else
and it all comes with you. Both applications read and write the same bundle.

**Your original photos are never moved or modified.**

---

## Also new in 4.5: screen reader and keyboard fixes

Three classes of bug that a sighted spot-check would never surface.

**VoiceOver now reads the name of every field on macOS.** Tabbing to a text box, list
or picker announced its contents but never its label. The labels were there — VoiceOver
could find them by exploring — but nothing connected them to the control. The cause was
that wx has no working way to name a control for VoiceOver: `SetAccessible()` raises
`NotImplementedError` there, and `SetName()` reaches no NSAccessibility attribute. Names
are now set on the native view directly.

Worse, ImageDescriber's own `set_accessible_name()` helper called a wxPython method that
**does not exist**, behind a `hasattr` guard that was therefore always false. All 31 of
its call sites did nothing, on Windows as much as on macOS. The dialogs looked carefully
labelled and were not.

**Keyboard shortcuts no longer take over platform standards.** wx maps every `Ctrl`
accelerator to `Cmd` on macOS, so one shortcut has to clear two sets of conventions.
`Ctrl+M` for Change Model shadowed Minimise; `Ctrl+P` for Edit Prompts sat on Print;
`Ctrl+C` meant "copy the selected message" application-wide, which made `Cmd+C` useless
in every text box. IDT Chat also had no Edit menu at all — and on macOS that menu is
what makes `Cmd+A`, `Cmd+V` and `Cmd+Z` work in *any* text field, so pasting an API key
was impossible.

**A control could outrank the menu bar, on both platforms.** On macOS an `&` in a button
label becomes a Command key equivalent on the native button, and AppKit offers those
before the menu bar: `&Attach Files...` owned `Cmd+A` and opened a file picker instead of
selecting text. On Windows the same ampersands are the `Alt` keys, and a control answers
before the menu — so the attachments list had taken `Alt+C` away from the Chat menu, and
nine letters in ImageDescriber's menus were claimed twice and did nothing on the first
press.

Every accelerator and every `Alt` key in both applications is now written down, per
platform, and checked against the source by the test suite.

---

## Built to be usable without sight

The desktop app is built for screen reader users, not merely checked afterwards.
Controls are labelled, the window title reports progress (`72%, 36 of 50 images
described`) so you can check status without hunting, lists are single tab stops that
read as one coherent line instead of scattered columns, and the CLI wizard is written
to be listened to.

This is the point of the tool, not a feature of it.

The model pickers follow the same rule. When a refreshed list arrives while you are
choosing, IDT does not rebuild the control underneath you — it says so on the status
line and leaves your selection alone.

---

## It tells you when there's an update

IDT notices when a newer version is out.

**ImageDescriber** checks quietly at most once a day and says nothing unless there is
something to report. **Help → Check for Updates...** asks on demand, and **Help →
Automatically Check for Updates** turns the automatic check off. From a terminal,
`idt update` reports the same thing.

When an update exists you get **Download**, **Skip This Version**, or **Later**. On
Windows, Download closes the app and runs the installer, having first verified the
download against the release's published SHA-256. On macOS the disk image is saved to
your Downloads folder and shown in Finder; a disk image can't replace a running app,
so the final drag is yours.

`idt update` reports only — installing is the installer's job, and one installer
updates both applications. The check reads GitHub's public releases list and nothing
else — no account, no telemetry, nothing sent.

---

## Command reference

```
idt guideme     Interactive wizard — start here
idt describe    Describe a folder, a bundle, or paths piped from stdin
idt download    Fetch images from a web page (--describe to describe them)
idt video       Extract video frames and optionally describe them
idt embed       Write descriptions into image metadata (EXIF + XMP)
idt export      HTML, CSV, or text output
idt show        Print descriptions (--json to pipe elsewhere)
idt status      How far along a job is
idt stats       Token usage and cost estimates
idt combine     Merge descriptions across several jobs
idt watch       Monitor a folder and describe new arrivals
idt chat        Chat with a model from the terminal
idt models      What models are available (--refresh, --all)
idt prompts     What description styles exist
idt config      Set your defaults
idt update      Check for a newer release
idt version     Version information
```

`idt <command> --help` for options.

---

## Known limitations

- **macOS builds are Apple Silicon only.** No Intel Mac build is published. Intel
  users can run from source.
- **Work done before v4.5 isn't converted automatically.** Older `wf_…` output
  folders still open in the desktop app: **File → Open Workflow Result (Viewer
  Mode)…** to read one as it is, or **File → Import Workflow (to Workspace)…** to
  bring its descriptions into a `.idtw` bundle.
- **`idt guideme` needs a terminal it can read from.** Run from a script or a pipe,
  it exits immediately with `Error: EOF when reading a line`. Use `idt describe` in
  scripts.
- **A brand-new model's cost and context window are unknown to IDT** until a later
  release records them. It is still usable; `idt stats` may show no cost estimate for
  it, and long conversations are trimmed conservatively.
- Local models are slower than cloud ones, sometimes much slower, depending on your
  hardware.

---

## Help

- **[User Guide](https://kellylford.github.io/Image-Description-Toolkit/user-guide.html)** — the full manual
- **[Report an issue](https://github.com/kellylford/Image-Description-Toolkit/issues)**
- In the desktop app: **Help → User Guide**

---

## Providers as of this release

Run `idt models` to see exactly what your own API keys give you. As of this release the
models each provider recommends for describing images:

| Provider | Recommended models |
|---|---|
| Claude | `claude-opus-5`, `claude-sonnet-5`, `claude-opus-4-8`, `claude-haiku-4-5-20251001` |
| OpenAI | `gpt-5.2`, `gpt-5.1`, `gpt-5-mini`, `gpt-5-nano`, `o4-mini`, `o3` |
| Ollama | whatever you've pulled — `idt models --provider ollama` |
