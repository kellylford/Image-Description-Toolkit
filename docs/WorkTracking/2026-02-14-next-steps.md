# Next Steps - February 14, 2026

## Where We Left Off

Successfully fixed Configure dialog Windows crash and consolidated testing branches.

## Immediate Next Steps

### 1. Test and Release Windows Build from WXMigration Branch
- [ ] Download latest Windows build from GitHub Actions (WXMigration branch)
- [ ] Test Configure Settings dialog - verify it opens and accepts keyboard input
- [ ] Test that all functionality works correctly
- [ ] Upload to v4beta release (Option 3: move v4beta tag to WXMigration HEAD)
  - Delete old v4beta tag locally and remote
  - Create new v4beta tag at current WXMigration commit (f53238c)
  - Force push tag
  - Replace release assets with new builds

### 2. Resume MacApp Branch Testing
- [ ] Build ImageDescriber.app from MacApp branch locally
- [ ] Test VoiceOver accessibility improvements:
  - wx.ComboBox → wx.Choice (no crashes)
  - DescriptionListBox shows full text (no truncation)
- [ ] Test Configure Settings dialog on macOS
- [ ] Test geocoding returns English place names
- [ ] Compare experience with WXMigration builds

## Branch Status

**WXMigration** (Windows testing):
- Configure dialog fixes (crash resolved)
- Geocoding English language support
- DescriptionListBox platform-aware (truncated on Windows, full on macOS)
- GitHub Actions automated builds
- Ready for Windows release

**MacApp** (macOS testing):
- All WXMigration fixes PLUS wx.ComboBox → wx.Choice VoiceOver crash fix
- 18 commits since v4beta
- Ready for macOS testing

## Future Work (Not Urgent)

### macOS Automated Builds
When ready to set up GitHub Actions for macOS:
- Need Apple Developer certificate and credentials
- Will create signed, notarized .dmg installers
- Prevents security warnings on download

### Windows Code Signing
Optional for official release:
- Requires separate code signing certificate (~$100-400/year)
- NOT included with Windows Developer account
- Eliminates SmartScreen warnings

## Key Accomplishments This Session

1. ✅ Fixed Configure dialog parent/sizer crash on Windows
2. ✅ Fixed Configure dialog focus handling for screen readers
3. ✅ Added geocoding English language support
4. ✅ Made DescriptionListBox VoiceOver-accessible on macOS
5. ✅ Set up GitHub Actions for automated Windows builds
6. ✅ Consolidated all fixes into MacApp branch for testing

## Technical Notes

- Platform detection in DescriptionListBox uses `sys.platform == 'darwin'`
- Windows builds still use truncation + wx.Accessible
- macOS builds show full text for VoiceOver compatibility
- Configure dialog now uses proper dialog→panel→content hierarchy
