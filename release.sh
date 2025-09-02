#!/bin/bash
# Release Preparation Script for Image Description Toolkit
# Version 1.0.0

echo "🚀 Preparing Image Description Toolkit v1.0.0 Release"
echo "=================================================="

# Check if we're on the main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "❌ Error: Must be on main branch for release. Currently on: $current_branch"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Working directory not clean. Please commit all changes first."
    git status --short
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/version > /dev/null; then
    echo "❌ Warning: Ollama is not running. Some tests may fail."
    echo "   Start Ollama with: ollama serve"
fi

echo "✅ Git status: Clean working directory on main branch"

# Run tests to ensure everything works
echo ""
echo "🧪 Running test suite..."
cd tests
python run_tests.py
test_result=$?

if [ $test_result -eq 0 ]; then
    echo "✅ All tests passed"
else
    echo "❌ Tests failed. Please fix issues before release."
    exit 1
fi

cd ..

# Check if requirements.txt dependencies can be installed
echo ""
echo "📦 Verifying dependencies..."
pip check > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ All dependencies are compatible"
else
    echo "⚠️  Warning: Some dependency conflicts detected"
    pip check
fi

# Create the release tag
echo ""
echo "🏷️  Creating release tag v1.0.0..."
git tag -a v1.0.0 -m "Release version 1.0.0

🌟 First stable release of Image Description Toolkit

Major features:
- Unified workflow system for complete media processing pipeline
- Comprehensive model testing with detailed analytics
- AI-powered image descriptions using local Ollama models
- Video frame extraction and HEIC image conversion
- Professional HTML report generation
- Qt6 GUI viewer application with Copy Image Path functionality
- Complete documentation and testing suite

See CHANGELOG.md for detailed release notes."

echo "✅ Tag v1.0.0 created"

# Display next steps
echo ""
echo "🎉 Release v1.0.0 is ready!"
echo ""
echo "📋 Next steps:"
echo "   1. Push the tag to GitHub: git push origin v1.0.0"
echo "   2. Create a GitHub release using the tag"
echo "   3. Upload any release assets (if needed)"
echo "   4. Announce the release"
echo ""
echo "📝 Release notes are available in CHANGELOG.md"
echo "📖 Documentation is ready in README.md and docs/"
echo "🧪 Test suite can be run with: cd tests && python run_tests.py"
echo ""
echo "🚀 Ready to ship! 🎊"
