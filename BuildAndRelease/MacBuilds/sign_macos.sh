#!/bin/bash
# ============================================================================
# Developer ID code signing for IDT macOS builds
# ============================================================================
# Signs an .app bundle or a bare executable with a Developer ID Application
# certificate, under the hardened runtime, with a secure timestamp -- the
# three things Apple requires before notarization will accept a submission.
#
# Usage:
#   bash BuildAndRelease/MacBuilds/sign_macos.sh <path-to-.app-or-binary> [...]
#
# Environment:
#   IDT_SIGNING_IDENTITY   Full identity string, e.g.
#                          "Developer ID Application: Kelly Ford (P887QF74N8)"
#                          If unset, the first Developer ID Application
#                          identity in the keychain is used.
#   IDT_ENTITLEMENTS       Path to entitlements plist.
#                          Defaults to entitlements.plist beside this script.
#   IDT_KEYCHAIN           Optional keychain to search (CI uses a temporary
#                          one so the signing key never touches the login
#                          keychain).
#
# Why not `codesign --deep`:
#   --deep is deprecated by Apple and applies the same entitlements to every
#   nested binary, which is wrong. It also silently skips code it does not
#   recognise. The correct approach is inside-out: sign nested Mach-O objects
#   first, deepest first, then the top-level bundle last. That is what this
#   script does, and it is a no-op on onefile builds that have no nested code.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTITLEMENTS="${IDT_ENTITLEMENTS:-$SCRIPT_DIR/entitlements.plist}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-.app-or-binary> [more paths...]"
    exit 2
fi

if [ ! -f "$ENTITLEMENTS" ]; then
    echo "ERROR: entitlements file not found: $ENTITLEMENTS"
    exit 1
fi

# ----------------------------------------------------------------------------
# Resolve signing identity
# ----------------------------------------------------------------------------
KEYCHAIN_ARGS=()
if [ -n "${IDT_KEYCHAIN:-}" ]; then
    KEYCHAIN_ARGS=(--keychain "$IDT_KEYCHAIN")
fi

IDENTITY="${IDT_SIGNING_IDENTITY:-}"
if [ -z "$IDENTITY" ]; then
    echo "No IDT_SIGNING_IDENTITY set; searching keychain..."
    IDENTITY=$(security find-identity -v -p codesigning ${IDT_KEYCHAIN:+"$IDT_KEYCHAIN"} \
        | grep "Developer ID Application" \
        | head -1 \
        | sed 's/.*"\(.*\)"/\1/') || true
fi

if [ -z "$IDENTITY" ]; then
    echo "ERROR: No Developer ID Application identity found."
    echo "       Set IDT_SIGNING_IDENTITY, or import the certificate first."
    echo ""
    echo "Available codesigning identities:"
    security find-identity -v -p codesigning || true
    exit 1
fi

echo "Signing identity: $IDENTITY"
echo "Entitlements:     $ENTITLEMENTS"
echo ""

# ----------------------------------------------------------------------------
# Sign one Mach-O object. Entitlements are applied only to the top-level
# target -- nested libraries inherit the containing app's entitlements and
# must not carry their own.
# ----------------------------------------------------------------------------
sign_one() {
    local path="$1"
    local with_entitlements="$2"

    # Drop any inherited signature first. Third-party wheels frequently ship
    # .dylib files signed by another team; re-signing over them without
    # removing the old signature can leave a stale team identifier behind.
    codesign --remove-signature "${KEYCHAIN_ARGS[@]+"${KEYCHAIN_ARGS[@]}"}" "$path" 2>/dev/null || true

    if [ "$with_entitlements" = "yes" ]; then
        codesign --force \
            --options runtime \
            --timestamp \
            --entitlements "$ENTITLEMENTS" \
            "${KEYCHAIN_ARGS[@]+"${KEYCHAIN_ARGS[@]}"}" \
            --sign "$IDENTITY" \
            "$path"
    else
        codesign --force \
            --options runtime \
            --timestamp \
            "${KEYCHAIN_ARGS[@]+"${KEYCHAIN_ARGS[@]}"}" \
            --sign "$IDENTITY" \
            "$path"
    fi
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
for TARGET in "$@"; do
    if [ ! -e "$TARGET" ]; then
        echo "ERROR: not found: $TARGET"
        exit 1
    fi

    echo "========================================================================"
    echo "Signing: $TARGET"
    echo "========================================================================"

    if [ -d "$TARGET" ]; then
        # A bundle. Sign nested code inside-out.
        #
        # Note: the current onefile specs produce no Contents/Frameworks, so
        # these loops find nothing and cost nothing. They matter if the specs
        # ever move to onedir (COLLECT), which is the recommended layout if
        # notarization rejects the onefile build.

        # Nested frameworks, deepest path first.
        while IFS= read -r fw; do
            [ -n "$fw" ] || continue
            echo "  framework: ${fw#$TARGET/}"
            sign_one "$fw" no
        done < <(find "$TARGET" -type d -name "*.framework" 2>/dev/null | awk '{print length" "$0}' | sort -rn | cut -d' ' -f2-)

        # Loadable libraries, deepest path first.
        while IFS= read -r lib; do
            [ -n "$lib" ] || continue
            echo "  library:   ${lib#$TARGET/}"
            sign_one "$lib" no
        done < <(find "$TARGET" -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | awk '{print length" "$0}' | sort -rn | cut -d' ' -f2-)

        # The bundle last. This also signs Contents/MacOS/<executable>.
        echo "  bundle:    $(basename "$TARGET")"
        sign_one "$TARGET" yes
    else
        # A bare executable, e.g. the onefile idt CLI.
        sign_one "$TARGET" yes
    fi

    echo ""
    echo "  Verifying..."
    codesign --verify --strict --verbose=2 "$TARGET"

    # Gatekeeper's own assessment. Until the build is notarized this reports
    # rejection, which is expected and not an error at this stage.
    if [ -d "$TARGET" ]; then
        echo "  Gatekeeper assessment (expect rejection until notarized):"
        spctl --assess --type execute --verbose=2 "$TARGET" 2>&1 || true
    fi

    echo "  Signed: $TARGET"
    echo ""
done

echo "========================================================================"
echo "Signing complete"
echo "========================================================================"
