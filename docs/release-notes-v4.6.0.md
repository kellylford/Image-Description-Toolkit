# Image Description Toolkit v4.6.0

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
| **`ImageDescriptionToolkitSetup-4.6.0-windows.exe`** | Windows 10/11, 64-bit | **Start here.** Installs all three applications. |
| **`IDT-4.6.0-macos-arm64.dmg`** | macOS, Apple Silicon | **Start here.** Contains all three. |
| `idt-4.6.0-windows-x64.exe` | Windows | Just the command-line tool, no installer |
| `ImageDescriber-4.6.0-windows-x64.exe` | Windows | Just the image GUI, no installer |
| `IDTChat-4.6.0-windows-x64.exe` | Windows | Just the chat client, no installer |
| `idt-4.6.0-macos-arm64.tar.gz` | macOS | Just the command-line tool |
| `SHA256SUMS.txt` | — | Checksums, if you want to verify your download |

No Python, no dependencies. The Windows installer is signed; the macOS build is signed
and notarized by Apple.

The standalone `.exe` files are for people who want one tool and no installer. Most
people want the installer, which puts all three on the Start menu.

---

## New in 4.6: descriptions that never leave your Mac

macOS 27 includes an AI model that runs on the machine itself, and IDT can now use
it. Pick **Apple Intelligence** as your provider and your photos are described on
your own Mac: no API key, no account, no internet connection, and no cost however
many images you run through it.

It is about four to six seconds an image once it warms up, and what comes back is
real alt text — objects, colours, what is in front of what, laid out left to right —
not a one-line caption.

**What you need**

- A Mac with Apple Silicon running macOS 27 or later.
- Apple Intelligence switched on in **System Settings → Apple Intelligence & Siri**,
  with its model downloaded.
- One command, once per machine, typed by an administrator:

```
sudo fm license
```

That last step is Apple's licence agreement for the on-device model. It applies to
everyone who uses the Mac, so it needs an administrator and IDT cannot do it for you.
Run `idt models --provider apple` afterwards and IDT will tell you whether this Mac is
ready — and if not, which of the three things above is missing. On a Mac that cannot
run it at all, the option is hidden rather than offered and then failing.

**What to expect from it.** It is a small model compared with Claude or GPT. Expect
shorter, plainer descriptions, less interpretation, and less certainty about small
text inside a picture. If you want the most detailed result, use a cloud provider.
If you want something free, fast and completely private, this is the one to reach
for. Every prompt style works with it — `detailed`, `accessibility`, `artistic` and
the rest each change the output the way they do everywhere else.

**It refuses some pictures.** The on-device model declines certain images outright —
IDT says so plainly, and the run carries on to the next one. Retrying the same request
will not help, but a different prompt style often will, and which one is not
predictable: on one photo of a museum taxidermy display, `narrative` and `detailed`
worked on one machine while `accessibility` and `artistic` worked on another. The
shorter styles are refused most often, `aialttext` and `simple` among them, which is
worth knowing if you are generating alt text. `docs/apple-intelligence-safety-refusals.md`
records everything that was measured, and ships a script that reproduces it.

One limit worth knowing: the on-device model holds about 4,096 tokens in total, an
order of magnitude less than the cloud models. That is ample for describing images,
but **chats** reach the limit quickly. When one does, IDT says so and asks you to
start a new conversation rather than silently retrying something that cannot work.

---

## New in 4.6: Claude on the subscription you already pay for

If you have Claude Pro or Max, IDT can now use that subscription instead of an API
key. Choose **Claude Code** as your provider, sign in once, and requests count
against your plan rather than charging an API account.

```
claude auth login
```

Pick `haiku`, `sonnet` or `opus`. Each is an alias the Claude Code app resolves to
the current model of that tier, so the list cannot go stale the way a hardcoded one
does.

**What it costs you.** Not money, but some of your plan's allowance. A measured run
of 103 images used at most about 4% of a five-hour window on a Pro plan. Each image
goes on its own with a short instruction and none of Claude Code's usual extras, so
it costs roughly what the same request would through the API. Describing images
draws on the same allowance as your ordinary Claude conversations, so a long coding
session can use more of it than a folder of photos will.

IDT refuses to use Claude Code if it is signed in any other way — with an API key,
say — because that would bill an API account, which is the opposite of the point.
The provider only appears once Claude Code is installed.

---

## The three applications

IDT is three programs that share everything — the same AI providers, the same
settings, the same files on disk. Use whichever suits the moment; you can start work
in one and finish in another.

**ImageDescriber** — a desktop app. Load a folder, pick a model and a description
style, and watch descriptions appear. Review and edit them, browse your images, ask
follow-up questions about a picture in a chat window, and export when you're done.

**IDT Chat** — a standalone chat client for Ollama, Claude, OpenAI, Claude Code and
Apple Intelligence, built for keyboard and screen reader use. Introduced in 4.5; the
two new providers reach it in this release.

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
| **Apple Intelligence** | Free | Your Mac | **New in 4.6.** macOS 27 on Apple Silicon. Nothing leaves the machine. |
| **Claude Code** | Your Claude plan | Cloud | **New in 4.6.** Uses a Pro/Max subscription instead of an API key. |
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

## From 4.5: screen reader and keyboard fixes

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

## From 4.5: embedded descriptions you can actually find, and a TIFF fix

Descriptions can be written into the image files themselves, so they travel with the
photo. The guide explained how to put them in and never said how to get them back out,
which made the whole feature hard to trust: you get a folder of copies and no way to
confirm anything happened.

**The user guide now says where to look**, on both platforms. On Windows: switch File
Explorer to Details view, tab to the column headers, press `Shift+F10`, and turn on
**Comments** or **Title** — then arrowing down the list reads each description along with
its file name. Which column works depends on the format, so the guide spells that out;
PNG has no EXIF at all and only appears under Title. On macOS: `Cmd+I` for Get Info,
Preview's Inspector, Spotlight, `mdls`, or Photos captions. It also warns that Finder's
**Comments** column is a note Finder keeps on the side and *not* the embedded
description — switching it on shows nothing, which looks exactly like a failed embed.

**Embedding into a TIFF used to destroy the file.** `.tif` and `.tiff` were handed to the
JPEG writer, which injected a JPEG segment over the TIFF byte-order magic. The result was
not a TIFF missing its description; it was a file Pillow, Explorer and Preview all refused
to open. Nothing raised an error — the embed reported success and handed back dead files.
TIFF now has its own writer, and multi-page TIFFs keep every page.

Every claim in the new instructions is checked by the test suite against the real thing:
the actual Explorer column values on Windows, and on macOS the ImageIO framework that Get
Info and Preview read through.

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
- **Apple Intelligence declines some images.** Not a fault and not worth retrying;
  try a different prompt style. See the note above.
- **Apple Intelligence holds about 4,096 tokens.** Fine for describing images; short
  for chat. IDT tells you when a conversation has outgrown it.
- **Apple Intelligence needs a one-time `sudo fm license`** run by an administrator.
  It applies to everyone who uses that Mac, and no application can do it for you.
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
| Claude Code | `haiku`, `sonnet`, `opus` — aliases that always point at the current model of each tier |
| Apple Intelligence | `system` — the one on-device model; run `idt models --provider apple` to check this Mac is ready |
