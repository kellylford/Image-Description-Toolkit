#!/bin/bash
# build_executable.sh - Automated IDT executable build script

set -e  # Exit on any error

echo "🔨 Building IDT Executable..."

# Clean previous builds
echo "📁 Cleaning previous builds..."
rm -rf build/ dist/

# Verify Python environment
echo "🐍 Checking Python environment..."
python --version
pip list | grep -E "(PyInstaller|Pillow|requests)"

# Run tests on source code
echo "🧪 Running source code tests..."
python -c "import scripts.workflow; print('✅ workflow module imports')"
python -c "import scripts.workflow_utils; print('✅ workflow_utils module imports')"
python -c "import scripts.config_loader; print('✅ config_loader module imports')"

# Build executable
echo "🏗️ Building executable with PyInstaller..."
python -m PyInstaller final_working.spec

# Verify executable
echo "🔍 Testing executable..."
if [ -f "dist/idt.exe" ]; then
    echo "✅ Executable created successfully"
    
    # Test basic functionality
    echo "🧪 Testing executable functionality..."
    cd dist
    ./idt.exe --help > /dev/null && echo "✅ Help command works"
    ./idt.exe workflow --help > /dev/null && echo "✅ Workflow command works"
    ./idt.exe check-models --help > /dev/null && echo "✅ Check-models command works"
    cd ..
    
    # Show file info
    echo "📊 Executable info:"
    ls -lh dist/idt.exe
    
    # Copy for batch file compatibility
    echo "📋 Copying executable for batch file compatibility..."
    cp dist/idt.exe ./
    if [ -f "idt.exe" ]; then
        echo "✅ Copied to root directory for easier batch file usage"
    else
        echo "⚠️ Failed to copy executable to root directory"
    fi
    
else
    echo "❌ Executable build failed!"
    exit 1
fi

echo "🎉 Build complete!"
echo "📁 Executable locations:"
echo "  - dist/idt.exe (main build output)"
echo "  - idt.exe (copied for batch file compatibility)"