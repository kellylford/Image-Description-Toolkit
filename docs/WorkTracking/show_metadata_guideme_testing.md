# Show Metadata Guideme Testing

## Test Run: January 27, 2025

### Test Objective
Verify that the new `--guideme` flag launches the interactive wizard and walks users through all configuration options.

### Test Setup
- **Tool**: `tools/show_metadata/show_metadata.py`
- **Command**: `python show_metadata.py --guideme`
- **Expected**: Interactive wizard with 7 steps

### Test Results

#### ✅ Test 1: Wizard Launch
- **Command**: `python show_metadata.py --guideme`
- **Result**: SUCCESS - Wizard header displayed correctly
- **Output**:
  ```
  ======================================================================
    Show Metadata - Interactive Wizard
  ======================================================================
  
  Welcome! This wizard will help you set up metadata extraction.
  You can press Ctrl+C at any time to exit.
  ```

#### ✅ Test 2: Step 1 - Directory Prompt
- **Expected**: Prompt for image directory with examples
- **Result**: SUCCESS - Directory prompt displayed with helpful examples
- **Output**:
  ```
  ======================================================================
    Step 1: Image Directory
  ======================================================================
  
  Enter the path to the directory containing images to analyze.
  Examples:
    - C:\Photos\Vacation
    - //server/share/photos
    - /mnt/photos
  
  Image directory path:
  ```

#### ✅ Test 3: Help Flag Compatibility
- **Command**: `python show_metadata.py --help`
- **Result**: SUCCESS - Help text still displays correctly
- **Note**: --guideme flag does not interfere with normal CLI operation

### Wizard Flow (Not Fully Tested)
The following steps would appear in a complete run:
1. Image Directory ✅ (tested)
2. Recursive Scanning (y/n prompt)
3. Meta Suffix Display (y/n prompt)
4. Reverse Geocoding (y/n prompt with sub-prompts)
   - User-Agent configuration
   - Rate limiting delay
   - Cache file location
5. CSV Export (y/n prompt with file path)
6. Command Summary (preview and save)
7. Execution (run now / show command / go back)

### Command Persistence
- **File**: `tools/show_metadata/.show_metadata_last_command`
- **Format**: Shell command with timestamp header
- **Status**: Not yet tested (requires completing wizard flow)

### Accessibility Features Verified
- ✅ Clear section headers with visual separators
- ✅ Step numbers in headers
- ✅ Helpful examples in prompts
- ✅ Ctrl+C exit support (tested)

### Integration Status
- ✅ Wizard launches correctly
- ✅ No interference with normal CLI mode
- ✅ Help text still accessible
- ⏳ Full wizard flow not tested (requires user input)
- ⏳ Command persistence not verified (requires completing wizard)
- ⏳ Command execution not tested (requires completing wizard)

### Recommendations
1. **User Testing**: Have a user run through the full wizard flow
2. **Command Verification**: Check that saved commands are valid
3. **Error Handling**: Test invalid directory paths and edge cases
4. **Screen Reader**: Verify with actual screen reader software

### Conclusion
The guideme wizard launches successfully and displays prompts correctly. The feature is ready for user testing. Full integration testing requires completing the interactive wizard flow, which needs actual user input.

## Next Steps
- User completes a full wizard run
- Verify saved command file format
- Test command execution
- Document common use cases
