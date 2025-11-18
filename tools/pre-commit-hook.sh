#!/bin/bash
# Pre-commit hook: Run critical workflow tests before allowing commit
#
# Install: ln -s ../../tools/pre-commit-hook.sh .git/hooks/pre-commit
# Or: copy this to .git/hooks/pre-commit and chmod +x

echo "Running pre-commit checks..."

# 1. Check for suspicious workflow logic patterns
echo "Checking for suspicious patterns in workflow.py..."

# Pattern 1: is_workflow_dir should ONLY check input_dir == base_output_dir
if git diff --cached scripts/workflow.py | grep -E "is_workflow_dir.*\.exists\(\)" > /dev/null; then
    echo "❌ ERROR: is_workflow_dir should not check .exists() conditions"
    echo "   This can cause normal workflows to incorrectly trigger workflow mode"
    echo "   Only check: input_dir == base_output_dir"
    exit 1
fi

# Pattern 2: Ensure regular images are always processed (not just in else block)
if git diff --cached scripts/workflow.py | grep -A50 "describe_images" | grep -B5 "regular_input_images" | grep "else:" > /dev/null; then
    echo "⚠️  WARNING: Regular image processing appears to be in conditional block"
    echo "   Verify this is intentional and won't skip files in normal workflows"
fi

# 2. Run integration tests if workflow.py changed
if git diff --cached --name-only | grep -q "scripts/workflow.py"; then
    echo "workflow.py changed, running integration tests..."
    
    # Run only the fast integration tests
    if ! python -m pytest pytest_tests/integration/test_workflow_file_types.py -v --tb=short; then
        echo "❌ Integration tests failed - commit blocked"
        echo "Fix the failing tests before committing workflow.py changes"
        exit 1
    fi
    
    echo "✅ Integration tests passed"
fi

# 3. Check for common workflow bugs
echo "Checking for common workflow bugs..."

# Bug: Using .glob() instead of .rglob() for nested directories
if git diff --cached scripts/workflow.py | grep -E "\.glob\(['\"].*\.(jpg|png|jpeg)" > /dev/null; then
    echo "⚠️  WARNING: Found .glob() usage - verify it shouldn't be .rglob() for nested dirs"
fi

echo "✅ Pre-commit checks passed"
exit 0
