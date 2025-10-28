# Issue: Implement Automated Testing and CI/CD Pipeline

**Created:** 2025-10-28  
**Priority:** High  
**Status:** Planning  

## Problem Statement

Currently, bugs (format string errors, race conditions, frozen mode path issues) are only discovered during manual testing. This wastes time and delays releases. We need automated testing that catches issues before deployment.

## Current State

### What Exists ✅
- Basic test framework (`pytest_tests/`, `run_tests.py`)
- 4 test files (sanitization, status_log, workflow_config, metadata_safety)
- Build automation (`BuildAndRelease/build_idt.bat`)
- Local build-test-deploy script (`build-test-deploy.bat`)

### What's Broken ❌
- Pytest has configuration issues (buffer detachment errors)
- Tests don't run successfully in current setup
- No CI/CD automation on GitHub
- No automated validation after builds

### What's Missing ❌
- Integration tests with actual Ollama models
- Geocoding feature tests with real GPS data
- Frozen vs development mode tests
- GitHub Actions workflows
- Self-hosted runner configuration

## Recent Bugs That Should Have Been Caught by Tests

1. **Format String Injection** (Oct 27-28, 2025)
   - User EXIF data with `{}` characters caused KeyError
   - Would have been caught by: `test_metadata_safety.py` tests

2. **Config File Race Condition** (Oct 28, 2025)
   - Config write not flushed before ImageDescriber read it
   - Would have been caught by: `test_workflow_config.py` tests

3. **Frozen Mode Path Resolution** (Oct 28, 2025)
   - Using `__file__` instead of `sys.executable` in frozen builds
   - Would have been caught by: frozen mode path tests

## Proposed Solution

### Phase 1: Fix Current Tests (Immediate)
**Goal:** Get existing tests running without errors

**Tasks:**
- [ ] Fix pytest configuration (disable problematic plugins)
- [ ] Verify all 4 test files run successfully
- [ ] Add `pytest-mock` for better mocking support
- [ ] Document how to run tests locally
- [ ] Update `run_tests.py` to handle venv properly

**Success Criteria:**
- `pytest pytest_tests -v` completes without errors
- All tests pass or have clear skip reasons
- Documentation shows how to run tests

### Phase 2: Basic GitHub Actions (Quick Win)
**Goal:** Catch obvious errors on every commit

**What Can Run in GitHub Cloud:**
- ✅ Syntax checking (pyflakes, flake8)
- ✅ Import validation (all modules import successfully)
- ✅ Unit tests that don't need Ollama/models
- ✅ Format string safety tests
- ✅ Config file I/O tests
- ✅ Path resolution tests (mocked)
- ✅ Build verification (PyInstaller runs successfully)

**What CANNOT Run in GitHub Cloud:**
- ❌ Actual AI model inference (no Ollama)
- ❌ GPU-dependent operations
- ❌ Full workflow integration tests
- ❌ Real image description generation

**Tasks:**
- [ ] Create `.github/workflows/unit-tests.yml`
- [ ] Create `.github/workflows/build-check.yml`
- [ ] Add status badges to README
- [ ] Configure Python version matrix (3.11, 3.12, 3.13)
- [ ] Set up Windows runner (since app is Windows-specific)

**Workflow Example:**
```yaml
name: Unit Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-mock
      - run: pytest pytest_tests/unit -v --tb=short
```

### Phase 3: Self-Hosted Runner (Full Integration)
**Goal:** Run complete tests with real Ollama models

**Why Self-Hosted:**
- Your machine already has Ollama + models
- Has test images with GPS EXIF data
- Can test actual AI inference
- Can validate geocoding with real API calls
- Can test frozen executables

**Setup Requirements:**
1. Install GitHub Actions runner on your development machine
2. Configure as Windows runner
3. Label runner: `self-hosted, Windows, ollama-enabled`
4. Ensure Ollama service starts automatically

**Tasks:**
- [ ] Download GitHub Actions runner for Windows
- [ ] Install runner as Windows service
- [ ] Configure runner authentication (token-based)
- [ ] Create test image dataset with GPS EXIF
- [ ] Create `.github/workflows/integration-tests.yml`
- [ ] Add workflow that targets self-hosted runner
- [ ] Test full build → deploy → validate cycle

**Integration Test Workflow:**
```yaml
name: Integration Tests
on: 
  push:
    branches: [main]
jobs:
  full-test:
    runs-on: [self-hosted, windows, ollama-enabled]
    steps:
      - uses: actions/checkout@v4
      - name: Run full test suite
        run: |
          .venv\Scripts\activate
          pytest pytest_tests -v --tb=short
      - name: Build executable
        run: BuildAndRelease\build_idt.bat
      - name: Deploy and validate
        run: BuildAndRelease\build-test-deploy.bat c:\idt2 c:\idt2\testimages
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: c:\idt2\Descriptions\wf_ValidationRun*
```

### Phase 4: Advanced Automation (Future)
**Goal:** Complete DevOps pipeline

**Tasks:**
- [ ] Automated release creation (tag → build → GitHub release)
- [ ] Automated installer packaging
- [ ] Performance benchmarks (track description generation speed)
- [ ] Coverage reports (codecov.io integration)
- [ ] Nightly builds with all models
- [ ] Automated documentation updates
- [ ] Dependency vulnerability scanning (Dependabot)

## Testing Strategy

### Unit Tests (Fast, No Dependencies)
**Run on:** Every commit (GitHub cloud)
**Coverage:**
- Format string safety
- Path resolution (frozen vs dev)
- Config file I/O
- Metadata extraction (mocked EXIF)
- Sanitization functions
- Utility functions

### Integration Tests (Slow, Needs Ollama)
**Run on:** Main branch commits, PRs (self-hosted)
**Coverage:**
- Real AI model inference
- Geocoding with live API
- Full workflow execution
- Frozen executable validation
- UNC path handling
- HEIC conversion

### Regression Tests (Specific Bug Fixes)
**Run on:** Every commit
**Coverage:**
- Known bugs (format strings, race conditions, etc.)
- Mark with `@pytest.mark.regression`
- Should never fail once fixed

## Decision Points

### 1. Self-Hosted Runner Location
**Options:**
- A) Your current development machine (Surface Pro)
- B) Dedicated test machine/VM
- C) Both (dev machine for quick tests, dedicated for official releases)

**Considerations:**
- Power/uptime requirements
- Network stability
- Ollama GPU usage during tests
- Security (runner has repo access)

### 2. Test Coverage Goals
**Options:**
- A) Basic (syntax, imports, critical bugs) - ~40% coverage
- B) Moderate (+ unit tests, config, metadata) - ~60% coverage
- C) Comprehensive (+ integration, E2E) - ~80% coverage

**Recommendation:** Start with A, grow to B over time

### 3. When to Block Merges
**Options:**
- A) Only block on syntax/import errors
- B) Block on unit test failures
- C) Block on integration test failures
- D) All of the above

**Recommendation:** B for now (unit tests must pass), C eventually

### 4. Testing Philosophy
**Mock Everything vs Test Reality:**
- **Mock approach:** Fast, portable, tests logic only
- **Reality approach:** Slow, requires setup, tests actual behavior
- **Hybrid approach:** Mock for unit tests, real for integration

**Recommendation:** Hybrid (what I've started building)

## Resource Requirements

### Time Investment
- Phase 1: 2-4 hours (fix existing tests)
- Phase 2: 1-2 hours (basic GitHub Actions)
- Phase 3: 3-5 hours (self-hosted runner setup)
- Phase 4: Ongoing (continuous improvement)

### Infrastructure
- GitHub Actions minutes: Free for public repos, minimal for private
- Self-hosted runner: Your existing machine (no cost)
- Test data storage: ~100MB for test images

### Maintenance
- Test updates: 10-30 min per feature addition
- Runner maintenance: Check monthly, update quarterly
- Dependency updates: Automated with Dependabot

## Benefits

### Immediate (Phase 1-2)
- Catch syntax errors before manual testing
- Validate imports and dependencies
- Prevent format string regressions
- Faster feedback on PRs

### Medium Term (Phase 3)
- Automated validation of builds
- Catch integration issues early
- Confidence in releases
- Less manual testing burden

### Long Term (Phase 4)
- Full DevOps automation
- One-click releases
- Performance tracking
- Community contributions easier to validate

## Risks and Mitigations

### Risk: Self-Hosted Runner Security
**Mitigation:** 
- Only run on trusted branches
- Don't expose secrets in logs
- Regular runner updates
- Consider isolated VM for runner

### Risk: Test Flakiness
**Mitigation:**
- Proper waits/retries for timing issues
- Isolate tests from each other
- Clean state between tests
- Mock external dependencies where possible

### Risk: Slow Test Suite
**Mitigation:**
- Parallel test execution
- Skip slow tests for quick feedback
- Cache dependencies and models
- Incremental testing (only affected code)

### Risk: Maintenance Overhead
**Mitigation:**
- Start small, grow gradually
- Automate test data generation
- Good test naming/organization
- Document test requirements

## Next Steps

1. **Decision Required:** Choose which phases to implement
2. **Decision Required:** Self-hosted runner location/timing
3. **Action:** Fix pytest configuration issues
4. **Action:** Get existing tests passing
5. **Action:** Create GitHub Actions workflow (Phase 2)
6. **Action:** Evaluate self-hosted runner setup (Phase 3)

## Related Issues/PRs
- Format string bug fixes (Oct 27-28, 2025)
- Geocoding race condition fix (Oct 28, 2025)
- Frozen mode path resolution (Oct 28, 2025)

## References
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Self-Hosted Runners Guide](https://docs.github.com/en/actions/hosting-your-own-runners)
- [pytest Documentation](https://docs.pytest.org/)
- Current test files: `pytest_tests/unit/`
- Build scripts: `BuildAndRelease/`

---

**Discussion:** Add comments below with thoughts on:
- Which phase(s) to prioritize?
- Self-hosted runner feasibility?
- Test coverage goals?
- Any concerns or questions?
