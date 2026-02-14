#!/bin/bash
# Finder-launchable wrapper for diagnose_app.sh
# Double-click this file in Finder to run diagnostics

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to that directory
cd "$SCRIPT_DIR"

# Clear the screen for cleaner output
clear

# Run the diagnostic script
./diagnose_app.sh

# Keep terminal window open so user can read results
echo ""
echo "========================================"
echo "Press any key to close this window..."
echo "========================================"
read -n 1 -s
