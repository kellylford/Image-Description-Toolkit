# Test Framework for ImageDescriber

This directory contains a contained test framework that mirrors the ImageDescriber app functionality.

## Structure
- `contained_test.py` - Main test script that mirrors ImageDescriber ProcessingWorker
- `results/` - All test outputs are saved here (auto-created)

## Features
- ✅ **Contained**: All files stay within `imagedescriber/test_framework/`
- ✅ **Model Detection**: Automatically detects available Ollama models like the app
- ✅ **Mirrors App Logic**: Uses same ProcessingWorker code patterns
- ✅ **Follow-up Testing**: Tests follow-up questions like the app
- ✅ **Limited Runtime**: Prevents long test runs with configurable limits

## Usage
```bash
cd imagedescriber/test_framework
python contained_test.py
```

## Output
- Results saved to `results/test_results_YYYYMMDD_HHMMSS.json`
- Summary printed to console
- All files contained within this directory

## Configuration
- Modify `max_tests` parameter to control test duration
- Adjust `follow_ups` list for different questions
- Change `prompts` dictionary for different prompt styles
