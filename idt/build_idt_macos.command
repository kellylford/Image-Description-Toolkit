#!/bin/bash
# Make script executable from Finder (macOS .command file)
# Double-click this file in Finder to build IDT for macOS

# Change to script's directory
cd "$(dirname "$0")"

# Run the actual build script
./build_idt.sh

# Keep terminal open to show results
echo ""
echo "Press any key to close..."
read -n 1
