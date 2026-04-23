#!/usr/bin/env python3
"""
Viewer App Comprehensive Analysis Tool

Analyzes the viewer wxPython application for:
- Code quality issues
- PyInstaller compatibility
- Import patterns
- Function signatures
- Error handling
- Accessibility compliance
"""

import sys
import ast
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Ensure we can import from scripts
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class ViewerCodeAnalyzer:
    """Analyzes viewer_wx.py for potential issues"""
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.issues = defaultdict(list)
        self.stats = {}
        
    def analyze(self):
        """Run all analysis checks"""
        print("=" * 80)
        print("VIEWER APP CODE ANALYSIS")
        print("=" * 80)
        print(f"File: {self.file_path}")
        print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.file_path.exists():
            print(f"ERROR: File not found: {self.file_path}")
            return
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            print(f"CRITICAL: Syntax error in file: {e}")
            return
        
        # Run analysis checks
        self.check_imports(tree, source_code)
        self.check_pyinstaller_compatibility(source_code)
        self.check_error_handling(tree)
        self.check_function_signatures(tree)
        self.check_accessibility(source_code)
        self.check_threading(tree)
        self.calculate_stats(tree, source_code)
        
        # Display results
        self.display_results()
        
        return self.issues, self.stats
    
    def check_imports(self, tree, source_code):
        """Check import patterns for issues"""
        print("[1/6] Checking import patterns...")
        
        # Look for problematic import patterns
        import_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        
        for node in import_nodes:
            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                
                # Check for 'from scripts.' pattern (PyInstaller issue)
                if module.startswith('scripts.'):
                    line_num = node.lineno
                    self.issues['pyinstaller_imports'].append({
                        'line': line_num,
                        'module': module,
                        'issue': "Import from 'scripts.' may fail in frozen mode",
                        'severity': 'high'
                    })
                
                # Check for try/except fallback pattern
                # This is good - check if imports have fallbacks
                line_idx = node.lineno - 1
                lines = source_code.split('\n')
                
                # Look back to see if in try block
                in_try = False
                for i in range(max(0, line_idx - 5), line_idx):
                    if 'try:' in lines[i]:
                        in_try = True
                        break
                
                if module.startswith(('scripts', 'shared', 'models')) and not in_try:
                    self.issues['missing_import_fallback'].append({
                        'line': node.lineno,
                        'module': module,
                        'issue': 'Import without try/except fallback',
                        'severity': 'medium'
                    })
        
        print(f"  - Found {len(import_nodes)} imports")
        print(f"  - PyInstaller issues: {len(self.issues['pyinstaller_imports'])}")
        print(f"  - Missing fallbacks: {len(self.issues['missing_import_fallback'])}")
    
    def check_pyinstaller_compatibility(self, source_code):
        """Check for PyInstaller-specific issues"""
        print("[2/6] Checking PyInstaller compatibility...")
        
        lines = source_code.split('\n')
        
        # Check for frozen mode detection
        has_frozen_check = any('getattr(sys,' in line and 'frozen' in line for line in lines)
        if not has_frozen_check:
            self.issues['pyinstaller'].append({
                'issue': 'No sys.frozen check found',
                'severity': 'medium',
                'line': 0
            })
        
        # Check for path resolution
        has_path_resolution = any('_project_root' in line or 'executable' in line for line in lines)
        if has_path_resolution:
            print(f"  + Has proper path resolution for frozen mode")
        else:
            self.issues['pyinstaller'].append({
                'issue': 'Missing project root path resolution',
                'severity': 'high',
                'line': 0
            })
    
    def check_error_handling(self, tree):
        """Check error handling patterns"""
        print("[3/6] Checking error handling...")
        
        try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
        except_handlers = sum(len(node.handlers) for node in try_blocks)
        
        # Find functions without error handling
        func_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        funcs_without_try = []
        
        for func in func_defs:
            # Skip small functions (likely trivial)
            if len(func.body) < 3:
                continue
            
            has_try = any(isinstance(node, ast.Try) for node in ast.walk(func))
            if not has_try and func.name.startswith('on_') or func.name in ['load_workspace', 'load_image', 'redescribe']:
                funcs_without_try.append({
                    'function': func.name,
                    'line': func.lineno,
                    'issue': 'Event handler or critical function without try/except',
                    'severity': 'medium'
                })
        
        self.issues['error_handling'].extend(funcs_without_try)
        
        print(f"  - Try/except blocks: {len(try_blocks)}")
        print(f"  - Exception handlers: {except_handlers}")
        print(f"  - Functions without error handling: {len(funcs_without_try)}")
    
    def check_function_signatures(self, tree):
        """Check function signatures for consistency"""
        print("[4/6] Checking function signatures...")
        
        func_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        # Check for functions with many parameters (potential signature mismatch issues)
        complex_signatures = []
        for func in func_defs:
            num_args = len(func.args.args)
            if num_args > 5:
                complex_signatures.append({
                    'function': func.name,
                    'line': func.lineno,
                    'args_count': num_args,
                    'issue': f'Function has {num_args} parameters (potential signature mismatch)',
                    'severity': 'low'
                })
        
        self.issues['complex_signatures'].extend(complex_signatures)
        print(f"  - Total functions: {len(func_defs)}")
        print(f"  - Complex signatures (>5 params): {len(complex_signatures)}")
    
    def check_accessibility(self, source_code):
        """Check accessibility compliance"""
        print("[5/6] Checking accessibility compliance...")
        
        lines = source_code.split('\n')
        
        # Check for accessible patterns
        has_listbox = any('DescriptionListBox' in line for line in lines)
        has_name_params = sum(1 for line in lines if 'name=' in line)
        has_labels = sum(1 for line in lines if 'wx.StaticText' in line and 'label=' in line)
        
        # Check for wx.ListCtrl (should use wx.ListBox for accessibility)
        uses_listctrl = any('wx.ListCtrl' in line for line in lines)
        
        if uses_listctrl:
            self.issues['accessibility'].append({
                'issue': 'Uses wx.ListCtrl instead of wx.ListBox (accessibility concern)',
                'severity': 'medium',
                'line': next(i+1 for i, line in enumerate(lines) if 'wx.ListCtrl' in line)
            })
        
        if has_listbox:
            print(f"  + Uses accessible DescriptionListBox")
        
        print(f"  - name= parameters: {has_name_params}")
        print(f"  - Static text labels: {has_labels}")
    
    def check_threading(self, tree):
        """Check threading implementation"""
        print("[6/6] Checking threading implementation...")
        
        # Find threading-related code
        thread_nodes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if 'Thread' in ast.unparse(node.func):
                        thread_nodes.append(node)
        
        # Check for proper thread cleanup
        has_thread_cleanup = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ['join', 'daemon']:
                has_thread_cleanup = True
                break
        
        if len(thread_nodes) > 0 and not has_thread_cleanup:
            self.issues['threading'].append({
                'issue': 'Threading used but no explicit cleanup found',
                'severity': 'medium',
                'line': 0
            })
        
        print(f"  - Threading nodes found: {len(thread_nodes)}")
        print(f"  - Has cleanup: {has_thread_cleanup}")
    
    def calculate_stats(self, tree, source_code):
        """Calculate code statistics"""
        lines = source_code.split('\n')
        
        self.stats = {
            'total_lines': len(lines),
            'code_lines': sum(1 for line in lines if line.strip() and not line.strip().startswith('#')),
            'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
            'blank_lines': sum(1 for line in lines if not line.strip()),
            'functions': len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]),
            'classes': len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]),
            'imports': len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]),
            'try_blocks': len([node for node in ast.walk(tree) if isinstance(node, ast.Try)]),
        }
    
    def display_results(self):
        """Display analysis results"""
        print()
        print("=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        
        # Statistics
        print("\n[*] CODE STATISTICS")
        print("-" * 80)
        for key, value in self.stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Issues by severity
        print("\n[!] ISSUES FOUND")
        print("-" * 80)
        
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        if total_issues == 0:
            print("  + No issues found!")
            return
        
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for category, issues in self.issues.items():
            if not issues:
                continue
            
            print(f"\n{category.upper().replace('_', ' ')} ({len(issues)} issues):")
            
            for issue in issues:
                severity = issue.get('severity', 'unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                icon = {'high': '[H]', 'medium': '[M]', 'low': '[L]'}.get(severity, '[?]')
                line_info = f"Line {issue['line']}: " if 'line' in issue and issue['line'] > 0 else ""
                print(f"  {icon} {line_info}{issue['issue']}")
                
                # Show additional details if available
                if 'module' in issue:
                    print(f"     Module: {issue['module']}")
                if 'function' in issue:
                    print(f"     Function: {issue['function']}")
        
        print(f"\n[#] ISSUE SUMMARY")
        print("-" * 80)
        print(f"  [H] High severity: {severity_counts['high']}")
        print(f"  [M] Medium severity: {severity_counts['medium']}")
        print(f"  [L] Low severity: {severity_counts['low']}")
        print(f"  Total: {total_issues}")


def main():
    """Run viewer analysis"""
    viewer_path = project_root / "viewer" / "viewer_wx.py"
    
    analyzer = ViewerCodeAnalyzer(viewer_path)
    issues, stats = analyzer.analyze()
    
    # Save results to JSON
    output_dir = project_root / "docs" / "WorkTracking"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"viewer_analysis_{timestamp}.json"
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'file_analyzed': str(viewer_path),
        'statistics': stats,
        'issues': dict(issues),
        'total_issues': sum(len(v) for v in issues.values())
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[>] Results saved to: {output_file}")
    
    return 0 if results['total_issues'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
