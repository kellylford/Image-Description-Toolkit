---
name: Improve Menu Selection in guideme Command
about: Enhance the interactive menu with arrow key navigation and better accessibility
title: 'Improve menu selection in `idt guideme` with arrow key navigation'
labels: enhancement, accessibility, user-experience
assignees: ''
---

## Summary
The `idt guideme` command currently uses numbered selection for menu choices. This works well for screen readers but could be enhanced with arrow key navigation while maintaining accessibility.

## Current Implementation
- Users type numbers (1-N) to select options
- ✅ Screen reader friendly (reads full lists)
- ✅ No dependencies required
- ✅ Works everywhere
- ❌ Requires more typing

## Proposed Enhancement
Add arrow key navigation with a visible system cursor that screen readers can track.

## Implementation Options

### Option 1: `pick` library (Recommended)
**Package**: https://pypi.org/project/pick/
- ✅ Small dependency (~10KB)
- ✅ Cross-platform (Windows, Mac, Linux)
- ✅ Arrow key navigation
- ✅ Visual cursor that screen readers can track
- ✅ Simple API
- ✅ Well-maintained
- ❌ Adds one dependency

**Example Usage**:
```python
from pick import pick

options = ['ollama', 'openai', 'claude']
selected, index = pick(options, 'Select a provider:', indicator='=>')
```

### Option 2: `prompt_toolkit`
**Package**: https://pypi.org/project/prompt-toolkit/
- ✅ Professional, feature-rich CLI framework
- ✅ Excellent accessibility support
- ✅ Better styling and customization
- ✅ Used by many major projects (IPython, pgcli, etc.)
- ❌ Larger dependency (~600KB)
- ❌ More complex API
- ❌ May be overkill for simple menus

**Example Usage**:
```python
from prompt_toolkit.shortcuts import radiolist_dialog

result = radiolist_dialog(
    title="Select Provider",
    text="Which AI provider would you like to use?",
    values=[
        ('ollama', 'Ollama'),
        ('openai', 'OpenAI'),
        ('claude', 'Claude')
    ]
).run()
```

### Option 3: `simple-term-menu`
**Package**: https://pypi.org/project/simple-term-menu/
- ✅ Good middle ground
- ✅ Arrow key navigation
- ✅ Customizable
- ✅ Screen reader support
- ❌ Unix/Linux focused (Windows support requires windows-curses)

### Option 4: Keep current numbered selection + add optional arrow mode
- Detect if terminal supports advanced features
- Fallback to numbered selection if not
- Best of both worlds but adds complexity

## Files to Update
1. `scripts/guided_workflow.py` - Update menu selection functions
2. `requirements.txt` - Add chosen library
3. `final_working.spec` - Ensure library is bundled in executable

## Accessibility Considerations
- **Critical**: Any solution must maintain a visible system cursor position
- Screen readers need to be able to track selection
- Should work with NVDA, JAWS, Narrator, VoiceOver
- Keyboard-only navigation must remain fully functional
- Should provide audio/text feedback on selection

## Testing Requirements
- [ ] Test with NVDA on Windows
- [ ] Test with JAWS on Windows  
- [ ] Test with Narrator on Windows
- [ ] Test with VoiceOver on macOS
- [ ] Test in standard terminals (CMD, PowerShell, bash)
- [ ] Test in IDE terminals (VS Code, PyCharm)
- [ ] Test when compiled as executable
- [ ] Verify fallback behavior if terminal doesn't support features

## Recommendation
Start with **Option 1 (`pick`)** because:
1. Smallest dependency
2. Purpose-built for this exact use case
3. Proven cross-platform support
4. Easy to implement
5. Can always upgrade to prompt_toolkit later if needed

## Priority
**Medium** - Current implementation works well, this is a UX enhancement for future release.

## Additional Notes
- This enhancement should not break existing functionality
- Consider making it optional via environment variable or flag
- Document the behavior in user guide
- Add to release notes when implemented
