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
| **`ImageDescriptionToolkitSetup-4.5.0-windows.exe`** | Windows 10/11, 64-bit | **Start here.** Installs both apps. |
| **`IDT-4.5.0-macos-arm64.dmg`** | macOS 12+, Apple Silicon | **Start here.** Contains both apps. |
| `idt-4.5.0-windows-x64.exe` | Windows | Just the command-line tool, no installer |
| `ImageDescriber-4.5.0-windows-x64.exe` | Windows | Just the GUI, no installer |
| `idt-4.5.0-macos-arm64.tar.gz` | macOS | Just the command-line tool |
| `SHA256SUMS.txt` | — | Checksums, if you want to verify your download |

No Python, no dependencies. The Windows installer is signed; the macOS build is signed
and notarized by Apple.

The standalone `.exe` files are for people who want one tool and no installer. Most
people want the installer.

---

## The two applications

IDT is two programs that share everything — the same AI providers, the same settings,
the same files on disk. Use whichever suits the moment; you can start work in one and
finish in the other.

**ImageDescriber** — a desktop app. Load a folder, pick a model and a description
style, and watch descriptions appear. Review and edit them, browse your images, ask
follow-up questions about a picture in a chat window, and export when you're done.

**idt** — a command-line tool for doing the same thing to thousands of files without
supervision, or wiring IDT into a script.

---

## Getting started

### The desktop app

1. Install and launch **ImageDescriber**.
2. **File → Load Directory** and choose a folder of images.
3. Pick a provider and a description style.
4. **Processing → Process All Undescribed**.

That's the whole loop. If you have no AI provider set up yet, see below — start with
Ollama.

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
| **MLX** | Free | Your Mac | Apple Silicon only, desktop app only. |

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

## Built to be usable without sight

The desktop app is built for screen reader users, not merely checked afterwards.
Controls are labelled, the window title reports progress (`72%, 36 of 50 images
described`) so you can check status without hunting, lists are single tab stops that
read as one coherent line instead of scattered columns, and the CLI wizard is written
to be listened to.

This is the point of the tool, not a feature of it.

---

## It tells you when there's an update

New in this release: IDT notices when a newer version is out.

**ImageDescriber** checks quietly at most once a day and says nothing unless there is
something to report. **Help → Check for Updates...** asks on demand, and **Help →
Automatically Check for Updates** turns the automatic check off. From a terminal,
`idt update` reports the same thing.

When an update exists you get **Download**, **Skip This Version**, or **Later**. On
Windows, Download closes the app and runs the installer, having first verified the
download against the release's published SHA-256. On macOS the disk image is saved to
your Downloads folder and shown in Finder; a disk image can't replace a running app,
so the final drag is yours.

One update covers both applications. The check reads GitHub's public releases list and
nothing else — no account, no telemetry, nothing sent.

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
idt models      What models are available
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
- **`watch` and `video` still use older per-folder storage**, not the `.idtw` bundle.
- **Descriptions from before v4.5 aren't picked up automatically.** Old `wf_…` output
  folders are still readable in the desktop app's viewer.
- **`idt guideme` needs a real terminal.** In a non-interactive environment it will
  hang; use `idt describe` directly.
- **`idt update` only reports.** It doesn't download or install — run the installer,
  or use the desktop app's update prompt.
- **HEIC support may need extra pieces** on Windows: the free
  [HEIF Image Extensions](https://www.microsoft.com/store/productId/9PMMSR1CGPWG)
  from the Microsoft Store.
- Local models are slower than cloud ones, sometimes much slower, depending on your
  hardware.

---

## Help

- **[User Guide](https://kellylford.github.io/Image-Description-Toolkit/user-guide.html)** — the full manual
- **[Report an issue](https://github.com/kellylford/Image-Description-Toolkit/issues)**
- In the desktop app: **Help → User Guide**

---

## Providers as of this release

| Provider | Models |
|---|---|
| Claude | claude-opus-5, claude-sonnet-5, claude-opus-4-8, claude-haiku-4-5 |
| OpenAI | gpt-5.2, gpt-5.1, gpt-5-mini, gpt-5-nano, o4-mini, o3 |
| Ollama | whatever you've pulled — `idt models --provider ollama` |
