# AI-Assisted Quality Assurance Strategy
**Date**: 2026-01-20  
**Context**: 100% AI-generated codebase with 23% fix rate in WXMigration branch  
**Problem**: Reactive testing loop is time-expensive; need proactive issue detection

## The Core Problem

**Current State**:
1. User tests manually → finds bug
2. AI fixes bug → user tests again
3. Repeat until something else breaks
4. **Cost**: User time + uncertainty about what else is broken

**Root Cause**: AI lacks the full test suite that would catch issues before deployment

---

## Proposed Solution: 4-Tier AI-Assisted QA

### Tier 1: Automated Regression Test Suite (HIGHEST PRIORITY)

Create pytest tests that encode the bugs we've found, so they can NEVER happen again:

```python
# pytest_tests/test_regression_suite.py
"""
Tests based on actual bugs found in WXMigration branch.
Each test represents a production failure.
"""

def test_workflow_variable_consistency():
    """Regression: unique_images vs unique_source_count mismatch"""
    # Use AST to verify all return statements reference defined variables
    import ast
    from pathlib import Path
    
    workflow_path = Path("scripts/workflow.py")
    tree = ast.parse(workflow_path.read_text())
    
    # Extract all function definitions and verify return statements
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check that all variables in return statements are defined
            pass  # Implementation details

def test_import_patterns_frozen_compatible():
    """Regression: 'from scripts.X' breaks in PyInstaller"""
    # Grep for forbidden import patterns
    import subprocess
    
    result = subprocess.run(
        ["grep", "-r", "from scripts\\.", "scripts/", "analysis/", "imagedescriber/"],
        capture_output=True
    )
    
    forbidden_imports = result.stdout.decode()
    assert forbidden_imports == "", f"Found forbidden imports:\n{forbidden_imports}"

def test_function_signature_consistency():
    """Regression: combinedescriptions function signature changed but callers not updated"""
    # Use list_code_usages equivalent to find all callers
    # Verify argument counts match
    pass

def test_viewer_keyboard_navigation():
    """Regression: Listbox not in sizer, EVT_LISTBOX not bound"""
    # Parse viewer_wx.py AST to verify:
    # 1. desc_list added to sizer
    # 2. EVT_LISTBOX bound to handler
    pass
```

**AI Action**: I can create this test suite NOW, encoding all 4 bugs we found today.

---

### Tier 2: Comparison Testing Framework

**Concept**: Run identical commands on main branch vs WXMigration, diff the results

```python
# tools/comparison_test.py
"""
Runs the same command on two branches and compares:
- Exit codes
- Stdout/stderr
- Generated files
- Log contents
"""

import subprocess
import json
from pathlib import Path

def run_on_branch(branch, command, test_dir):
    """Checkout branch, run command, capture all outputs"""
    subprocess.run(["git", "checkout", branch])
    
    # Build exe
    subprocess.run(["cd", "idt", "&&", "build_idt.bat"], shell=True)
    
    # Run command
    result = subprocess.run(
        ["dist/idt.exe"] + command.split(),
        capture_output=True,
        cwd=test_dir
    )
    
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout.decode(),
        "stderr": result.stderr.decode(),
        "files": list(Path(test_dir).glob("**/*")),
        "logs": list(Path(test_dir).glob("**/logs/*.log"))
    }

def compare_branches(command, test_dir):
    main_result = run_on_branch("main", command, test_dir)
    wx_result = run_on_branch("WXMigration", command, test_dir)
    
    # Deep comparison
    differences = {}
    
    if main_result["exit_code"] != wx_result["exit_code"]:
        differences["exit_code"] = {
            "main": main_result["exit_code"],
            "wx": wx_result["exit_code"]
        }
    
    # Compare file counts, descriptions generated, etc.
    # Flag any discrepancies
    
    return differences

# Run suite
test_cases = [
    ("workflow testimages", "test_workflow_1"),
    ("combinedescriptions --input-dir wf_test", "test_combine_1"),
    ("stats wf_test", "test_stats_1")
]

for command, test_dir in test_cases:
    diffs = compare_branches(command, test_dir)
    if diffs:
        print(f"REGRESSION DETECTED in '{command}':")
        print(json.dumps(diffs, indent=2))
```

**AI Action**: I can implement this and run it TONIGHT to find ALL behavioral differences between branches.

---

### Tier 3: Static Analysis Checks (Pre-Commit)

**Concept**: Before ANY code is committed, run automated checks

```python
# tools/pre_commit_checks.py
"""
Runs before git commit to catch issues AI agents introduce.
"""

import subprocess
import sys
from pathlib import Path
import ast

def check_forbidden_imports():
    """Flag 'from scripts.X' patterns"""
    result = subprocess.run(
        ["grep", "-rn", "from scripts\\.", "scripts/", "analysis/", "imagedescriber/"],
        capture_output=True
    )
    
    if result.returncode == 0:
        print("❌ FORBIDDEN IMPORT PATTERNS FOUND:")
        print(result.stdout.decode())
        return False
    return True

def check_undefined_variables():
    """Use AST to find variables referenced but not defined"""
    errors = []
    
    for py_file in Path("scripts").glob("**/*.py"):
        tree = ast.parse(py_file.read_text())
        
        # For each function, track defined vs referenced variables
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            defined = set()
            referenced = set()
            
            # Walk function body
            for node in ast.walk(func):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        defined.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        referenced.add(node.id)
            
            undefined = referenced - defined - set(dir(__builtins__))
            if undefined:
                errors.append(f"{py_file}:{func.name} - undefined: {undefined}")
    
    if errors:
        print("❌ UNDEFINED VARIABLES:")
        for e in errors:
            print(f"  {e}")
        return False
    return True

def check_all_callers_updated():
    """When function signatures change, verify all callers updated"""
    # Git diff to find changed function signatures
    # Use grep to find all call sites
    # Verify argument counts match
    pass

def main():
    checks = [
        ("Forbidden imports", check_forbidden_imports),
        ("Undefined variables", check_undefined_variables),
        ("Caller consistency", check_all_callers_updated)
    ]
    
    failures = []
    for name, check_func in checks:
        print(f"Running {name}...")
        if not check_func():
            failures.append(name)
    
    if failures:
        print(f"\n❌ PRE-COMMIT CHECKS FAILED: {', '.join(failures)}")
        sys.exit(1)
    
    print("✅ All pre-commit checks passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Setup as git hook**:
```bash
# .git/hooks/pre-commit
#!/bin/bash
python tools/pre_commit_checks.py
```

**AI Action**: I can create this and install the git hook NOW.

---

### Tier 4: End-to-End Integration Tests

**Concept**: Full workflow tests with known-good data

```python
# pytest_tests/test_integration.py
"""
Full workflow tests using test data with known outputs.
"""

import subprocess
from pathlib import Path
import json

class TestWorkflowIntegration:
    
    def test_full_workflow_with_videos(self, tmp_path):
        """Test complete workflow: video → frames → convert → describe → HTML"""
        
        # Copy test videos to tmp_path
        test_videos = Path("test_data/videos")
        
        # Run workflow
        result = subprocess.run(
            ["dist/idt.exe", "workflow", str(tmp_path), "--model", "gpt-4o-mini"],
            capture_output=True
        )
        
        # Assertions
        assert result.returncode == 0, f"Workflow failed: {result.stderr}"
        
        # Check outputs
        workflow_dirs = list(tmp_path.glob("wf_*"))
        assert len(workflow_dirs) == 1, "Should create exactly 1 workflow directory"
        
        wf_dir = workflow_dirs[0]
        
        # Verify structure
        assert (wf_dir / "images").exists()
        assert (wf_dir / "descriptions").exists()
        assert (wf_dir / "HTML_Output").exists()
        assert (wf_dir / "workflow_metadata.json").exists()
        
        # Verify metadata
        metadata = json.loads((wf_dir / "workflow_metadata.json").read_text())
        assert metadata["model"] == "gpt-4o-mini"
        assert "timestamp" in metadata
        
        # Verify logs
        logs = list((wf_dir / "logs").glob("*.log"))
        assert len(logs) > 0
        
        # Check for errors in logs
        for log in logs:
            content = log.read_text()
            assert "ERROR" not in content, f"Errors found in {log.name}"
    
    def test_combinedescriptions_output_format(self, tmp_path):
        """Verify combinedescriptions CSV has correct columns and data"""
        # Run combinedescriptions
        # Verify CSV has: Image Name, Date/Time, Description, Source Workflow
        pass
    
    def test_viewer_loads_workflow(self):
        """Test viewer can load and display workflow results"""
        # Launch viewer with test workflow
        # Verify listbox populated, images load, keyboard nav works
        pass
```

**AI Action**: I can implement this using your existing testimages/ directory.

---

## Recommended Phased Implementation

### Phase 1: Foundation (Week 1) - RECOMMENDED START
1. **Create regression test suite** based on 4 bugs found today
2. **Run comparison testing** (main vs WXMigration) to find ALL differences
3. **Document findings** in comprehensive report

**AI Can Do This Autonomously** - Just say "Go ahead with Phase 1"

### Phase 2: Prevention (Week 2)
1. Install pre-commit hooks for static analysis
2. Create CI/CD pipeline (GitHub Actions) to run tests on every commit
3. Establish "definition of done" checklist for AI

### Phase 3: Validation (Week 3)
1. Build end-to-end integration tests
2. Create test data repository with known-good outputs
3. Automate nightly regression runs

### Phase 4: Maintenance (Ongoing)
1. Every bug found → add test to regression suite
2. Every feature added → add integration test
3. Monthly comparison runs (main vs branches)

---

## What AI Can Do Autonomously vs. Needs User Input

### ✅ AI CAN DO AUTONOMOUSLY:
- Write regression tests encoding known bugs
- Run comparison tests between branches
- Create static analysis tools (AST, grep patterns)
- Build pre-commit hooks
- Generate test data for integration tests
- Run automated test suites and report failures
- Scan codebase for patterns (undefined variables, forbidden imports)

### ⚠️ NEEDS USER INPUT:
- Defining "correct behavior" for new features (what SHOULD happen?)
- Prioritizing which tests to run (time/cost trade-offs)
- Deciding when to merge (risk tolerance)
- Approving automated fixes (trust level)
- Providing edge cases (unusual user workflows)

---

## Immediate Action Plan (Can Start Tonight)

**Option A: Full Audit (Recommended)**
```
AI Agent Actions:
1. Create regression test suite (4 tests for known bugs) - 30 min
2. Implement comparison testing framework - 1 hour
3. Run comparison tests (main vs WXMigration) - 2 hours
4. Generate comprehensive report of ALL differences - 30 min

Total: ~4 hours of AI work
User Time: Review report next morning, decide on fixes
```

**Option B: Targeted Testing**
```
AI Agent Actions:
1. Create regression tests only - 30 min
2. Run pytest suite - 5 min
3. Fix only confirmed regressions - 1-2 hours

Total: ~2 hours of AI work
User Time: Approve fixes, rebuild production exe
```

**Option C: Static Analysis Only**
```
AI Agent Actions:
1. Create AST analyzer for undefined variables - 1 hour
2. Create grep scanner for forbidden imports - 30 min
3. Scan entire codebase, generate report - 30 min

Total: ~2 hours of AI work
User Time: Review report, prioritize fixes
```

---

## Cost-Benefit Analysis

**Current Approach** (Manual Testing):
- User Time: 1-2 hours per bug found
- AI Time: 30 min per fix
- Coverage: Reactive (only tests user thinks to run)
- **Risk**: Unknown bugs lurking

**Proposed Approach** (Automated Testing):
- **Upfront Cost**: 4-8 hours AI work to build test suite
- **Ongoing Cost**: 5 min per commit (automated)
- Coverage: Comprehensive (all critical paths)
- **Benefit**: Catches bugs before user sees them

**Break-Even Point**: After ~4-6 bugs caught by automated tests

---

## My Recommendation

**Start with Option A (Full Audit)** because:

1. **You have a working baseline** (main branch) - we can diff against it
2. **You have known bugs** (4 so far) - we can test for them
3. **AI can work autonomously** - you sleep, AI tests everything
4. **One-time investment** - then ongoing protection

**Specific Request to Get Started**:
> "Go ahead with Phase 1 Option A: Create regression test suite, run comparison testing between main and WXMigration branches, and generate a comprehensive report of all differences. I'll review it in the morning."

This shifts you from **reactive debugging** to **proactive quality assurance** with minimal additional user time investment.

Would you like me to proceed with any of these options?
