# IDT Style Guide — Markdown Formatting

Quick reference for editing `USER_GUIDE_COMPLETE.md` and other IDT docs. These conventions are already used throughout the user guide; follow them to keep everything consistent.

---

## Document Structure

### Title and Version
```markdown
# Image Description Toolkit — User Guide

**Version 4.0.0Beta2**
```
- One `#` title at the top
- Version in bold (`**...**`) immediately below, no heading

### Section Headings

| Level | Syntax | Use for |
|---|---|---|
| `##` | `## 1. Section Name` | Top-level numbered sections |
| `###` | `### Subsection Name` | Subsections within a section (no number) |

Sections are numbered (`## 1.`, `## 2.`, etc.). Subsections are not.

### Horizontal Rules
Use `---` to separate major sections. Place one blank line before and after.

---

## Table of Contents

Links use lowercase, hyphens for spaces, special characters removed:

```markdown
1. [Section Name](#1-section-name)
4. [The `guideme` Wizard](#4-your-first-descriptions--the-guideme-wizard)
```

- Em dashes (`—`) in headings become `--` in anchors
- Backtick content (`` `guideme` ``) is stripped in anchors
- Parentheses and other punctuation are removed

---

## Inline Text Formatting

| Pattern | Syntax | When to use |
|---|---|---|
| **Bold** | `**text**` | Key terms, important notes, UI labels, first mention of a concept |
| `Code` | `` `text` `` | Commands, filenames, config keys, model names, env vars, keyboard keys |
| *Italic* | `*text*` | Rarely used; avoid unless necessary |

**Examples from the guide:**
- UI labels: `**IDT**`, `**ImageDescriber**`, `**File → Open Folder**`
- Commands: `` `idt workflow` ``, `` `idt guideme` ``
- Keys: `` `Ctrl+L` ``, `` `P` ``, `` `B` ``
- Config keys: `` `default_model` ``, `` `batch_delay` ``
- File names: `` `image_descriptions.txt` ``, `` `workflow_config.json` ``
- Paths: `` `C:\IDT\` ``, `` `~/openai.txt` `` 
- Model names: `` `moondream:latest` ``, `` `llava:7b` ``

---

## Code Blocks

Fenced with triple backticks. Always specify the language when it applies.

**Shell commands (no language tag):**
````markdown
```
idt version
idt workflow ~/Photos
```
````

**Bash (when showing multiple commands with comments):**
````markdown
```bash
# Extract frames from a video
idt extract-frames myvideo.mp4

# Convert HEIC images
idt convert-images ~/Photos
```
````

**File content or prompt text (no language tag):**
````markdown
```
Provide a narrative description including objects, colors and detail.
Avoid interpretation, just describe.
```
````

Use `bash` when the block includes `#` comments. Use no language tag for single commands, file paths in output, or literal prompt text.

---

## Lists

### Unordered Lists
```markdown
- First item
- Second item
- Third item
```

Use `-` (not `*` or `+`). One blank line before the list, no blank line between items unless items are long.

### Ordered Lists
```markdown
1. First step
2. Second step
3. Third step
```

Use sequential numbers (not all `1.`).

### Nested Lists (indented sub-items)
```markdown
- Parent item
  - Sub-item (2 spaces indent)
  - Another sub-item
```

---

## Tables

```markdown
| Column A | Column B | Column C |
|---|---|---|
| Row 1A | Row 1B | Row 1C |
| Row 2A | Row 2B | Row 2C |
```

- Header row, separator row (`|---|`), then data rows
- No padding inside `|---|` separators (the guide does not use `:---:` alignment)
- Bold the first column only when it is a label/term column (see the API key table)

---

## Notes and Callouts

The guide uses a blockquote for tips, warnings, and platform-specific notes:

```markdown
> **Windows SmartScreen:** The application is not code-signed for Windows at this time. If SmartScreen warns you, click "More info" then "Run anyway."

> **Apple Silicon (M1/M2/M3/M4 Mac):** IDT also supports the MLX provider...
```

- Start with `> **Label:**` in bold
- Use for platform-specific caveats, warnings, and tips
- No emoji, no `NOTE:` / `WARNING:` / `TIP:` prefixes — use a descriptive label instead

---

## Menu Paths and UI References

Use backticks for menu paths and keyboard shortcuts:

```markdown
`File → Open Folder`
`Tools → Edit Prompts`
`Processing → Process Batch`
`Ctrl+L`
`Ctrl+S`
`P`
`B`
```

Use `→` (not `>` or `->`) as the menu separator.

---

## File Paths

| Platform | Style |
|---|---|
| macOS/Linux | `` `~/Photos/Vacation2025` ``, `` `/usr/local/bin/idt` `` |
| Windows | `` `C:\IDT\` ``, `` `C:\Photos\Vacation2025` `` |

When showing both platforms, present macOS first, then Windows.

---

## Section Cross-References

Link to other sections by number and anchor:

```markdown
See [Section 16](#16-analysis-and-export-commands) for full details.
See [Section 26](#26-monitoring-costs-for-cloud-models).
```

Format: `[Section N](#N-slug-of-heading)`

---

## Platform Split Formatting

When instructions differ by platform, use bold platform labels as sub-headings within a section:

```markdown
**macOS:** Double-click ImageDescriber in your Applications folder, or run `idt imagedescriber` in Terminal.
**Windows:** Start Menu → IDT → ImageDescriber, or run `idt imagedescriber` in a Command Prompt.
```

For longer platform-specific blocks, use `###` sub-headings:

```markdown
### macOS
...

### Windows
...
```

---

## Spacing Rules

- One blank line between paragraphs
- One blank line before and after code blocks
- One blank line before and after lists
- One blank line before and after tables
- One blank line before and after `---` rules
- No trailing spaces
