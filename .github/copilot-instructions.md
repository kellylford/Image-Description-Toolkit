# GitHub Copilot Instructions for Image-Description-Toolkit

Follow these guidelines for all coding work on this project.

## Code Quality Standards

1. **Professional Quality:** Code should be professional quality and tested before calling something complete and ready for submission.

2. **Planning and Tracking:** Planning and tracking documents should go in the `docs/worktracking/` directory and kept current as work is completed.

3. **Session Summaries:** Create and maintain a session summary document in `docs/worktracking/` with format `YYYY-MM-DD-session-summary.md`. Update it throughout the session with:
   - Changes made (files modified, features added)
   - Technical decisions and rationale
   - Testing results
   - User-friendly summaries of what was accomplished
   - Keep it updated until explicitly told to stop

4. **Accessibility:** All coding should be WCAG 2.2 AA conformant. This should be a given for this project, so being accessible doesn't need to be highlighted in documentation unless it is something especially unique.

5. **Dual Support:** Work needs to keep in mind that we want to keep support for both the script-based approach for image descriptions and the GUI ImageDescriber app.

6. **No Shortcuts:** Avoid the typical behavior of AI of taking shortcuts, not scanning files completely, and more. This has already resulted in duplicate code at times and extensive time debugging. The project has become too large for constant testing.

7. **Reposatory Hygiene:** Keep the repository clean and organized. Remove unused files, fix broken links, and ensure that documentation is up to date.

8. **Agent Identification:** Always identify yourself at the start of each response using the format `<Claude Sonnet 3.5>` (or your actual model name). This helps users track which AI agent they're working with across sessions.

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

## Viewer Development Patterns

### Accessibility Requirements
- **Single Tab Stops**: Use QListWidget instead of QTableWidget when possible to minimize tab stops
- **Combined Text**: Concatenate data into single strings for list items rather than multiple columns
- **Screen Reader Support**: Always set accessible names/descriptions on widgets
- **Keyboard Navigation**: Ensure all functionality accessible via keyboard (arrows, Enter, tab)

### Date/Time Formatting
- **Standard Format**: `M/D/YYYY H:MMP` (no leading zeros, A/P suffix)
  - Examples: `3/25/2025 7:35P`, `10/16/2025 8:03A`
- **EXIF Extraction Priority**: DateTimeOriginal > DateTimeDigitized > DateTime > file mtime
- **Consistent Across Features**: Use same format for workflow timestamps and image dates

### Window Title Guidelines
- **Always Show Stats**: Display percentage and count when content loaded, not just in live mode
- **Format**: `"XX%, X of Y images described"` (integer percentage, no decimals)
- **Live Mode Indicator**: Add `"(Live)"` suffix when actively monitoring
- **Workflow Name**: Include in title for screen reader context

### Code Reuse
- **Import from scripts**: Reuse functions from `scripts/list_results.py` for workflow scanning
- **Shared Functions**: `find_workflow_directories()`, `count_descriptions()`, `format_timestamp()`
- **Avoid Duplication**: Check if functionality exists elsewhere before implementing

### Error Handling
- **Graceful Degradation**: Always provide fallbacks (e.g., file mtime if no EXIF)
- **Try-Except for Optional**: Use try-except for optional imports and features
- **Clear Messages**: Provide actionable error messages to users
- **Silent Failures**: Don't crash on missing data, log and continue

