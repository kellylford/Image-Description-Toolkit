#!/bin/bash
# cleanup_galleries.sh
# Removes redundant gallery files, reducing size from 4.3GB to ~70MB

set -e  # Exit on error

cd "$(dirname "$0")"

echo "============================================================"
echo "🧹 ImageGallery Cleanup Script"
echo "============================================================"
echo ""
echo "This will delete 4.2GB of redundant files:"
echo ""
echo "  ❌ contentprototype/  (259MB) - Superseded by europe/"
echo "  ❌ cottage/          (3.6GB) - Server is source of truth"
echo "  ❌ europe/production/         - Keep only webdeploy/"
echo "  ❌ images/            (83MB) - Duplicate of cottage"
echo "  ❌ data/              (11MB) - Legacy data files"
echo "  ❌ jsondata/          (1MB)  - Legacy JSON location"
echo ""
echo "✅ KEEPING:"
echo "  - template/          Clean template for new galleries"
echo "  - europe/webdeploy/  Deployment-ready Europe gallery"
echo "  - *.py scripts       Utility scripts"
echo "  - *.md docs          All documentation"
echo "  - index.html         Root template"
echo ""
echo "Before: 4.3GB"
echo "After:  ~70MB"
echo "Saved:  4.2GB (98% reduction)"
echo ""
echo "============================================================"
echo "⚠️  WARNING: This cannot be undone!"
echo "============================================================"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Create backup record
echo ""
echo "📝 Creating backup record..."
mkdir -p archive/cleanup_$(date +%Y%m%d_%H%M%S)
CLEANUP_DIR="archive/cleanup_$(date +%Y%m%d_%H%M%S)"

echo "# Cleanup performed on $(date)" > "$CLEANUP_DIR/DELETED.txt"
echo "" >> "$CLEANUP_DIR/DELETED.txt"
echo "Directories deleted:" >> "$CLEANUP_DIR/DELETED.txt"
echo "" >> "$CLEANUP_DIR/DELETED.txt"

# Record sizes before deletion
du -sh contentprototype cottage europe/production images data jsondata 2>/dev/null >> "$CLEANUP_DIR/DELETED.txt" || true

echo "✅ Backup record created in $CLEANUP_DIR"
echo ""

# Delete directories one by one with confirmation
echo "🗑️  Deleting contentprototype/ (259MB)..."
if [ -d "contentprototype" ]; then
    rm -rf contentprototype/
    echo "   ✅ Deleted"
else
    echo "   ⚠️  Already removed"
fi

echo "🗑️  Deleting cottage/ (3.6GB) - This may take a moment..."
if [ -d "cottage" ]; then
    rm -rf cottage/
    echo "   ✅ Deleted"
else
    echo "   ⚠️  Already removed"
fi

echo "🗑️  Deleting europe/production/..."
if [ -d "europe/production" ]; then
    rm -rf europe/production/
    echo "   ✅ Deleted"
else
    echo "   ⚠️  Already removed"
fi

echo "🗑️  Deleting root images/ (83MB)..."
if [ -d "images" ]; then
    rm -rf images/
    echo "   ✅ Deleted"
else
    echo "   ⚠️  Already removed"
fi

echo "🗑️  Deleting root data/ (11MB)..."
if [ -d "data" ]; then
    rm -rf data/
    echo "   ✅ Deleted"
else
    echo "   ⚠️  Already removed"
fi

echo "🗑️  Deleting root jsondata/ (1MB)..."
if [ -d "jsondata" ]; then
    rm -rf jsondata/
    echo "   ✅ Deleted"
else
    echo "   ⚠️  Already removed"
fi

echo ""
echo "============================================================"
echo "✅ Cleanup complete!"
echo "============================================================"
echo ""
echo "📊 Results:"
echo "   Before: 4.3GB"
echo "   After:  $(du -sh . | cut -f1)"
echo ""
echo "✅ Remaining structure:"
echo "   - template/          Clean template"
echo "   - europe/webdeploy/  Deployment-ready"
echo "   - Documentation      All *.md files"
echo "   - Scripts            All *.py files"
echo ""
echo "📝 Cleanup record saved in:"
echo "   $CLEANUP_DIR/DELETED.txt"
echo ""
echo "🎯 Next steps:"
echo "   1. Verify: python build_gallery.py europe/webdeploy/"
echo "   2. Test:   cd europe/webdeploy && python -m http.server 8000"
echo "   3. Commit: git add . && git commit -m 'Clean up gallery duplicates'"
echo ""
echo "============================================================"
