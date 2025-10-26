# Source Control Guide for Image Gallery

## What Should Be in Source Control

### ✅ INCLUDE (Always commit these)

#### Core Template Files
- `index.html` - Root template (clean version from 6de91fb)
- `template/` - Complete empty template structure
  - `template/index.html`
  - `template/images/.gitkeep`
  - `template/jsondata/.gitkeep`
  - `template/README.md`

#### Documentation
- `*.md` files (all documentation)
  - `ARCHITECTURE.md`
  - `ARIA_EVALUATION_OCT24.md`
  - `TEMPLATE_CHECKLIST.md`
  - `DEPLOYMENT_READY_OCT25.md`
  - `REPLICATION_GUIDE.md`
  - `SETUP_GUIDE.md`
  - `README.md`
  - etc.

#### Python Scripts
- `generate_descriptions.py` - Converts workflow outputs to JSON
- `generate_alt_text.py` - Adds alt_text fields
- `export_analysis_data.py` - Exports analysis data
- Any other `.py` files

#### Configuration
- `.gitignore` - Excludes large files

#### Archive
- `archive/` - Historical documentation

### ❌ EXCLUDE (Never commit these)

#### Large Binary Files
- `images/` - Image files (~65-83MB per gallery)
- `*/images/` - Images in any subdirectory
- `cottage/`, `europe/`, `contentprototype/` - Entire gallery deployments

**Why**: Binary image files are large and deployment-specific. They should be:
- Stored on the deployment server
- Backed up separately
- Not in git (bloats repository)

#### Workflow Outputs
- `descriptions/` - Workflow directories (~130MB-3.6GB)
- `*/descriptions/` - In any subdirectory

**Why**: These are temporary working files that can be regenerated. Contains:
- Logs
- Temporary files
- API responses
- Can be recreated by running workflows again

#### Deployment-Specific Data
- `jsondata/*.json` - JSON config files
- `gallery-data/*.json` - Gallery data files
- `data/` - Data directory

**Why**: These are generated from workflows and specific to each deployment. They:
- Can be regenerated with scripts
- Are deployment-specific
- Change frequently
- Are small but deployment-specific

#### Generated Files
- `*.csv` - CSV exports (can be regenerated)

### 🤔 OPTIONAL (Case by case)

#### Example Gallery (One Only)
You might want to keep ONE small example gallery for reference:
- Consider: A minimal example with 3-5 images (not 25)
- Include: Just the structure and a few files
- Purpose: Show working example
- Size: Keep under 5MB total

Currently NOT recommended - documentation is sufficient.

## Current .gitignore

The `.gitignore` file excludes:
```
images/          # All image directories
jsondata/*.json  # JSON configs
descriptions/    # Workflow outputs
gallery-data/    # Gallery data
data/            # Data directory
cottage/         # Gallery deployments
europe/
contentprototype/
*.csv            # Exports

# But keeps:
*.md             # Documentation
*.py             # Scripts
index.html       # Root template
template/        # Template structure
```

## File Sizes (Current)

```
cottage/         3.6GB  ❌ DO NOT COMMIT
europe/          259MB  ❌ DO NOT COMMIT
contentprototype/ 259MB ❌ DO NOT COMMIT
data/            11MB   ❌ DO NOT COMMIT
images/          83MB   ❌ DO NOT COMMIT
```

## Workflow

### When Creating a New Gallery:

1. **Copy template** (not tracked):
   ```bash
   cp -r template/ my-gallery/
   ```

2. **Work locally** (not tracked):
   - Add images to `my-gallery/images/`
   - Run workflows to `my-gallery/descriptions/`
   - Generate JSON to `my-gallery/jsondata/`

3. **Deploy** (not tracked):
   - Upload `my-gallery/` to server
   - Server stores the deployment

4. **Commit only** (tracked):
   - Updated scripts (if you improved them)
   - Updated documentation (if you learned something)
   - Updated root `index.html` (if you fixed bugs)

### When Improving the Template:

1. **Make changes** to root `index.html`
2. **Test thoroughly**
3. **Update template**:
   ```bash
   cp index.html template/index.html
   ```
4. **Document changes** in ARIA_EVALUATION or ARCHITECTURE
5. **Commit**:
   ```bash
   git add index.html template/index.html *.md
   git commit -m "Update gallery template: [description]"
   ```

## Backup Strategy

Since galleries are NOT in git:

### For Active Galleries:
- **Server**: Primary storage (live deployment)
- **Local**: Working copy during development
- **Backup**: Separate backup of server content

### For Gallery Source Images:
- Keep original source images in separate location
- Don't rely on gallery deployments as source
- Original photos should be in photo management system

### For Workflow Outputs:
- Can be regenerated from source images
- No need to backup descriptions/ folders
- Just keep track of which models/prompts were used

## Git Status Check

Before committing, verify sizes:
```bash
git status --short
git add -n .  # Dry run to see what would be added
```

If you see large files, check .gitignore!

## Emergency: Accidentally Committed Large Files

If you accidentally commit large files:

```bash
# Remove from staging (before push)
git reset HEAD cottage/

# Remove from history (after push - DANGEROUS)
git filter-branch --tree-filter 'rm -rf cottage/' HEAD
# Or use git-filter-repo (better tool)

# Add to .gitignore
echo "cottage/" >> .gitignore
```

## Summary

**Simple Rule**: 
- ✅ Commit: Documentation, scripts, root template
- ❌ Don't commit: Images, galleries, workflow outputs, JSON data

Keep the repository lean and fast. Gallery deployments live on servers, not in git.
