"""
Regression Test Suite for IDT CLI
==================================
Each test represents a real production bug found in the WXMigration branch.
These tests must ALWAYS pass to prevent regressions.

Date Created: 2026-01-20
Context: Migration from PyQt6 to wxPython introduced multiple regressions
Fix Rate: 23% of commits were fixes (17 of 74)

References:
- docs/worktracking/2026-01-20-MIGRATION-AUDIT.md
- docs/worktracking/AI_COMPREHENSIVE_REVIEW_PROTOCOL.md
"""

import ast
import subprocess
from pathlib import Path
import re
import pytest


class TestWorkflowVariableConsistency:
    """
    Regression: unique_images vs unique_source_count mismatch
    
    Bug: Variable defined as `unique_images` but returned as `unique_source_count`
    Impact: NameError crash after 57 minutes of processing
    Commit: 03cd2b3 (introduced bug), 400bb3c (fixed)
    File: scripts/workflow.py
    """
    
    def test_workflow_return_statements_use_defined_variables(self):
        """Verify all return statement variables are defined in scope"""
        workflow_path = Path("scripts/workflow.py")
        content = workflow_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        errors = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Track variables defined in this function
                defined_vars = set()
                return_vars = set()
                
                for child in ast.walk(node):
                    # Find assignments (variable definitions)
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                defined_vars.add(target.id)
                    
                    # Find return statements
                    if isinstance(child, ast.Return) and child.value:
                        # Extract variable names from return value
                        for name_node in ast.walk(child.value):
                            if isinstance(name_node, ast.Name):
                                return_vars.add(name_node.id)
                
                # Check for undefined variables in return statements
                # (excluding built-ins, function parameters, and common imports)
                builtins = set(dir(__builtins__))
                undefined = return_vars - defined_vars - builtins - {'self', 'True', 'False', 'None'}
                
                if undefined:
                    errors.append(
                        f"Function '{node.name}' at line {node.lineno}: "
                        f"returns undefined variable(s): {', '.join(sorted(undefined))}"
                    )
        
        assert not errors, "\n".join(errors)
    
    def test_specific_unique_images_variable(self):
        """Specifically check for the unique_images/unique_source_count bug"""
        workflow_path = Path("scripts/workflow.py")
        content = workflow_path.read_text(encoding='utf-8')
        
        # Check that unique_images is used consistently (not unique_source_count)
        # This was the actual bug: defined as unique_images, returned as unique_source_count
        
        # Find all references
        unique_images_refs = len(re.findall(r'\bunique_images\b', content))
        unique_source_count_refs = len(re.findall(r'\bunique_source_count\b', content))
        
        # Should have multiple references to unique_images (definition + uses)
        assert unique_images_refs > 0, "unique_images variable should be defined and used"
        
        # Should have NO references to unique_source_count (the bug)
        assert unique_source_count_refs == 0, (
            f"Found {unique_source_count_refs} references to 'unique_source_count' - "
            "this was the buggy variable name that caused NameError"
        )


class TestImportPatternsPyInstallerCompatibility:
    """
    Regression: 'from scripts.X' breaks in PyInstaller frozen executables
    
    Bug: Imports like 'from scripts.module import X' work in dev but fail in frozen exe
    Impact: ModuleNotFoundError in production executables
    Reason: PyInstaller flattens directory structure, 'scripts' package doesn't exist in _MEIPASS
    Solution: Use module-level imports with try/except fallback
    """
    
    def test_no_forbidden_scripts_imports(self):
        """Check for 'from scripts.X' import patterns"""
        forbidden_patterns = [
            r'from\s+scripts\.',
            r'from\s+imagedescriber\.',
            r'from\s+analysis\.',
        ]
        
        # Check these directories
        dirs_to_check = ['scripts', 'analysis', 'idt']
        
        errors = []
        
        for directory in dirs_to_check:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
                
            for py_file in dir_path.glob("**/*.py"):
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in forbidden_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        errors.append(
                            f"{py_file}:{line_num} - Forbidden import pattern: {match.group()}"
                        )
        
        assert not errors, (
            "Found forbidden import patterns that will break in PyInstaller:\n" +
            "\n".join(errors) +
            "\n\nUse module-level imports with try/except instead:\n"
            "  try:\n"
            "      from module_name import X\n"
            "  except ImportError:\n"
            "      from scripts.module_name import X\n"
        )
    
    def test_required_files_have_fallback_imports(self):
        """Verify critical files use try/except import pattern"""
        critical_files = [
            'scripts/workflow.py',
            'scripts/image_describer.py',
            'idt/idt_cli.py',
        ]
        
        for file_path in critical_files:
            path = Path(file_path)
            if not path.exists():
                continue
                
            content = path.read_text(encoding='utf-8')
            
            # Look for try/except import patterns (basic check)
            has_try_except_import = bool(re.search(r'try:\s*\n\s*from\s+.*import.*\n\s*except ImportError:', content))
            
            # This is a soft check - not all files need it, but workflow.py definitely does
            if 'workflow.py' in str(path):
                assert has_try_except_import, (
                    f"{file_path} should use try/except import pattern for PyInstaller compatibility"
                )


class TestFunctionSignatureConsistency:
    """
    Regression: combinedescriptions function signature changed but callers not updated
    
    Bug: get_image_date_for_sorting() moved from local (2 args) to shared.exif_utils (1 arg)
          but callers still passing 2 arguments
    Impact: TypeError: get_image_date_for_sorting() takes 1 positional argument but 2 were given
    File: analysis/combine_workflow_descriptions.py
    Fix: Created wrapper function to bridge signature difference
    """
    
    def test_combine_workflow_has_wrapper_function(self):
        """Verify wrapper function exists to handle signature mismatch"""
        combine_path = Path("analysis/combine_workflow_descriptions.py")
        content = combine_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        # Find the get_image_date_for_sorting function definition
        wrapper_found = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'get_image_date_for_sorting':
                wrapper_found = True
                
                # Check it has the right number of parameters (2: image_name, base_dir)
                # The wrapper should accept 2 args, then call shared version with 1 arg
                params = [arg.arg for arg in node.args.args]
                assert len(params) == 2, (
                    f"Wrapper function should take 2 parameters, got {len(params)}: {params}"
                )
                break
        
        assert wrapper_found, (
            "analysis/combine_workflow_descriptions.py should have wrapper function "
            "get_image_date_for_sorting() to bridge signature difference with shared.exif_utils"
        )
    
    def test_shared_exif_utils_has_single_arg_version(self):
        """Verify shared version takes 1 argument (image_path)"""
        shared_path = Path("shared/exif_utils.py")
        if not shared_path.exists():
            pytest.skip("shared/exif_utils.py not found")
            
        content = shared_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'get_image_date_for_sorting':
                params = [arg.arg for arg in node.args.args]
                assert len(params) == 1, (
                    f"Shared version should take 1 parameter (image_path), got {len(params)}: {params}"
                )
                break


class TestCodeCompleteness:
    """
    General regression checks for incomplete code changes
    
    These tests catch the pattern of AI agents making partial changes:
    - Renaming variables in definitions but not in usages
    - Changing function signatures but not updating callers
    - Adding features but not updating all related code
    """
    
    def test_no_undefined_variables_in_workflow(self):
        """Scan workflow.py for common undefined variable patterns"""
        workflow_path = Path("scripts/workflow.py")
        content = workflow_path.read_text(encoding='utf-8')
        
        # Common bug patterns from our experience
        suspicious_patterns = [
            (r'return.*unique_source_count', 'unique_source_count in return statement'),
            (r'print.*unique_source_count', 'unique_source_count in print statement'),
        ]
        
        errors = []
        for pattern, description in suspicious_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Verify it's actually defined
                if 'unique_source_count' in match.group() and 'unique_source_count =' not in content:
                    line_num = content[:match.start()].count('\n') + 1
                    errors.append(f"Line {line_num}: {description} but variable not defined")
        
        assert not errors, "\n".join(errors)
    
    def test_workflow_syntax_valid(self):
        """Ensure workflow.py is syntactically valid Python"""
        workflow_path = Path("scripts/workflow.py")
        content = workflow_path.read_text(encoding='utf-8')
        
        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"workflow.py has syntax error: {e}")
    
    def test_image_describer_syntax_valid(self):
        """Ensure image_describer.py is syntactically valid Python"""
        describer_path = Path("scripts/image_describer.py")
        content = describer_path.read_text(encoding='utf-8')
        
        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"image_describer.py has syntax error: {e}")
    
    def test_combine_descriptions_syntax_valid(self):
        """Ensure combine_workflow_descriptions.py is syntactically valid Python"""
        combine_path = Path("analysis/combine_workflow_descriptions.py")
        content = combine_path.read_text(encoding='utf-8')
        
        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"combine_workflow_descriptions.py has syntax error: {e}")


class TestBuildConfiguration:
    """
    Regression checks for build configuration issues
    
    Ensures PyInstaller spec files are properly configured and
    build scripts are consistent
    """
    
    def test_idt_spec_file_exists(self):
        """Verify idt.spec exists for PyInstaller builds"""
        spec_path = Path("idt/idt.spec")
        assert spec_path.exists(), "idt/idt.spec must exist for building frozen executable"
    
    def test_build_script_uses_correct_venv(self):
        """Verify build script references .winenv (not winenv)"""
        build_script = Path("idt/build_idt.bat")
        if not build_script.exists():
            pytest.skip("build_idt.bat not found")
            
        content = build_script.read_text(encoding='utf-8')
        
        # Should reference .winenv (with dot)
        assert '.winenv' in content or '.venv' in content, (
            "build_idt.bat should reference .winenv or .venv directory"
        )
        
        # Should NOT reference winenv (without dot) - this was a bug
        assert 'call winenv\\' not in content, (
            "build_idt.bat should NOT reference 'winenv' - use '.winenv' instead"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
