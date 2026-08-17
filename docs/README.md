# Image Description Toolkit — Documentation

Welcome to the IDT documentation. The published accessible version is available at the
project GitHub Pages site.

## Start here

- **[USER_GUIDE.md](USER_GUIDE.md)** — the complete guide to all three apps: the `idt`
  command line tool, the ImageDescriber GUI, and IDT Chat. Part 2 is the full command
  reference, with every option and worked examples.
- **[Release notes — v4.5.1](release-notes-v4.5.1.md)** — what IDT is, how to install it,
  and what changed most recently.

## By topic

| Document | What it covers |
|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | Installation, first workflow, every CLI command, both GUIs, accessibility, troubleshooting |
| [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) | Config files, API keys, customization |
| [WEB_DOWNLOAD_GUIDE.md](WEB_DOWNLOAD_GUIDE.md) | Downloading and describing images from websites |
| [IMAGE_FORMAT_SUPPORT.md](IMAGE_FORMAT_SUPPORT.md) | Which image and video formats are supported, and how HEIC is handled |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Architecture, `idt_core` inventory, build system, testing, conventions |
| [CI_WORKFLOWS.md](CI_WORKFLOWS.md) | GitHub Actions: what each workflow does, signing, and how a release is cut |
| [CLI_INVENTORY.md](CLI_INVENTORY.md) | A point-in-time audit of the v4.5 CLI against the previous one. Historical — see the user guide for current behaviour |
| [IDT Style Guide.md](IDT%20Style%20Guide.md) | Writing style for documentation and UI text |

## Component documentation

- **[imagedescriber/README.md](../imagedescriber/README.md)** — the batch processing GUI
- **[tools/README.md](../tools/README.md)** — additional utilities

## Where to look for...

**Getting started** → [USER_GUIDE.md](USER_GUIDE.md), Part 1

**A specific command** → [USER_GUIDE.md](USER_GUIDE.md), Part 2. There is no separate
CLI reference file; the command documentation lives in the user guide so there is one
place to keep current.

**Which AI provider to use** → [USER_GUIDE.md](USER_GUIDE.md), Part 4. Run
`idt models` to see what your own API keys give you access to.

**Writing prompts** → [USER_GUIDE.md](USER_GUIDE.md), Part 5

**Screen reader and keyboard use** → [USER_GUIDE.md](USER_GUIDE.md), Part 8. Accessibility
is the point of this toolkit rather than a feature of it, so it is covered throughout
rather than only there.

**Development history** → [WorkTracking/](WorkTracking/) — session summaries and planning
documents.

## Documentation standards

- **Accessibility-first** — screen reader friendly formatting throughout
- **Example-driven** — concepts come with working examples
- **Current** — updated with each release, and links are checked against files that exist

---

*Last updated: 2026-08-16 — v4.5.1*
