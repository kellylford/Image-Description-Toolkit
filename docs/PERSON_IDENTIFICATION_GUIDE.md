# Person Identification — User Guide

**Status: Draft — Feature in active development**

---

## Table of Contents

1. [Overview](#1-overview)
2. [The People-Focused Prompt](#2-the-people-focused-prompt)
3. [The Known Persons Database](#3-the-known-persons-database)
4. [Method 1: Manual Tagging](#4-method-1-manual-tagging)
5. [Method 2: Face Recognition](#5-method-2-face-recognition)
6. [Reviewing Groups and Linking to Known Persons](#6-reviewing-groups-and-linking-to-known-persons)
7. [Exporting and Importing Person Data](#7-exporting-and-importing-person-data)
8. [Person Tags in HTML Reports](#8-person-tags-in-html-reports)
9. [CLI Quick Reference](#9-cli-quick-reference)
10. [Privacy and Data Storage](#10-privacy-and-data-storage)

---

## 1. Overview

Person identification in IDT lets you associate names with images in your workspace. Once tagged, a person's name travels with the workflow output and appears in HTML reports — making it possible to search, sort, and review photos not just by AI description but by who is in them.

There are two complementary approaches:

| Approach | Best for | Requires |
|---|---|---|
| **Manual tagging** | Small collections, known individuals, quick annotations | Nothing extra |
| **Face recognition** | Large collections, unknown faces, automated grouping | Optional engine install |

Both approaches use the same underlying Known Persons Database, so tags created by either method are interchangeable.

---

## 2. The People-Focused Prompt

Before tagging, you need good descriptions to work from. IDT includes a built-in prompt style called **people_focused** designed to direct the AI to describe individuals in detail: age range, gender expression, hair color, clothing, position in the frame, and other distinguishing characteristics.

### Using the prompt in ImageDescriber

1. Open a workspace in ImageDescriber.
2. In the provider/prompt controls, open the prompt style list.
3. Select **People Focused**.
4. Run the description as normal.

### Using the prompt from the CLI

```
idt workflow --images ./photos --prompt people_focused
```

The resulting descriptions will contain enough physical detail for both text-based grouping and manual identification.

---

## 3. The Known Persons Database

The Known Persons Database is stored in your `.idtworkspace` file. Each person record contains:

- **Name** — display name shown everywhere (e.g., "Alice Smith")
- **Physical traits** — free-text description used when matching AI-generated descriptions (e.g., "tall woman, auburn hair, wire-frame glasses, usually wears formal clothing")
- **Notes** — optional free-form field

Adding detailed physical traits improves matching accuracy when the AI description references someone by appearance rather than name.

### Managing persons in ImageDescriber

Go to **Tools → Manage Known Persons**. The dialog lets you:

- Add a new person (name, traits, notes)
- Edit an existing person's record
- Remove a person (also removes their tags from all images)
- See how many images each person is tagged in

### Managing persons from the CLI

```
# Add a person
idt persons add --name "Alice Smith" --traits "tall, auburn hair, glasses"

# List all persons in the workspace
idt persons list

# List with a specific workspace file
idt persons list --workspace my_photos.idtworkspace
```

If your current directory contains exactly one `.idtworkspace` file, IDT will use it automatically. Otherwise, pass `--workspace` explicitly.

---

## 4. Method 1: Manual Tagging

Manual tagging is the simplest approach. You select an image, type or choose a name, and IDT records the association.

### Tagging in ImageDescriber

1. Select the image in the image list.
2. Open the **Descriptions** menu and choose **Tag Person in Image**.
3. In the dialog, type a name or select an existing person from your Known Persons Database.
4. Click **OK**.

The image's detail area will show a "People" label with the tagged names.

To remove a tag, open the same dialog, select the person, and click **Remove Tag**.

### Tagging from the CLI

```
# Tag an image (IDT will auto-find the workspace in the current directory)
idt persons tag --image IMG_001.jpg --person "Alice Smith"

# Tag with an explicit workspace
idt persons tag --image ./photos/IMG_001.jpg --person "Alice Smith" --workspace my_photos.idtworkspace

# Remove a tag
idt persons untag --image IMG_001.jpg --person "Alice Smith"
```

---

## 5. Method 2: Face Recognition

Face recognition is an optional capability that detects faces in images, computes embeddings, and groups similar faces together automatically. You then review the groups and assign names from your Known Persons Database.

> **Note:** Face recognition requires downloading and installing additional packages (PyTorch, facenet-pytorch, scikit-learn). This is around 1–2 GB of disk space. The data never leaves your machine.

### Step 1: Install the engine

**In ImageDescriber:** Go to **Tools → Install Face Recognition Engine**. A progress dialog shows each package being installed. This only needs to be done once.

**From the CLI:**

```
# Install
idt persons install-engine

# Check whether the engine is installed
idt persons install-engine --status

# Force a clean reinstall
idt persons install-engine --reinstall
```

### Step 2: Scan faces

Scanning reads each image, detects faces, and stores mathematical face embeddings in a local database file (`.idt_faces.db` in your workspace directory). No image data leaves your system.

**In ImageDescriber:** Go to **Process → Scan Faces in Images**. A progress dialog tracks each image.

### Step 3: Cluster faces

Clustering groups the stored face embeddings by similarity using an algorithm that automatically determines how many distinct individuals are present. Images of the same person should end up in the same cluster.

**In ImageDescriber:** Go to **Process → Cluster Faces**. After clustering completes, the **Grouping Results** dialog opens automatically.

### Step 4: Review groups and assign names

The **Grouping Results** dialog shows each cluster of similar-looking faces. For each group, you can:

- See a summary of the images involved
- Type a name to link the group to a known person (or create a new person record on the spot)
- Mark a group as "unknown" to leave it unresolved for now
- Skip groups you are not sure about

Once you assign a name to a group, all images in that group are tagged with that person.

### Finding similar faces for a single image

If you want to check what clusters a particular image's faces belong to:

1. Select the image in ImageDescriber.
2. Go to **Process → Find Similar Faces**.
3. A result dialog shows the best matching stored face for each detected face, along with the similarity score and person name if one has been assigned.

---

## 6. Reviewing Groups and Linking to Known Persons

The Grouping Results dialog (opened after **Cluster Faces** or manually from the face review workflow) works as follows:

- Each row represents a group of images the system believes shows the same individual.
- The **Description Summary** column shows any common physical descriptors pulled from AI descriptions.
- The **Method** column shows how the group was created: `cv` for face recognition, `text` for text-mining.
- Use the **Link to Person** button or dropdown to assign a name from your Known Persons Database.
- Use **New Person** to create a new record and link in one step.
- Use **Skip** to leave a group unresolved — you can come back to it later.

Changes are written to the workspace when you click **Save and Close**.

---

## 7. Exporting and Importing Person Data

Person tags are stored in your `.idtworkspace` file. When you generate an HTML report from a workflow, IDT automatically writes the relevant tags into a `persons_export.json` file inside the workflow's `descriptions/` folder. This means the tags travel alongside the descriptions when you share or archive a workflow output folder.

To manually export or import:

```
# Export person data for a specific workflow output folder
idt persons export --workflow ./wf_2026-04-04_1020_gpt4o_people_focused

# Import person data from a workflow folder back into your workspace
idt persons import --workflow ./wf_2026-04-04_1020_gpt4o_people_focused

# Generate a full person identification report
idt persons report

# Report scoped to a single workflow
idt persons report --workflow ./wf_2026-04-04_1020_gpt4o_people_focused

# Save the report to a file
idt persons report --output persons_report.txt

# Save the report as HTML
idt persons report --output persons_report.html
```

---

## 8. Person Tags in HTML Reports

When IDT generates an HTML report for a workflow (via the `idt workflow` command or ImageDescriber's report export), any images with person tags display a "People identified" section in their card. The section lists the names of all tagged persons for that image.

The tags are sourced from the `persons_export.json` file in the descriptions folder. If you add new tags after a report has been generated, regenerate the report or re-export.

---

## 9. CLI Quick Reference

All person commands are accessed through the `idt persons` command group.

| Command | What it does |
|---|---|
| `idt persons add --name "Name" --traits "description"` | Add a person to the Known Persons Database |
| `idt persons list` | List all known persons and tag counts |
| `idt persons tag --image FILE --person "Name"` | Tag an image with a person |
| `idt persons untag --image FILE --person "Name"` | Remove a tag |
| `idt persons report` | Print a full person identification report |
| `idt persons report --workflow DIR` | Report scoped to one workflow folder |
| `idt persons report --output FILE.html` | Save report as HTML |
| `idt persons export --workflow DIR` | Export person data to a workflow folder |
| `idt persons import --workflow DIR` | Import person data from a workflow folder |
| `idt persons install-engine` | Install the face recognition engine |
| `idt persons install-engine --status` | Check whether the engine is installed |
| `idt persons install-engine --reinstall` | Force reinstall the engine |

All commands accept `--workspace FILE` to specify a `.idtworkspace` file explicitly. If omitted, IDT auto-detects the workspace in the current directory.

---

## 10. Privacy and Data Storage

All person identification data is stored locally on your machine:

- **Known Persons Database** — stored in your `.idtworkspace` file alongside your project.
- **Face embeddings** — stored in `.idt_faces.db` in your workspace directory. This is a SQLite database containing mathematical vectors derived from faces. It does not contain image data. It is created only when you run Scan Faces.
- **Workflow export** — `persons_export.json` is written inside each workflow's `descriptions/` folder when you export or generate a report.

None of this data is transmitted to any external service. When you describe images using a cloud AI provider (OpenAI, Claude, Ollama cloud), the *image content* is sent to that provider according to their terms of service — but person names, trait descriptions, and face embeddings are never sent anywhere.

To remove all person data from a workspace, delete the `.idtworkspace` file or use `Tools → Manage Known Persons` to remove records individually.
