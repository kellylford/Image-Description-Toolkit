# ImageGallery Cleanup Plan - October 25, 2025

## Current State (4.3GB Total)

```
ImageGallery/
├── contentprototype/    259MB  ❌ DELETE - Superseded by europe/webdeploy/
├── cottage/            3.6GB  ❌ DELETE - Server (idtdemo) is source of truth
├── europe/             259MB  ⚠️  KEEP webdeploy/, DELETE production/
├── images/              83MB  ❌ DELETE - Duplicate of cottage images + temp files
├── data/                11MB  ❌ DELETE - Legacy data files
├── jsondata/           ~1MB   ❌ DELETE - Legacy location, superseded by galleries
└── template/            ~1MB  ✅ KEEP - Clean template for new galleries
```

## Analysis

### 1. contentprototype/ (259MB) - DELETE ❌

**What it is**: Working directory used to develop the europe gallery

**Contents**:
- images/ - 25 Europe images (SAME as europe/webdeploy/images/)
- descriptions/ - Workflow outputs
- Various scripts and bat files

**Why delete**: 
- ✅ Europe gallery is complete in europe/webdeploy/
- ✅ Images are duplicated
- ✅ Scripts are duplicated from root
- ✅ Only served as development workspace

**Action**: DELETE entire directory

### 2. cottage/ (3.6GB) - DELETE ❌

**What it is**: Local copy of cottage gallery

**Contents**:
- production/ - Working directory with descriptions/
- webdeploy/ - Deployment-ready files (images + jsondata)

**Why delete**:
- ✅ Server (kellford.com/idtdemo) is the source of truth
- ✅ Server version is working and tested
- ✅ 3.6GB is largest directory (mostly workflow outputs)
- ✅ Can be recreated from source images if needed

**Action**: DELETE entire directory

### 3. europe/production/ - DELETE ❌

**What it is**: Working directory for europe gallery

**Keep**: europe/webdeploy/ (deployment-ready files)
**Delete**: europe/production/ (working files with descriptions/)

**Why**:
- ✅ webdeploy/ is the clean deployment version
- ✅ production/ contains large workflow outputs
- ✅ Descriptions can be regenerated from workflows

**Action**: DELETE europe/production/ only

### 4. Root images/ (83MB) - DELETE ❌

**What it is**: Cottage images plus temp evaluation file

**Contents**:
- 25 cottage images (IMG_4276-4302, photo-20825)
- 1 text file: alt_text_evaluation_summary_*.txt

**Why delete**:
- ✅ Images are duplicated in cottage/webdeploy/images/
- ✅ Text file is temporary evaluation output
- ✅ Not needed for gallery operations
- ⚠️  NOTE: If deleting cottage/, keep ONE copy somewhere

**Action**: 
- If keeping cottage/: DELETE images/
- If deleting cottage/: MOVE images to backup first, then delete

### 5. Root data/ (11MB) - DELETE ❌

**What it is**: Legacy data directory

**Contents**:
- jsondata/ - JSON config files (39 files)
- CSV exports
- Log files

**Why delete**:
- ✅ JSON files are superseded by cottage/europe webdeploy/
- ✅ CSV/logs are old analysis outputs
- ✅ Can be regenerated if needed

**Action**: DELETE entire directory

### 6. Root jsondata/ (39 JSON files, ~1MB) - DELETE ❌

**What it is**: Legacy JSON location

**Why delete**:
- ✅ Old location before gallery-data/ structure
- ✅ Superseded by individual gallery jsondata/ folders
- ✅ Configs are for cottage gallery (now on server)

**Action**: DELETE entire directory

## What to KEEP

### ✅ Essential Files (Keep)

```
ImageGallery/
├── index.html              ✅ Root template (6de91fb)
├── build_gallery.py        ✅ Gallery builder script
├── generate_*.py           ✅ Utility scripts
├── *.md                    ✅ All documentation
├── .gitignore              ✅ Source control config
├── template/               ✅ Clean template
│   ├── index.html
│   ├── README.md
│   ├── images/.gitkeep
│   └── jsondata/.gitkeep
├── archive/                ✅ Historical documentation
└── europe/                 ✅ Current deployment
    ├── README.md
    └── webdeploy/
        ├── index.html
        ├── images/ (25 images, 65MB)
        └── jsondata/ (5 configs)
```

**Total after cleanup**: ~70MB (from 4.3GB) - **98% reduction!**

## Cleanup Script

```bash
#!/bin/bash
# cleanup_galleries.sh

cd /path/to/Image-Description-Toolkit/tools/ImageGallery

echo "🧹 ImageGallery Cleanup Script"
echo "This will delete 4.2GB of redundant files"
echo ""
echo "Directories to DELETE:"
echo "  - contentprototype/ (259MB)"
echo "  - cottage/ (3.6GB)"
echo "  - europe/production/"
echo "  - images/ (83MB)"
echo "  - data/ (11MB)"
echo "  - jsondata/ (1MB)"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Create backup record
echo "Creating backup record..."
mkdir -p archive/cleanup_$(date +%Y%m%d)
echo "Deleted directories on $(date)" > archive/cleanup_$(date +%Y%m%d)/DELETED.txt
du -sh contentprototype cottage europe/production images data jsondata >> archive/cleanup_$(date +%Y%m%d)/DELETED.txt

# Delete directories
echo "Deleting contentprototype/..."
rm -rf contentprototype/

echo "Deleting cottage/..."
rm -rf cottage/

echo "Deleting europe/production/..."
rm -rf europe/production/

echo "Deleting root images/..."
rm -rf images/

echo "Deleting root data/..."
rm -rf data/

echo "Deleting root jsondata/..."
rm -rf jsondata/

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Before: 4.3GB"
echo "After:  ~70MB"
echo "Saved:  4.2GB (98% reduction)"
echo ""
echo "Remaining:"
echo "  - template/ (clean template)"
echo "  - europe/webdeploy/ (deployment-ready)"
echo "  - Documentation files"
echo "  - Python scripts"
```

## Safety Measures

### Before Running Cleanup

1. **Verify server deployment**:
   ```bash
   # Check idtdemo is working
   curl -I https://www.kellford.com/idtdemo/
   ```

2. **Verify europe gallery built**:
   ```bash
   python build_gallery.py europe/webdeploy/
   # Should show "✅ Gallery build complete!"
   ```

3. **List what will be deleted**:
   ```bash
   du -sh contentprototype cottage europe/production images data jsondata
   ```

4. **Optional: Create archive**:
   ```bash
   # If you want to keep a compressed backup
   tar -czf ../ImageGallery_backup_$(date +%Y%m%d).tar.gz \
       contentprototype/ cottage/ images/ data/ jsondata/
   ```

### After Cleanup Verification

1. **Check remaining structure**:
   ```bash
   ls -lh
   du -sh .
   ```

2. **Verify template works**:
   ```bash
   python build_gallery.py template/
   # Should show "No images found" (expected)
   ```

3. **Verify europe still works**:
   ```bash
   cd europe/webdeploy/
   python -m http.server 8000
   # Test in browser
   ```

## Recovery Plan

If you need to recreate galleries:

### Cottage Gallery
- Source: https://www.kellford.com/idtdemo/ (live server)
- Can download if needed
- Or recreate from original 25 source images

### Europe Gallery
- Still exists: europe/webdeploy/
- Source images can be re-selected from originals
- Descriptions can be regenerated with IDT workflows

## Post-Cleanup Structure

```
ImageGallery/              ~70MB total
├── index.html             Template (97KB)
├── build_gallery.py       Builder script
├── generate_*.py          Utility scripts
├── *.md                   Documentation (~50KB)
├── .gitignore             
├── archive/               Historical docs
│   └── cleanup_20251025/  Record of deleted items
├── template/              Clean template
│   ├── index.html
│   ├── README.md
│   ├── images/.gitkeep
│   └── jsondata/.gitkeep
└── europe/                ~65MB
    ├── README.md
    └── webdeploy/
        ├── index.html
        ├── images/ (25 images)
        └── jsondata/ (5 configs)
```

## Recommendations

1. **Run cleanup**: Saves 4.2GB, keeps everything essential
2. **Update .gitignore**: Already done (excludes large files)
3. **Commit clean state**: Commit after cleanup (small, fast repo)
4. **Document source images**: Keep track of where original photos are stored
5. **Server backups**: Ensure idtdemo server content is backed up separately

## Status

- [x] Analysis complete
- [x] Cleanup plan documented
- [x] Safety script created
- [ ] User approval to proceed
- [ ] Execute cleanup
- [ ] Verify results
- [ ] Commit clean state
