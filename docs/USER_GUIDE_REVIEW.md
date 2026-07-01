<!-- AI-generated review of USER_GUIDE.md by gemma4:31b-cloud on 2026-07-01 -->

This is a comprehensive and well-structured user guide. It successfully bridges the gap between a technical CLI reference and a functional GUI manual. The inclusion of accessibility standards (WCAG 2.2 AA) is a standout feature and is well-documented.

Below is the structured review.

---

## 1. Summary
The guide provides end-to-end documentation for the Image Description Toolkit (IDT), covering installation, configuration, and usage for both the `idt` CLI and the `ImageDescriber` GUI. It details AI provider integration, workspace management, video frame extraction, and metadata embedding, with a strong emphasis on accessibility and cross-platform compatibility.

## 2. Strengths
*   **Dual-Interface Harmony:** The guide clearly explains how the CLI and GUI interact via the `.idtw` workspace format, encouraging users to use the tool that fits their current task.
*   **Accessibility Focus:** Explicitly documenting screen reader compatibility and keyboard navigation is excellent and aligns with the project's goal of supporting accessibility workflows.
*   **Technical Depth:** The inclusion of the `.idtw` folder structure and `manifest.json` schema is invaluable for power users and contributors.
*   **Clear Onboarding:** The "Quick Start" and "Interactive Wizard" sections lower the barrier to entry for new users.
*   **Comprehensive Provider Coverage:** The breakdown of local vs. cloud providers, including specific model recommendations, is highly practical.

## 3. Issues Found

### Missing Content
*   **Uninstallation:** There are instructions for installation, but no guidance on how to cleanly remove the tools or clear the `~/.idt` config directory.
*   **Updating the Software:** The guide doesn't explain how to update to a newer version (e.g., whether to re-download the executable or `git pull` for source installs).
*   **Prompt Examples:** While prompt *styles* are listed, there are no examples of the *actual output* these prompts produce. Users cannot judge if "narrative" vs "detailed" meets their needs without seeing a sample description.

### Outdated or Inaccurate Information
*   **Model Versions:** In "Anthropic Claude," the guide lists `claude-opus-4-6` and `claude-sonnet-4-6`. As of current knowledge, Claude 3.5 is the standard; "4-6" appears to be a placeholder or a versioning error.
*   **MLX Availability:** The guide states MLX is "GUI only," but then suggests `pip install mlx-vlm` in the setup. If it is truly GUI-only, the installation step should be clarified as a dependency for the GUI.

### Inconsistencies
*   **Provider Naming:** The guide acknowledges that names differ between CLI and GUI (e.g., `anthropic` vs `claude`), but this creates a high cognitive load. 
    *   *Example:* In "Part 4: AI Providers," the header says "Anthropic Claude," but the text switches between the two names frequently.
*   **Shortcut Discrepancies:** In "Appendix D," the "View and Navigation" table lists `F5` for both "Update Image List" and "Filter: All Items."

### Clarity Problems
*   **"Workspace Bundle" vs "Folder":** The term "bundle" is used for `.idtw` folders. For non-technical users, "bundle" often implies a single compressed file (like a .zip). It should be explicitly stated that `.idtw` is a directory.
*   **HEIC Requirements:** The guide mentions `pillow-heif` is required for HEIC support, but it is listed under "Advanced Features" and "Troubleshooting" rather than the primary "System Requirements" or "Installation" sections.

### Formatting Issues
*   **Heading Hierarchy:** The transition from "Part 1" to "Appendix" is clear, but some sub-sections (like "The Prompt Editor") are referenced as links before they appear in the text, which can be jarring in a static PDF/Print version.

### Accessibility Gaps
*   **Color-Coded Status Icons:** In "The Main Window Layout," status is indicated by `[✓]`, `[ ]`, and `[!]`. While these are text-based, the guide should confirm if these icons have associated ARIA labels or text equivalents for screen readers.

---

## 4. Recommended Updates

### Priority 1: Critical / Accuracy (High)
1.  **Verify Model Versions:** Correct the Claude model versions (e.g., change `4-6` to `3.5 Sonnet` or the correct current version).
2.  **Fix Shortcut Conflict:** Resolve the `F5` key conflict in Appendix D.
3.  **Clarify `.idtw`:** Explicitly define "Workspace Bundle" as a "specialized folder" in the Overview to avoid confusion with archive files.

### Priority 2: User Experience (Medium)
1.  **Add "Sample Outputs":** Create a small table or gallery showing a "Concise" vs "Detailed" description for the same image.
2.  **Consolidate HEIC Dependencies:** Move the `pillow-heif` requirement to the "System Requirements" section so users don't encounter errors during their first run.
3.  **Add Update Instructions:** Provide a 3-step guide on how to update the pre-built executables.

### Priority 3: Polish & Maintenance (Low)
1.  **Uninstallation Guide:** Add a brief section on how to remove the software and its configuration files.
2.  **Provider Mapping Table:** Create a simple "Translation Table" at the start of Part 4:
    *   *CLI Name $\rightarrow$ GUI Name*
    *   *anthropic $\rightarrow$ claude*
    *   *florence $\rightarrow$ huggingface*
3.  **Accessibility Verification:** Add a note confirming that the `[✓]` and `[!]` icons are announced as "Described" or "Missing" by screen readers.
