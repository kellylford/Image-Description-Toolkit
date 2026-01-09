#!/bin/bash
# ============================================================================
# Double-click launcher for build_viewer_wx.sh
# ============================================================================
# This wrapper allows double-clicking from Finder to run the wxPython build
# ============================================================================

# Change to the script's directory
cd "$(dirname "$0")"

# Run the actual build script
./build_viewer_wx.sh

# Keep terminal open on completion (remove these lines if you don't want this)
echo ""
echo "Press any key to close..."
read -n 1 -s
