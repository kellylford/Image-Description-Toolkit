"""
Branch Comparison Testing Framework
====================================
Compares behavior of idt CLI between main and WXMigration branches.

Purpose:
- Run identical commands on both branches
- Compare outputs, exit codes, generated files, logs
- Identify behavioral differences and regressions

Date Created: 2026-01-20
Author: AI Agent (Claude Sonnet 4.5)
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import hashlib
import tempfile


class BranchComparator:
    """Compares idt CLI behavior across git branches"""
    
    def __init__(self, repo_path: Path, branch_a: str, branch_b: str):
        self.repo_path = Path(repo_path)
        self.branch_a = branch_a
        self.branch_b = branch_b
        self.current_branch = self._get_current_branch()
        
    def _get_current_branch(self) -> str:
        """Get current git branch"""
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    
    def _checkout_branch(self, branch: str):
        """Checkout a specific branch"""
        print(f"  Checking out branch: {branch}")
        result = subprocess.run(
            ['git', 'checkout', branch],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to checkout {branch}: {result.stderr}")
    
    def _build_idt(self) -> Dict[str, Any]:
        """Build idt.exe in current branch"""
        print("  Building idt.exe...")
        
        build_script = self.repo_path / 'idt' / 'build_idt.bat'
        
        # Run build script
        result = subprocess.run(
            [str(build_script)],
            cwd=self.repo_path / 'idt',
            capture_output=True,
            text=True,
            shell=True,
            timeout=300  # 5 minute timeout
        )
        
        exe_path = self.repo_path / 'idt' / 'dist' / 'idt.exe'
        
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exe_exists': exe_path.exists(),
            'exe_size': exe_path.stat().st_size if exe_path.exists() else 0
        }
    
    def _run_idt_command(self, command: List[str], work_dir: Path, timeout: int = 600) -> Dict[str, Any]:
        """
        Run idt command and capture all outputs
        
        Args:
            command: List of command arguments (e.g., ['workflow', 'testimages'])
            work_dir: Working directory for command execution
            timeout: Command timeout in seconds (default 10 minutes)
        
        Returns:
            Dictionary with execution results
        """
        exe_path = self.repo_path / 'idt' / 'dist' / 'idt.exe'
        
        if not exe_path.exists():
            return {
                'success': False,
                'error': 'idt.exe not found',
                'exit_code': -1
            }
        
        full_command = [str(exe_path)] + command
        
        print(f"  Running: {' '.join(full_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timed_out': False
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'timed_out': True
            }
    
    def _collect_outputs(self, work_dir: Path) -> Dict[str, Any]:
        """Collect all output files and logs from work directory"""
        
        outputs = {
            'workflow_dirs': [],
            'description_files': [],
            'html_files': [],
            'log_files': [],
            'csv_files': [],
            'file_count': 0,
            'total_size': 0
        }
        
        # Find workflow directories
        workflow_dirs = list(work_dir.glob('wf_*'))
        outputs['workflow_dirs'] = [d.name for d in workflow_dirs]
        
        # Scan for specific file types
        for wf_dir in workflow_dirs:
            # Description files
            desc_files = list((wf_dir / 'descriptions').glob('*.txt')) if (wf_dir / 'descriptions').exists() else []
            outputs['description_files'].extend([f.relative_to(work_dir).as_posix() for f in desc_files])
            
            # HTML files
            html_files = list((wf_dir / 'HTML_Output').glob('*.html')) if (wf_dir / 'HTML_Output').exists() else []
            outputs['html_files'].extend([f.relative_to(work_dir).as_posix() for f in html_files])
            
            # Log files
            log_files = list((wf_dir / 'logs').glob('*.log')) if (wf_dir / 'logs').exists() else []
            outputs['log_files'].extend([f.relative_to(work_dir).as_posix() for f in log_files])
        
        # CSV files (for combinedescriptions)
        csv_files = list(work_dir.glob('*.csv'))
        outputs['csv_files'] = [f.name for f in csv_files]
        
        # Count total files and size
        all_files = list(work_dir.rglob('*'))
        outputs['file_count'] = len([f for f in all_files if f.is_file()])
        outputs['total_size'] = sum(f.stat().st_size for f in all_files if f.is_file())
        
        return outputs
    
    def _extract_errors_from_logs(self, work_dir: Path) -> List[str]:
        """Extract ERROR lines from log files"""
        errors = []
        
        for log_file in work_dir.rglob('*.log'):
            try:
                content = log_file.read_text(encoding='utf-8', errors='ignore')
                for line_num, line in enumerate(content.splitlines(), 1):
                    if 'ERROR' in line.upper() or 'EXCEPTION' in line.upper():
                        errors.append(f"{log_file.name}:{line_num} - {line.strip()}")
            except Exception as e:
                errors.append(f"Failed to read {log_file.name}: {e}")
        
        return errors
    
    def compare_command(self, command: List[str], test_data_source: Path = None) -> Dict[str, Any]:
        """
        Compare a specific command across both branches
        
        Args:
            command: Command to run (e.g., ['workflow', 'testimages'])
            test_data_source: Optional path to test data to copy into work directories
        
        Returns:
            Comparison results dictionary
        """
        results = {
            'command': ' '.join(command),
            'timestamp': datetime.now().isoformat(),
            'branches': {
                self.branch_a: {},
                self.branch_b: {}
            },
            'differences': [],
            'comparison': {}
        }
        
        # Test each branch
        for branch in [self.branch_a, self.branch_b]:
            print(f"\nTesting branch: {branch}")
            
            # Checkout branch
            self._checkout_branch(branch)
            
            # Build idt.exe
            build_result = self._build_idt()
            results['branches'][branch]['build'] = build_result
            
            if not build_result['success']:
                print(f"  [FAIL] Build failed for {branch}")
                results['branches'][branch]['skipped'] = True
                continue
            
            # Create temporary work directory
            with tempfile.TemporaryDirectory() as temp_dir:
                work_dir = Path(temp_dir)
                
                # Copy test data if provided
                if test_data_source and test_data_source.exists():
                    print(f"  Copying test data from {test_data_source}")
                    shutil.copytree(test_data_source, work_dir / test_data_source.name)
                    
                    # Update command to use copied data
                    adjusted_command = [
                        arg if arg != str(test_data_source) else str(work_dir / test_data_source.name)
                        for arg in command
                    ]
                else:
                    adjusted_command = command
                
                # Run command
                run_result = self._run_idt_command(adjusted_command, work_dir)
                results['branches'][branch]['execution'] = run_result
                
                # Collect outputs
                outputs = self._collect_outputs(work_dir)
                results['branches'][branch]['outputs'] = outputs
                
                # Extract errors from logs
                errors = self._extract_errors_from_logs(work_dir)
                results['branches'][branch]['errors'] = errors
                
                # Status summary
                print(f"  Exit code: {run_result['exit_code']}")
                print(f"  Files created: {outputs['file_count']}")
                print(f"  Errors in logs: {len(errors)}")
        
        # Return to original branch
        self._checkout_branch(self.current_branch)
        
        # Compare results
        results['comparison'] = self._compare_results(results['branches'])
        
        return results
    
    def _compare_results(self, branches: Dict[str, Any]) -> Dict[str, Any]:
        """Compare execution results between branches"""
        
        branch_a_data = branches[self.branch_a]
        branch_b_data = branches[self.branch_b]
        
        comparison = {
            'identical': True,
            'differences': []
        }
        
        # Skip if either branch was skipped
        if branch_a_data.get('skipped') or branch_b_data.get('skipped'):
            comparison['identical'] = False
            comparison['differences'].append('One or both builds failed')
            return comparison
        
        # Compare exit codes
        exit_a = branch_a_data['execution']['exit_code']
        exit_b = branch_b_data['execution']['exit_code']
        
        if exit_a != exit_b:
            comparison['identical'] = False
            comparison['differences'].append(
                f"Exit codes differ: {self.branch_a}={exit_a}, {self.branch_b}={exit_b}"
            )
        
        # Compare file counts
        files_a = branch_a_data['outputs']['file_count']
        files_b = branch_b_data['outputs']['file_count']
        
        if files_a != files_b:
            comparison['identical'] = False
            comparison['differences'].append(
                f"File counts differ: {self.branch_a}={files_a}, {self.branch_b}={files_b}"
            )
        
        # Compare error counts
        errors_a = len(branch_a_data['errors'])
        errors_b = len(branch_b_data['errors'])
        
        if errors_a != errors_b:
            comparison['identical'] = False
            comparison['differences'].append(
                f"Error counts differ: {self.branch_a}={errors_a}, {self.branch_b}={errors_b}"
            )
        
        # Compare workflow directory counts
        wf_dirs_a = len(branch_a_data['outputs']['workflow_dirs'])
        wf_dirs_b = len(branch_b_data['outputs']['workflow_dirs'])
        
        if wf_dirs_a != wf_dirs_b:
            comparison['identical'] = False
            comparison['differences'].append(
                f"Workflow dir counts differ: {self.branch_a}={wf_dirs_a}, {self.branch_b}={wf_dirs_b}"
            )
        
        return comparison
    
    def run_test_suite(self, test_cases: List[Tuple[List[str], Path]]) -> Dict[str, Any]:
        """
        Run a suite of test cases
        
        Args:
            test_cases: List of (command, test_data_path) tuples
        
        Returns:
            Aggregate results
        """
        suite_results = {
            'timestamp': datetime.now().isoformat(),
            'branches_compared': [self.branch_a, self.branch_b],
            'test_cases': [],
            'summary': {
                'total_tests': len(test_cases),
                'passed': 0,
                'failed': 0,
                'regressions': []
            }
        }
        
        for i, (command, test_data) in enumerate(test_cases, 1):
            print(f"\n{'='*80}")
            print(f"Test Case {i}/{len(test_cases)}: {' '.join(command)}")
            print('='*80)
            
            result = self.compare_command(command, test_data)
            suite_results['test_cases'].append(result)
            
            # Update summary
            if result['comparison']['identical']:
                suite_results['summary']['passed'] += 1
                print(f"\n[PASS] PASSED - Branches behave identically")
            else:
                suite_results['summary']['failed'] += 1
                suite_results['summary']['regressions'].append({
                    'command': ' '.join(command),
                    'differences': result['comparison']['differences']
                })
                print(f"\n[FAIL] FAILED - Behavioral differences detected:")
                for diff in result['comparison']['differences']:
                    print(f"  - {diff}")
        
        return suite_results


def main():
    """Run comprehensive comparison test suite"""
    
    repo_path = Path(__file__).parent.parent
    
    comparator = BranchComparator(
        repo_path=repo_path,
        branch_a='main',
        branch_b='WXMigration'
    )
    
    # Define test cases
    # Format: (command_args, test_data_path_or_None)
    test_cases = [
        # Version check (simple smoke test)
        (['version'], None),
        
        # Workflow with testimages
        (['workflow', str(repo_path / 'testimages'), '--model', 'gpt-4o-mini', '--skip-video', '--skip-conversion'], None),
        
        # Stats analysis (requires existing workflow directory)
        # This will need an existing workflow - skip for now
        # (['stats', 'wf_*'], None),
        
        # Content analysis
        # (['contentreview', 'wf_*'], None),
    ]
    
    print(f"Starting comparison test suite")
    print(f"Repository: {repo_path}")
    print(f"Comparing: {comparator.branch_a} vs {comparator.branch_b}")
    print(f"Test cases: {len(test_cases)}")
    
    results = comparator.run_test_suite(test_cases)
    
    # Save results
    output_file = repo_path / 'docs' / 'worktracking' / f'comparison_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    
    if results['summary']['regressions']:
        print(f"\nRegressions found:")
        for reg in results['summary']['regressions']:
            print(f"  - {reg['command']}")
            for diff in reg['differences']:
                print(f"    • {diff}")
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return results


if __name__ == '__main__':
    main()
