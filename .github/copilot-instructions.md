# GitHub Copilot Instructions for Image-Description-Toolkit

Follow these guidelines for all coding work on this project.

## Code Quality Standards

1. **Professional Quality:** Code should be professional quality and tested before calling something complete and ready for submission.

2. **Planning and Tracking:** Planning and tracking documents should go in the `docs/worktracking/` directory and kept current as work is completed.

3. **Accessibility:** All coding should be WCAG 2.2 AA conformant. This should be a given for this project, so being accessible doesn't need to be highlighted in documentation unless it is something especially unique.

4. **Dual Support:** Work needs to keep in mind that we want to keep support for both the script-based approach for image descriptions and the GUI ImageDescriber app.

5. **No Shortcuts:** Avoid the typical behavior of AI of taking shortcuts, not scanning files completely, and more. This has already resulted in duplicate code at times and extensive time debugging. The project has become too large for constant testing.

6. **Reposatory Hygiene:** Keep the repository clean and organized. Remove unused files, fix broken links, and ensure that documentation is up to date.

## Project-Specific Guidelines

### Testing Checklist
- Maintain `TESTING_CHECKLIST_OCT13.md` (or current date) as a living document
- Update it automatically whenever making commits, adding features, creating documentation, or fixing bugs
- Ensure the checklist always reflects the current state of the session Note: this file is in docs\archive.

### Documentation Structure
- Main documentation: `docs/`
- Work tracking: `docs/worktracking/`
- Feature-specific docs: Appropriate subdirectories

### Architecture
- **CLI Tool:** `idt.exe` - Main command-line interface
- **GUI Tools:** ImageDescriber, Viewer, Prompt Editor
- **Scripts:** Python scripts for workflow automation
- **Shared Config:** `scripts/` directory contains shared configuration files

### Key Principles
- Support both frozen (executable) and development (Python script) modes
- Maintain backward compatibility
- Create helper files (batch files on Windows) for user convenience
- Opt-in approach for optional features (e.g., stats generation)
- Keep directories clean - avoid automatic file creation unless essential
