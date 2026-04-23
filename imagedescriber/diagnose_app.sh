#!/bin/bash
# Diagnostic script for ImageDescriber.app launch issues
# Usage: ./diagnose_app.sh

APP_PATH="dist/ImageDescriber.app"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "ImageDescriber.app Diagnostics"
echo "========================================"
echo ""

# Check if app exists
echo "1. Checking if app bundle exists..."
if [ -d "$APP_PATH" ]; then
    echo "   ✓ App bundle found: $APP_PATH"
else
    echo "   ✗ App bundle NOT found at: $APP_PATH"
    echo "   Run ./build_imagedescriber_wx.sh first"
    exit 1
fi
echo ""

# Check executable
echo "2. Checking executable..."
EXEC_PATH="$APP_PATH/Contents/MacOS/ImageDescriber"
if [ -f "$EXEC_PATH" ]; then
    echo "   ✓ Executable exists"
    file "$EXEC_PATH" | sed 's/^/   /'
else
    echo "   ✗ Executable NOT found"
    exit 1
fi
echo ""

# Check code signature
echo "3. Checking code signature..."
codesign -dv "$APP_PATH" 2>&1 | head -10 | sed 's/^/   /'
echo ""

# Verify signature
echo "4. Verifying signature (this may take a moment)..."
if codesign --verify --deep --strict "$APP_PATH" 2>&1; then
    echo "   ✓ Signature is valid"
else
    echo "   ! Signature verification warnings (may be normal for ad-hoc signing)"
fi
echo ""

# Check Python syntax
echo "5. Checking Python source files for syntax errors..."
cd "$SCRIPT_DIR"
for pyfile in imagedescriber_wx.py workers_wx.py data_models.py dialogs_wx.py; do
    if [ -f "$pyfile" ]; then
        if .venv/bin/python -m py_compile "$pyfile" 2>/dev/null; then
            echo "   ✓ $pyfile"
        else
            echo "   ✗ $pyfile has syntax errors!"
            .venv/bin/python -m py_compile "$pyfile"
        fi
    fi
done
echo ""

# Try to launch and capture output
echo "6. Attempting to launch app directly..."
echo "   (Press Ctrl+C after a few seconds if it hangs)"
echo ""
timeout 5 "$EXEC_PATH" 2>&1 || true
echo ""

# Check for crash reports
echo "7. Checking for recent crash reports..."
CRASHES=$(ls -t ~/Library/Logs/DiagnosticReports/ 2>/dev/null | grep -i imagedescriber | head -3)
if [ -n "$CRASHES" ]; then
    echo "   Recent crashes found:"
    echo "$CRASHES" | sed 's/^/   - /'
    echo ""
    echo "   View latest crash log:"
    echo "   less ~/Library/Logs/DiagnosticReports/$(echo "$CRASHES" | head -1)"
else
    echo "   ✓ No recent crash reports"
fi
echo ""

# Check if app is currently running
echo "8. Checking if app is currently running..."
if ps aux | grep -v grep | grep -q "ImageDescriber.app"; then
    echo "   ✓ App is running:"
    ps aux | grep -v grep | grep "ImageDescriber.app" | sed 's/^/   /'
else
    echo "   App is NOT currently running"
fi
echo ""

echo "========================================"
echo "Diagnostics complete!"
echo "========================================"
echo ""
echo "If app still won't launch:"
echo "  1. Check Console.app for error messages"
echo "  2. Run: open '$APP_PATH' from terminal"
echo "  3. Check system logs: log show --predicate 'process == \"ImageDescriber\"' --last 5m"
echo ""
