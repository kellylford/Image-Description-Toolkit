"""
Comprehensive Integration Test Suite for IDT CLI
=================================================
Tests every idt command in both development and frozen modes.

Purpose: Surface ALL issues before systematic fixing.

Test Coverage:
1. All CLI commands with realistic arguments
2. Both dev mode (python scripts/X) and frozen mode (idt.exe X)
3. Output validation (exit codes, files created, logs)
4. Error detection (stderr, exception messages, log errors)

Date: 2026-01-20
Strategy: Find all issues first, then fix systematically
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import tempfile
import shutil


class IDTIntegrationTester:
    """Comprehensive integration testing for all IDT commands"""
    
    def __init__(self, repo_path: Path, test_data_dir: Path = None):
        self.repo_path = Path(repo_path)
        self.test_data_dir = test_data_dir or self.repo_path / 'testimages'
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': []
            }
        }
        
    def run_command(self, cmd: List[str], cwd: Path = None, timeout: int = 60) -> Dict[str, Any]:
        """Run a command and capture all outputs"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'  # Replace problematic characters instead of crashing
            )
            
            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout or '',
                'stderr': result.stderr or '',
                'timed_out': False,
                'exception': None
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'timed_out': True,
                'exception': 'TimeoutExpired'
            }
        except Exception as e:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'timed_out': False,
                'exception': type(e).__name__
            }
    
    def test_version_command(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt version"""
        test_name = f"{mode}_version"
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'version']
        else:  # frozen
            cmd = ['idt/dist/idt.exe', 'version']
        
        result = self.run_command(cmd)
        
        # Check for version string in output
        has_version = 'Image Description Toolkit' in result['stdout']
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'has_version_string': has_version,
                'no_exceptions': result['exception'] is None
            },
            'passed': result['success'] and has_version
        }
    
    def test_help_command(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt --help"""
        test_name = f"{mode}_help"
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', '--help']
        else:
            cmd = ['idt/dist/idt.exe', '--help']
        
        result = self.run_command(cmd)
        
        # Help should show usage and available commands
        has_usage = 'usage:' in result['stdout'].lower()
        has_commands = 'workflow' in result['stdout'].lower()
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'has_usage': has_usage,
                'has_commands': has_commands
            },
            'passed': result['success'] and has_usage and has_commands
        }
    
    def test_workflow_help(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt workflow --help"""
        test_name = f"{mode}_workflow_help"
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'workflow', '--help']
        else:
            cmd = ['idt/dist/idt.exe', 'workflow', '--help']
        
        result = self.run_command(cmd)
        
        has_usage = 'usage:' in result['stdout'].lower()
        has_model_arg = '--model' in result['stdout']
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'has_usage': has_usage,
                'has_model_arg': has_model_arg
            },
            'passed': result['success'] and has_usage
        }
    
    def test_list_prompts(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt prompt-list"""
        test_name = f"{mode}_prompt_list"
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'prompt-list']
        else:
            cmd = ['idt/dist/idt.exe', 'prompt-list']
        
        result = self.run_command(cmd)
        
        # Should list available prompts
        has_output = len(result['stdout']) > 0
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'has_output': has_output,
                'no_errors': 'error' not in result['stderr'].lower()
            },
            'passed': result['success'] and has_output
        }
    
    def test_check_models(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt check-models"""
        test_name = f"{mode}_check_models"
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'check-models']
        else:
            cmd = ['idt/dist/idt.exe', 'check-models']
        
        result = self.run_command(cmd)
        
        has_output = len(result['stdout']) > 0
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'has_output': has_output
            },
            'passed': result['success'] and has_output
        }
    
    def test_results_list(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt results-list"""
        test_name = f"{mode}_results_list"
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'results-list']
        else:
            cmd = ['idt/dist/idt.exe', 'results-list']
        
        result = self.run_command(cmd)
        
        # Should complete without error even if no workflows exist
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'no_crash': result['exception'] is None
            },
            'passed': result['success']
        }
    
    def test_stats_command(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt stats (requires workflow directory)"""
        test_name = f"{mode}_stats"
        
        # Find a workflow directory to test with
        workflow_dirs = list(self.repo_path.glob('wf_*'))
        
        if not workflow_dirs:
            return {
                'test_name': test_name,
                'command': 'idt stats <workflow_dir>',
                'result': {
                    'success': False,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': 'No workflow directories found for testing',
                    'exception': 'NoTestData'
                },
                'validation': {'skipped': True},
                'passed': False,
                'skipped': True
            }
        
        wf_dir = workflow_dirs[0]
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'stats', str(wf_dir)]
        else:
            cmd = ['idt/dist/idt.exe', 'stats', str(wf_dir)]
        
        result = self.run_command(cmd)
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'no_crash': result['exception'] is None
            },
            'passed': result['success']
        }
    
    def test_contentreview_command(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt contentreview (requires workflow directory)"""
        test_name = f"{mode}_contentreview"
        
        workflow_dirs = list(self.repo_path.glob('wf_*'))
        
        if not workflow_dirs:
            return {
                'test_name': test_name,
                'command': 'idt contentreview <workflow_dir>',
                'result': {
                    'success': False,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': 'No workflow directories found for testing',
                    'exception': 'NoTestData'
                },
                'validation': {'skipped': True},
                'passed': False,
                'skipped': True
            }
        
        wf_dir = workflow_dirs[0]
        
        if mode == 'dev':
            cmd = ['python', 'idt/idt_cli.py', 'contentreview', str(wf_dir)]
        else:
            cmd = ['idt/dist/idt.exe', 'contentreview', str(wf_dir)]
        
        result = self.run_command(cmd, timeout=120)  # Longer timeout
        
        return {
            'test_name': test_name,
            'command': ' '.join(cmd),
            'result': result,
            'validation': {
                'exit_code_0': result['exit_code'] == 0,
                'no_crash': result['exception'] is None
            },
            'passed': result['success']
        }
    
    def test_combinedescriptions(self, mode: str = 'dev') -> Dict[str, Any]:
        """Test: idt combinedescriptions"""
        test_name = f"{mode}_combinedescriptions"
        
        # Need workflow directories
        workflow_dirs = list(self.repo_path.glob('wf_*'))
        
        if not workflow_dirs:
            return {
                'test_name': test_name,
                'command': 'idt combinedescriptions',
                'result': {
                    'success': False,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': 'No workflow directories found for testing',
                    'exception': 'NoTestData'
                },
                'validation': {'skipped': True},
                'passed': False,
                'skipped': True
            }
        
        # Create temp output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_file = Path(f.name)
        
        try:
            if mode == 'dev':
                cmd = ['python', 'idt/idt_cli.py', 'combinedescriptions', '--output', str(output_file)]
            else:
                cmd = ['idt/dist/idt.exe', 'combinedescriptions', '--output', str(output_file)]
            
            result = self.run_command(cmd, timeout=120)
            
            # Check if output file was created
            output_created = output_file.exists()
            file_size = output_file.stat().st_size if output_created else 0
            
            return {
                'test_name': test_name,
                'command': ' '.join(cmd),
                'result': result,
                'validation': {
                    'exit_code_0': result['exit_code'] == 0,
                    'output_created': output_created,
                    'output_not_empty': file_size > 0
                },
                'passed': result['success'] and output_created
            }
        finally:
            if output_file.exists():
                output_file.unlink()
    
    def run_all_tests(self, modes: List[str] = ['dev', 'frozen']) -> Dict[str, Any]:
        """Run all integration tests"""
        
        test_methods = [
            self.test_version_command,
            self.test_help_command,
            self.test_workflow_help,
            self.test_list_prompts,
            self.test_check_models,
            self.test_results_list,
            self.test_stats_command,
            self.test_contentreview_command,
            self.test_combinedescriptions,
        ]
        
        for mode in modes:
            print(f"\n{'='*80}")
            print(f"Running tests in {mode.upper()} mode")
            print('='*80)
            
            for test_method in test_methods:
                test_result = test_method(mode)
                self.results['tests'].append(test_result)
                self.results['summary']['total'] += 1
                
                if test_result.get('skipped'):
                    print(f"  [SKIP] {test_result['test_name']} - {test_result['result']['stderr']}")
                    continue
                
                if test_result['passed']:
                    self.results['summary']['passed'] += 1
                    print(f"  [PASS] {test_result['test_name']}")
                else:
                    self.results['summary']['failed'] += 1
                    print(f"  [FAIL] {test_result['test_name']}")
                    print(f"    Exit code: {test_result['result']['exit_code']}")
                    if test_result['result']['stderr']:
                        print(f"    Stderr: {test_result['result']['stderr'][:200]}")
                    
                    # Add to error summary
                    self.results['summary']['errors'].append({
                        'test': test_result['test_name'],
                        'command': test_result['command'],
                        'exit_code': test_result['result']['exit_code'],
                        'stderr': test_result['result']['stderr'],
                        'exception': test_result['result']['exception']
                    })
        
        return self.results
    
    def save_results(self, output_file: Path):
        """Save test results to JSON"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print('='*80)
        print(f"Total tests: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Success rate: {self.results['summary']['passed'] / self.results['summary']['total'] * 100:.1f}%")
        
        if self.results['summary']['errors']:
            print(f"\n{'='*80}")
            print("FAILED TESTS")
            print('='*80)
            for error in self.results['summary']['errors']:
                print(f"\n{error['test']}:")
                print(f"  Command: {error['command']}")
                print(f"  Exit code: {error['exit_code']}")
                if error['stderr']:
                    print(f"  Error: {error['stderr'][:300]}")


def main():
    """Run comprehensive integration tests"""
    repo_path = Path(__file__).parent.parent
    
    tester = IDTIntegrationTester(repo_path)
    
    print("IDT Comprehensive Integration Test Suite")
    print("=" * 80)
    print(f"Repository: {repo_path}")
    print(f"Test modes: dev (Python scripts), frozen (idt.exe)")
    print()
    
    # Check if frozen exe exists
    frozen_exe = repo_path / 'idt' / 'dist' / 'idt.exe'
    modes = ['dev']
    if frozen_exe.exists():
        modes.append('frozen')
        print(f"[INFO] Found idt.exe - will test both dev and frozen modes")
    else:
        print(f"[WARN] idt.exe not found - testing dev mode only")
        print(f"       Run 'cd idt && build_idt.bat' to build frozen executable")
    
    # Run all tests
    results = tester.run_all_tests(modes)
    
    # Print summary
    tester.print_summary()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = repo_path / 'docs' / 'worktracking' / f'integration_test_results_{timestamp}.json'
    tester.save_results(output_file)
    
    # Exit with failure code if any tests failed
    if results['summary']['failed'] > 0:
        return 1
    return 0


if __name__ == '__main__':
    exit(main())
