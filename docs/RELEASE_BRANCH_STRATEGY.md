# Release Branch Strategy

## Current Setup

As of October 22, 2025, we use **release branches + tags** for version management.

### Branch Structure

```
main                    - Active development (latest features)
release/v3.0           - v3.0.x maintenance (frozen at v3.0.0 tag)
1.0release             - Legacy v1.0 branch (archived)
```

### Tags

- `v3.0.0` - Points to the v3.0 release commit (also where `release/v3.0` branch starts)
- `v1.1.0-cli` - Legacy CLI release
- `v1.0.0` - Legacy initial release

## Why Use Release Branches?

**Release branches provide:**
- ✅ Permanent snapshot that can't be accidentally deleted
- ✅ Protection from force-push accidents
- ✅ Clear place to apply hotfixes
- ✅ Easy cherry-picking of fixes between versions

**Tags alone are not sufficient because:**
- ⚠️ Can be deleted: `git push --delete origin v3.0.0`
- ⚠️ Can be moved: `git tag -f v3.0.0 <new-commit>`
- ⚠️ No built-in protection on most Git hosts

## Workflow

### Normal Development (main branch)

```bash
# Work on main for new features
git checkout main
git pull origin main

# Make changes, commit, push
git add .
git commit -m "Add new feature"
git push origin main
```

### Creating a New Release

```bash
# 1. Create release branch from main
git checkout main
git checkout -b release/v3.1
git push origin release/v3.1

# 2. Tag the release
git tag -a v3.1.0 -m "Release v3.1.0"
git push origin v3.1.0

# 3. Continue development on main
git checkout main
```

### Applying a Hotfix to v3.0

```bash
# 1. Create hotfix branch from release branch
git checkout release/v3.0
git checkout -b hotfix/v3.0.1-critical-fix

# 2. Make the fix
# ... edit files ...
git add .
git commit -m "Fix critical bug in stats_analysis.py"

# 3. Merge to release branch and tag
git checkout release/v3.0
git merge hotfix/v3.0.1-critical-fix
git tag -a v3.0.1 -m "Hotfix: Critical bug in stats analysis"
git push origin release/v3.0
git push origin v3.0.1

# 4. Also merge to main if applicable
git checkout main
git merge hotfix/v3.0.1-critical-fix
git push origin main

# 5. Clean up hotfix branch
git branch -d hotfix/v3.0.1-critical-fix
```

### When to Use release/v3.0

**Use the release branch for:**
- Critical bug fixes that affect v3.0 users
- Security patches
- Documentation corrections specific to v3.0
- Compatibility fixes

**Do NOT use for:**
- New features (those go in main for v3.1+)
- Breaking changes
- Major refactors
- Performance improvements (unless critical)

## GitHub Branch Protection (Recommended)

Consider protecting the release branches on GitHub:

1. Go to Settings → Branches → Add rule
2. Branch name pattern: `release/*`
3. Enable:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass
   - ✅ Include administrators
   - ✅ Restrict who can push to matching branches

This prevents accidental force-pushes or direct commits to release branches.

## Example Timeline

```
v1.0.0 (tag) ←─ 1.0release (branch)
  │
  ├─→ (archived, no longer maintained)

v3.0.0 (tag) ←─ release/v3.0 (branch)
  │              │
  │              ├─→ v3.0.1 (hotfix tag)
  │              └─→ v3.0.2 (hotfix tag)
  │
  └─→ main (branch)
      ├─→ New features for v3.1
      ├─→ Breaking changes for v4.0
      └─→ Ongoing development
```

## Current State (Oct 22, 2025)

- **main branch:** Contains performance analysis document (after v3.0.0 release)
- **release/v3.0 branch:** Frozen at v3.0.0 tag commit
- **v3.0.0 tag:** Points to analysis script fixes

### Commits after v3.0.0 tag

```
main HEAD:       c23bd21 - Add workflow performance analysis
                 be33bd0 - Update VERSION to 3.0.0
release/v3.0:    4d9ca4e - (v3.0.0 tag) Fix analysis scripts
```

## FAQ

**Q: Should I delete the v3.0.0 tag after creating release/v3.0?**  
A: No, keep both! The tag marks the exact release point, the branch allows for maintenance.

**Q: What if I need to support multiple major versions?**  
A: Create separate release branches:
- `release/v3.0` - v3.0.x hotfixes
- `release/v4.0` - v4.0.x hotfixes (when v4 is released)
- `main` - v5.0 development

**Q: Can I just use tags without release branches?**  
A: Not recommended. Tags can be accidentally deleted or moved. Branches provide better protection.

**Q: What about the VERSION file?**  
A: Update it on the release branch when creating hotfix tags:
- `release/v3.0` VERSION file: `3.0.0` → `3.0.1` → `3.0.2`
- `main` VERSION file: `3.1.0-dev` or `4.0.0-dev`

---

**Reference:** GitHub Flow with Release Branches  
**Strategy:** Trunk-based development with protected release maintenance branches
