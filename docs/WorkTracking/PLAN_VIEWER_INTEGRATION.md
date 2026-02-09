# Plan: Viewer Integration into ImageDescriber

**Date**: 2026-02-09
**Status**: Proposed

## 1. Objective
Consolidate the standalone `Viewer` application functionality into the `ImageDescriber` application. This creates a unified GUI tool that handles both the creation (Editor) and consumption (Viewer) of image descriptions.

## 2. Architecture Overview

### Current State
- **ImageDescriber**: Workspace-centric. Users load a list of images (Project/Workspace). Primary view is a list of images. Logic focuses on generating descriptions.
- **Viewer**: Workflow-centric. Users load a directory containing `image_descriptions.txt`. Primary view is a list of descriptions. Logic focuses on parsing text files and live monitoring.

### Future State (Integrated)
`ImageDescriber` becomes the single entry point with two distinct modes:

1.  **Editor Mode** (Existing functionality):
    -   **Data Source**: Image Workspace (`.json` or list of files).
    -   **Navigation**: Image List (Left) -> Description Editor (Right).
    -   **Focus**: Processing, Editing, Generating.

2.  **Viewer Mode** (New functionality):
    -   **Data Source**: Workflow Directory (folder with `image_descriptions.txt`).
    -   **Navigation**: Description List (Left) -> Image Preview & Details (Right).
    -   **Focus**: Reviewing, Monitoring, Exporting.
    -   **Behavior**: Supports "Live Monitoring" of active CLI workflows.

**Comment:**Viewer also needs to support workspaces. For example, I may load a workspace and as images are described, I need to be able to switch between desciber/editor (current) and viewer (new) modes.


## 3. Implementation Plan

### Phase 1: Core Logic Extraction
Extract the business logic from `viewer/viewer_wx.py` into reusable classes within `imagedescriber`.
-   **`WorkflowMonitor`**: Class to handle parsing `image_descriptions.txt` and watching for file changes (Live Mode).
-   **`WorkflowNavHelper`**: Logic for flattening description entries for the list view (handling multiple descriptions per image if necessary, though Viewer currently treats entries linearly).

### Phase 2: Viewer UI Component
Create `imagedescriber/workflow_viewer.py` containing:
-   **`ViewerPanel`**: A `wx.Panel` subclass that replicates the Viewer's UI layout.
    -   Left: `DescriptionListBox` (shared component).
    -   Right: Image Preview, Metadata, Full Text Display.
    -   Top/Bottom: Controls for "Live Mode", Refresh, Redescribe actions. 
-   This panel will be self-contained and can be swapped into the main frame.

### Phase 3: Main Window Integration
Modify `imagedescriber/imagedescriber_wx.py`:
1.  **Mode Management**: Add state to track current mode (Editor vs Viewer).
2.  **UI Switching**:
    -   Replace the static layout in `ImageDescriber` frame with a container that can show either `EditorPanel` (existing UI wrapped in a panel) or `ViewerPanel`.
    -   Alternatively, use a `wx.Notebook` allowing multiple open Workspaces/Workflows, but separate "Modes" might be cleaner for the menu bar.
3.  **Menu Bar Adaptation**:
    -   Update Menu Bar to show relevant actions based on active mode (e.g., "Live Mode" toggle only in Viewer Mode).
    -   Add `File -> Open Workflow Result...` to switch to Viewer Mode and load a directory.

### Phase 4: CLI & Entry Point Updates
1.  **Argument Parsing**: Update `imagedescriber_wx.py` to accept a directory argument.
    -   If argument is a directory with descriptions: Launch in **Viewer Mode**.
    -   If argument is a workspace file (`.json`): Launch in **Editor Mode**.
2.  **IDT CLI**:
    -   Update `idt viewer` command to launch `imagedescriber` with the appropriate arguments, effectively deprecating the separate `viewer` executable.

## 4. Navigation & User Experience

-   **Viewer Mode Navigation**:
    -   Retain the "Description-first" navigation.
    -   Arrow keys move through the description list.
    -   "Redescribe" actions in Viewer Mode will conceptually link to Editor functions (e.g., "Redescribe this image" could open it in Editor Mode? Or just trigger the existing backend process like Viewer does now). *Decision: Keep it simple first, use Viewer's existing lightweight redescribe dialogs.*

-   **Editor Mode Navigation**:
    -   Retain "Image-first" navigation.

## 5. Migration Steps

1.  **Create Components**: implement `imagedescriber/workflow_viewer.py` reusing logic from `viewer/viewer_wx.py`.
2.  **Refactor Main Frame**: Modify `ImageDescriber` to use a central content panel and support mode switching.
3.  **Wire Up**: Connect menus and file loading logic.
4.  **CLI Update**: Modify `idt_cli.py` to route `viewer` command to the new code.
5.  **Deprecation**: Remove `viewer/` directory once integration is verified.

## 6. Verification
-   Load `idt.exe viewer <directory>` -> verifies Viewer Mode.
-   Load `idt.exe imagedescriber` -> verifies Editor Mode.
-   Test Live Monitoring in Viewer Mode.
-   Test "Redescribe" actions in Viewer Mode.
