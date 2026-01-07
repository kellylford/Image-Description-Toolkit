#!/bin/bash
# ============================================================================
# Double-click launcher for create_macos_dmg.sh
# ============================================================================
# This wrapper allows double-clicking from Finder to create a DMG installer
# ============================================================================

# Change to the script's directory
cd "$(dirname "$0")"

# Run the actual DMG creation script
./create_macos_dmg.sh

# Keep terminal open on completion (remove these lines if you don't want this)
echo ""
echo "Press any key to close..."
read -n 1 -s
