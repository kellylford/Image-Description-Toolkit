# Image Description Toolkit - Project Roadmap

**Date:** October 6, 2025  
**Status:** Planning Phase  
**Current Focus:** Simplification and Release Preparation

---

## Executive Summary

After extensive testing with multiple AI providers (Ollama, OpenAI, Claude, ONNX, HuggingFace, GroundingDINO, YOLO), we've identified that the **core narrative description functionality** is what provides the most value. The object detection and NPU-based approaches, while technically interesting, add significant installation complexity without proportional benefit to description quality.

**Key Decision:** Simplify to three proven cloud/local providers (Claude, Ollama, OpenAI) + prepare for Gemini, then focus on packaging and release.

---

## Strategic Observations

### What Works Well
1. ✅ **Narrative descriptions** from Claude, Ollama, OpenAI are excellent quality
2. ✅ **Workflow system** (import, resume, batch processing) is solid
3. ✅ **ImageDescriber GUI** is functional and actively used
4. ✅ **Video frame extraction** and **HEIC conversion** work reliably
5. ✅ **HTML gallery generation** provides good visualization
6. ✅ **Multi-provider comparison** tools (combine_workflow_descriptions.py) are valuable

### What Adds Complexity Without Proportional Value
1. ❌ **ONNX models** - Installation complexity, limited narrative capability
2. ❌ **HuggingFace models** - Large downloads, variable quality, setup issues
3. ❌ **GroundingDINO** - Object detection useful but not for narrative descriptions
4. ❌ **YOLO integration** - Similar to GroundingDINO - specialized use case
5. ❌ **Copilot+ NPU** - Great concept but not ready for narrative descriptions yet

### The Core Problem with Object Detection
Object detection **reduces description quality** when used as a pre-filter:
- Ollama/Claude/OpenAI can describe items the detector missed
- Passing only detected objects limits the narrative scope
- The AI models already "see" the full image - why pre-filter?

**Conclusion:** Object detection has value for specialized tasks (counting, locating, filtering) but should NOT be in the primary narrative description workflow.

---

## Project Phases (Ordered)

### Phase 1: Model Removal & Simplification ⏳ CURRENT
**Goal:** Remove ONNX, HuggingFace, GroundingDINO, YOLO, Copilot+ from codebase  
**Outcome:** Clean codebase with Claude, Ollama, OpenAI only  
**Status:** Planning complete, awaiting approval

### Phase 2: Testing & Validation 📋 NEXT
**Goal:** Comprehensive testing of remaining providers  
**Tests:**
- Workflow scripts (video, convert, describe, html)
- ImageDescriber GUI (all tabs, import, resume)
- Batch processing with all three providers
- Edge cases (interruption, resume, large batches)

### Phase 3: Add Google Gemini 🆕 PENDING API KEY
**Goal:** Integrate fourth proven provider  
**Requirements:** Google API key from user  
**Approach:** Use Claude integration as template

### Phase 4: Bug Fixes 🐛 ONGOING
**Goal:** Fix issues discovered in testing  
**Priority:** Critical bugs blocking usage

### Phase 5: Packaging & Distribution 📦 FUTURE
**Goal:** Release as executable/installable package  
**Options:**
- PyInstaller for standalone executable
- Python wheel/pip package
- Docker container
- Conda package

### Phase 6: Documentation Rewrite 📝 FUTURE
**Goal:** Complete documentation refresh based on simplified codebase  
**Scope:**
- User guides for Claude/Ollama/OpenAI/Gemini
- Installation guide (simplified)
- Workflow examples
- Batch file templates
- Troubleshooting

### Phase 7: Release 🚀 FUTURE
**Goal:** Public release with simplified feature set  
**Version:** 2.0.0 (major version for breaking changes)

### Phase 8: Model Management Refactoring 🔧 FUTURE
**Goal:** Simplify model detection to < 5 steps  
**Current:** 20+ step process across multiple files  
**Target:** Centralized registry pattern with auto-detection

### Phase 9: Metadata Support 💾 FUTURE
**Goal:** Preserve and manage image metadata across workflow  
**Features:**
- EXIF preservation
- Description metadata embedding
- Cross-tool metadata sync

---

## Feedback on Proposed Plan

### ✅ Excellent Decisions

1. **Simplification First** - Removing complexity before release is the right move
2. **Testing Before Adding** - Validating current functionality before Gemini is smart
3. **Packaging Focus** - Making it easy to install/use is critical for adoption
4. **Documentation Last** - Documenting the final state prevents rework
5. **Metadata as Future Work** - Nice-to-have but not blocking release

### 💡 Suggested Refinements

#### Phase 2 (Testing)
- Consider creating automated test suite
- Document test cases in worktracking folder
- Create testing checklist for manual validation

#### Phase 5 (Packaging)
**Recommendation:** Start with **PyInstaller** for simplicity
- Creates standalone .exe (Windows) or binary (Mac/Linux)
- Users don't need Python installed
- Can bundle dependencies
- Relatively simple to maintain

**Pros:**
- One-click installation
- No dependency management for users
- Works on systems without Python

**Cons:**
- Large file size (~200-500MB)
- Still need Ollama installed separately (for local models)
- API keys still need manual setup

**Alternative Approaches:**
1. **Python Wheel** - For Python users, simpler but requires Python
2. **Docker** - Great for reproducibility, harder for non-technical users
3. **Conda** - Best for data science users, requires Conda ecosystem

**My Recommendation:** PyInstaller + clear documentation for Ollama installation

#### Phase 8 (Model Management)
**Critical Success Factor:** This is where future extensibility lives
- Consider provider plugin architecture
- Auto-discovery of models
- Centralized capability matrix
- Single registration point for new providers

### 🎯 Priority Adjustments

**Consider moving up:**
- Basic automated testing (Phase 2) - prevents regression
- Packaging exploration (Phase 5) - might reveal issues early

**Consider deferring:**
- Metadata support (Phase 9) - significant scope, low urgency

---

## Success Metrics

### Phase 1 Success
- [ ] All ONNX references removed
- [ ] All HuggingFace references removed
- [ ] All GroundingDINO references removed
- [ ] All YOLO references removed
- [ ] All Copilot+ references removed
- [ ] Code runs without errors
- [ ] No broken imports

### Phase 2 Success
- [ ] All workflow steps tested (video, convert, describe, html)
- [ ] All three providers tested in GUI
- [ ] Import/resume functionality validated
- [ ] Batch processing (100+ images) validated
- [ ] No crashes or data loss

### Phase 7 Success (Release)
- [ ] Installation takes < 10 minutes
- [ ] User can generate first description in < 5 minutes
- [ ] Documentation answers 90% of common questions
- [ ] Zero critical bugs reported in first week

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Model Removal | 2-3 hours | None |
| 2. Testing | 4-6 hours | Phase 1 complete |
| 3. Add Gemini | 1-2 hours | API key provided |
| 4. Bug Fixes | Variable | Issues discovered |
| 5. Packaging | 8-12 hours | Phase 2 complete |
| 6. Documentation | 12-16 hours | Phase 5 complete |
| 7. Release | 2-4 hours | Phase 6 complete |
| 8. Refactoring | 8-12 hours | Post-release |
| 9. Metadata | 16-20 hours | Post-release |

**Total to Release:** ~30-45 hours of work

---

## Risk Assessment

### High Risk 🔴
- **Packaging complexity** - May reveal unforeseen dependency issues
- **Model removal** - Could break unexpected functionality

### Medium Risk 🟡
- **Testing coverage** - Manual testing may miss edge cases
- **Documentation scope** - Larger than estimated

### Low Risk 🟢
- **Gemini integration** - Well-understood pattern (similar to Claude)
- **Bug fixes** - Typical development work

---

## Notes for Implementation

### When Removing Models
1. **Be systematic** - Use the checklist from Claude integration (reversed)
2. **Test after each provider removal** - Don't remove all at once
3. **Keep commits separate** - One provider per commit for easy rollback
4. **Check imports** - Many files import these providers
5. **Update batch files** - BatForScripts directory has examples

### For Packaging
1. **Start simple** - Basic PyInstaller first
2. **Test on clean machine** - Critical for validating dependencies
3. **Document installer creation** - So it can be repeated
4. **Consider size** - Look for ways to reduce package size

### For Documentation
1. **Screenshots** - Updated for simplified interface
2. **Quick start** - 5 minutes to first description
3. **Examples** - Real-world use cases
4. **Troubleshooting** - Common issues and solutions

---

## Open Questions

1. **Should we keep object detection as optional/advanced feature?**
   - Pros: Some users may want it
   - Cons: Adds complexity, maintenance burden
   - Recommendation: Remove for 2.0, consider plugin for 2.1+

2. **What about users who installed ONNX/HuggingFace?**
   - Migration guide in documentation
   - Clear communication about removed features
   - Explain benefits of simplification

3. **Ollama Cloud models?**
   - Keep or remove alongside ONNX/HF?
   - Recommendation: Keep - it's just an Ollama variant, minimal complexity

4. **Version numbering for release?**
   - 2.0.0 (breaking changes)
   - Or 1.0.0 (first "real" release)
   - Recommendation: 2.0.0 to signal major refactoring

---

## Next Steps

1. **Review this roadmap** - Get user feedback/approval
2. **Create removal plan** - Detailed checklist (separate document)
3. **Begin Phase 1** - Start removing models systematically
4. **Daily check-ins** - Brief status updates during active phases

---

**Last Updated:** October 6, 2025  
**Next Review:** After Phase 1 completion
