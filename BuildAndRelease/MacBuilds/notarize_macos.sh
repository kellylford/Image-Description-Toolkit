#!/bin/bash
# ============================================================================
# Notarize and staple an IDT macOS distributable
# ============================================================================
# Submits a .dmg (or .zip / .pkg) to Apple's notary service, waits for the
# verdict, and staples the ticket so the app validates offline.
#
# Usage:
#   bash BuildAndRelease/MacBuilds/notarize_macos.sh <path-to-.dmg-or-.zip>
#
# Credentials -- one of these two sets must be present.
#
#   App Store Connect API key (preferred, and what CI uses):
#     NOTARY_KEY_PATH     Path to the AuthKey_XXXXXXXXXX.p8 file
#     NOTARY_KEY_ID       The 10-character Key ID
#     NOTARY_ISSUER_ID    The issuer UUID from App Store Connect
#
#   Apple ID (fallback for local use):
#     NOTARY_APPLE_ID     Apple ID email
#     NOTARY_PASSWORD     App-specific password (NOT the account password)
#     NOTARY_TEAM_ID      Team ID, e.g. P887QF74N8
#
# The previous inline notarization block in create_macos_dmg.sh referenced a
# $PROFILE_NAME variable that was never assigned. Under `set -u` that would
# have aborted the script. It was unreachable in practice because SIGN_CODE
# was hardcoded to 0. This script replaces it.
#
# Stapling note: `stapler` works on .app, .dmg and .pkg, but NOT on a bare
# executable. The idt CLI therefore gets its ticket by being inside the
# notarized DMG rather than on its own.
# ============================================================================

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-.dmg-or-.zip>"
    exit 2
fi

TARGET="$1"

if [ ! -e "$TARGET" ]; then
    echo "ERROR: not found: $TARGET"
    exit 1
fi

# ----------------------------------------------------------------------------
# Build credential arguments
# ----------------------------------------------------------------------------
CRED_ARGS=()

if [ -n "${NOTARY_KEY_PATH:-}" ] && [ -n "${NOTARY_KEY_ID:-}" ] && [ -n "${NOTARY_ISSUER_ID:-}" ]; then
    if [ ! -f "$NOTARY_KEY_PATH" ]; then
        echo "ERROR: NOTARY_KEY_PATH set but file does not exist: $NOTARY_KEY_PATH"
        exit 1
    fi
    echo "Using App Store Connect API key (Key ID: $NOTARY_KEY_ID)"
    CRED_ARGS=(--key "$NOTARY_KEY_PATH" --key-id "$NOTARY_KEY_ID" --issuer "$NOTARY_ISSUER_ID")

elif [ -n "${NOTARY_APPLE_ID:-}" ] && [ -n "${NOTARY_PASSWORD:-}" ] && [ -n "${NOTARY_TEAM_ID:-}" ]; then
    echo "Using Apple ID credentials ($NOTARY_APPLE_ID)"
    CRED_ARGS=(--apple-id "$NOTARY_APPLE_ID" --password "$NOTARY_PASSWORD" --team-id "$NOTARY_TEAM_ID")

else
    echo "ERROR: No notarization credentials found."
    echo ""
    echo "Set either:"
    echo "  NOTARY_KEY_PATH + NOTARY_KEY_ID + NOTARY_ISSUER_ID   (API key)"
    echo "or:"
    echo "  NOTARY_APPLE_ID + NOTARY_PASSWORD + NOTARY_TEAM_ID   (Apple ID)"
    exit 1
fi

# ----------------------------------------------------------------------------
# Submit
# ----------------------------------------------------------------------------
echo ""
echo "========================================================================"
echo "SUBMITTING TO APPLE NOTARY SERVICE"
echo "========================================================================"
echo "File: $TARGET"
echo "This usually takes 2-15 minutes."
echo ""

SUBMIT_LOG=$(mktemp)
trap 'rm -f "$SUBMIT_LOG"' EXIT

if xcrun notarytool submit "$TARGET" "${CRED_ARGS[@]}" --wait 2>&1 | tee "$SUBMIT_LOG"; then
    :
fi

# Pull the submission id out so the full log can be fetched either way.
SUBMISSION_ID=$(grep -Eo '\bid: [0-9a-f-]{36}' "$SUBMIT_LOG" | head -1 | awk '{print $2}' || true)

if grep -q "status: Accepted" "$SUBMIT_LOG"; then
    echo ""
    echo "Notarization accepted."
else
    echo ""
    echo "========================================================================"
    echo "NOTARIZATION FAILED"
    echo "========================================================================"
    if [ -n "$SUBMISSION_ID" ]; then
        echo "Fetching the detailed log for submission $SUBMISSION_ID..."
        echo ""
        # This log names the exact offending binary and reason, which the
        # summary output above does not.
        xcrun notarytool log "$SUBMISSION_ID" "${CRED_ARGS[@]}" || true
    fi
    exit 1
fi

# ----------------------------------------------------------------------------
# Staple
# ----------------------------------------------------------------------------
echo ""
echo "Stapling the notarization ticket..."
xcrun stapler staple "$TARGET"
xcrun stapler validate "$TARGET"

echo ""
echo "========================================================================"
echo "NOTARIZED AND STAPLED: $TARGET"
echo "========================================================================"
echo ""
echo "Verify on a clean machine with:"
echo "  spctl --assess --type open --context context:primary-signature -v \"$TARGET\""
