#!/bin/bash
# ============================================================================
# Double-click launcher for macsetup.sh
# ============================================================================
# This wrapper allows double-clicking from Finder to set up the macOS
# environments. It matches the pattern already used by
# BuildAndRelease/MacBuilds/builditall_macos.command.
#
# Until 2026-08-13 this file was a byte-for-byte copy of macsetup.sh apart
# from two header comments. Every change had to be made twice, and nothing
# checked that it was -- so the two could drift silently. Delegating means
# there is one implementation.
#
# No "press any key" prompt here: macsetup.sh already ends with one, and a
# second would make the window need two keypresses to close.
# ============================================================================

cd "$(dirname "$0")" || exit 1

# exec replaces this process, so macsetup.sh's exit code is returned directly.
exec ./macsetup.sh
