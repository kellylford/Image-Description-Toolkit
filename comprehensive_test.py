#!/usr/bin/env python3
"""
ImageDescriber Comprehensive Testing Script

This script automatically tests all available Ollama models with all available 
prompt styles on a batch of test images, running the complete workflow pipeline.

Usage:
    python comprehensive_test.py <path_to_images>
    
Example:
    python comprehensive_test.py "C:\\Photos\\test_images"
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import csv


class ComprehensiveTester:
    """Comprehensive testing class for ImageDescriber workflow"""
    
    def __init__(self, image_path: str, output_base: Optional[str] = None):
        """
        Initialize the comprehensive tester
        
        Args:
            image_path: Path to directory containing test images
            output_base: Optional custom output directory
        """
        self.image_path = Path(image_path)
        if not self.image_path.exists():
            raise ValueError(f"Image path does not exist: {image_path}")
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_base:
            self.output_base = Path(output_base)
        else:
            self.output_base = Path(f"comprehensive_test_{timestamp}")
        
        self.output_base.mkdir(parents=True, exist_ok=True)
        
        # Determine script directory - workflow.py should be in scripts/ subdirectory
        self.script_dir = Path(__file__).parent / "scripts"
        if not self.script_dir.exists():
            # If scripts directory doesn't exist, assume we're running from project root
            self.script_dir = Path(__file__).parent
        
        # Test results storage
        self.results = []
        self.start_time = None
        self.end_time = None
        
        # Statistics
        self.model_stats = {}  # Per-model statistics
        self.prompt_stats = {}  # Per-prompt statistics
        
        print("="*80)
        print("ImageDescriber Comprehensive Testing")
        print("="*80)
        print(f"Image Path: {self.image_path}")
        print(f"Output Directory: {self.output_base}")
        print(f"Start Time: {datetime.now()}")
        print("="*80)
    
    def discover_models(self) -> List[str]:
        """Discover all available Ollama models"""
        print("\n=== STEP 1: Discovering Ollama models ===")
        
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse models from output (skip header)
            models = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip():
                    model_name = line.split()[0]
                    if model_name:
                        models.append(model_name)
                        print(f"Found model: {model_name}")
            
            if not models:
                raise ValueError("No models found in Ollama")
            
            print(f"\nDiscovered {len(models)} models")
            return models
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to query Ollama: {e}")
        except FileNotFoundError:
            raise RuntimeError("Ollama not found. Is Ollama installed and in PATH?")
    
    def discover_prompt_styles(self) -> List[str]:
        """Discover all available prompt styles from config"""
        print("\n=== STEP 2: Discovering prompt styles ===")
        
        config_path = self.script_dir / "image_describer_config.json"
        if not config_path.exists():
            # Try current directory
            config_path = Path("image_describer_config.json")
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            prompt_styles = list(config.get('prompt_variations', {}).keys())
            
            for style in prompt_styles:
                print(f"Found prompt style: {style}")
            
            if not prompt_styles:
                raise ValueError("No prompt styles found in config file")
            
            print(f"\nDiscovered {len(prompt_styles)} prompt styles")
            return prompt_styles
            
        except Exception as e:
            raise RuntimeError(f"Failed to read config file: {e}")
    
    def sanitize_name(self, name: str) -> str:
        """Convert model/prompt names to filesystem-safe strings"""
        if not name:
            return "unknown"
        # Replace problematic characters
        safe_name = name.replace(':', '_').replace(' ', '_').replace('/', '_')
        # Remove any other problematic characters
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-.')
        return safe_name
    
    def run_combination(self, model: str, prompt: str) -> Dict[str, Any]:
        """
        Run a single model/prompt combination through the complete workflow
        
        Args:
            model: Model name
            prompt: Prompt style name
            
        Returns:
            Dictionary with test results
        """
        # Create output directory for this combination
        safe_model = self.sanitize_name(model)
        safe_prompt = self.sanitize_name(prompt)
        combo_output = self.output_base / f"{safe_model}_{safe_prompt}"
        combo_output.mkdir(parents=True, exist_ok=True)
        
        # Record start time
        start_time = datetime.now()
        
        # Run complete workflow: video extraction, image conversion, description, HTML
        # Ensure all paths are absolute to prevent issues when changing directories
        abs_image_path = self.image_path.resolve()
        abs_combo_output = combo_output.resolve()
        
        # Use absolute path to workflow.py to avoid directory changing issues
        workflow_script = self.script_dir / "workflow.py"
        
        cmd = [
            sys.executable, str(workflow_script),
            str(abs_image_path),
            "--output-dir", str(abs_combo_output),
            "--model", model,
            "--prompt-style", prompt,
            "--steps", "video,convert,describe,html"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
                cwd=str(self.script_dir)  # Set working directory instead of changing it
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Analyze the results
            success = result.returncode == 0
            error_message = None
            
            if not success:
                error_message = result.stderr.strip() if result.stderr else "Unknown error"
            
            # Check what was actually created
            created_files = self.analyze_output(combo_output)
            
            result_data = {
                'model': model,
                'prompt': prompt,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'success': success,
                'error_message': error_message,
                'output_dir': str(combo_output),
                'stdout': result.stdout,
                'stderr': result.stderr,
                'created_files': created_files
            }
            
            # Update statistics
            self.update_statistics(result_data)
            
            return result_data
            
        except subprocess.TimeoutExpired:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            return {
                'model': model,
                'prompt': prompt,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'success': False,
                'error_message': 'Timeout after 30 minutes',
                'output_dir': str(combo_output),
                'stdout': '',
                'stderr': 'Process timed out',
                'created_files': {}
            }
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            return {
                'model': model,
                'prompt': prompt,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'success': False,
                'error_message': str(e),
                'output_dir': str(combo_output),
                'stdout': '',
                'stderr': str(e),
                'created_files': {}
            }
    
    def analyze_output(self, output_dir: Path) -> Dict[str, Any]:
        """Analyze what files were created in the output directory"""
        created_files = {
            'descriptions': False,
            'html_reports': False,
            'extracted_frames': False,
            'converted_images': False,
            'logs': False,
            'description_file_size': 0,
            'html_file_count': 0,
            'frame_count': 0,
            'converted_count': 0
        }
        
        if not output_dir.exists():
            return created_files
        
        # Check for descriptions
        desc_dir = output_dir / "descriptions"
        if desc_dir.exists():
            created_files['descriptions'] = True
            desc_file = desc_dir / "image_descriptions.txt"
            if desc_file.exists():
                created_files['description_file_size'] = desc_file.stat().st_size
        
        # Check for HTML reports
        html_dir = output_dir / "html_reports"
        if html_dir.exists():
            created_files['html_reports'] = True
            html_files = list(html_dir.glob("*.html"))
            created_files['html_file_count'] = len(html_files)
        
        # Check for extracted frames
        frames_dir = output_dir / "extracted_frames"
        if frames_dir.exists():
            created_files['extracted_frames'] = True
            frame_files = list(frames_dir.glob("*.jpg")) + list(frames_dir.glob("*.png"))
            created_files['frame_count'] = len(frame_files)
        
        # Check for converted images
        converted_dir = output_dir / "converted_images"
        if converted_dir.exists():
            created_files['converted_images'] = True
            converted_files = list(converted_dir.glob("*.jpg")) + list(converted_dir.glob("*.png"))
            created_files['converted_count'] = len(converted_files)
        
        # Check for logs
        logs_dir = output_dir / "logs"
        if logs_dir.exists():
            created_files['logs'] = True
        
        return created_files
    
    def update_statistics(self, result: Dict[str, Any]) -> None:
        """Update running statistics"""
        model = result['model']
        prompt = result['prompt']
        duration = result['duration']
        success = result['success']
        
        # Update model statistics
        if model not in self.model_stats:
            self.model_stats[model] = {
                'total_time': 0,
                'total_runs': 0,
                'successes': 0,
                'failures': 0,
                'avg_time': 0,
                'prompts': {}
            }
        
        self.model_stats[model]['total_time'] += duration
        self.model_stats[model]['total_runs'] += 1
        if success:
            self.model_stats[model]['successes'] += 1
        else:
            self.model_stats[model]['failures'] += 1
        self.model_stats[model]['avg_time'] = self.model_stats[model]['total_time'] / self.model_stats[model]['total_runs']
        
        # Update model-prompt statistics
        if prompt not in self.model_stats[model]['prompts']:
            self.model_stats[model]['prompts'][prompt] = {
                'time': duration,
                'success': success
            }
        
        # Update prompt statistics
        if prompt not in self.prompt_stats:
            self.prompt_stats[prompt] = {
                'total_time': 0,
                'total_runs': 0,
                'successes': 0,
                'failures': 0,
                'avg_time': 0
            }
        
        self.prompt_stats[prompt]['total_time'] += duration
        self.prompt_stats[prompt]['total_runs'] += 1
        if success:
            self.prompt_stats[prompt]['successes'] += 1
        else:
            self.prompt_stats[prompt]['failures'] += 1
        self.prompt_stats[prompt]['avg_time'] = self.prompt_stats[prompt]['total_time'] / self.prompt_stats[prompt]['total_runs']
    
    def run_comprehensive_test(self) -> None:
        """Run the complete comprehensive test"""
        # Discover models and prompts
        models = self.discover_models()
        prompts = self.discover_prompt_styles()
        
        total_combinations = len(models) * len(prompts)
        print(f"\n=== STEP 3: Running {total_combinations} test combinations ===")
        print("Steps: video extraction, image conversion, description generation, HTML reports")
        
        # Record overall start time
        self.start_time = datetime.now()
        
        combination = 0
        for model in models:
            for prompt in prompts:
                combination += 1
                
                print(f"\n{'-'*70}")
                print(f"Combination {combination}/{total_combinations}: {model} + {prompt}")
                print(f"{'-'*70}")
                
                result = self.run_combination(model, prompt)
                self.results.append(result)
                
                if result['success']:
                    print(f"✅ SUCCESS: {model} with {prompt} ({result['duration']:.1f}s)")
                else:
                    print(f"❌ FAILED: {model} with {prompt} - {result['error_message']}")
                
                # Small delay to prevent system overload
                time.sleep(1)
        
        # Record overall end time
        self.end_time = datetime.now()
        
        # Generate comprehensive reports
        self.generate_reports()
    
    def generate_reports(self) -> None:
        """Generate comprehensive test reports"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TESTING COMPLETED")
        print(f"{'='*80}")
        
        # Calculate summary statistics
        total_time = (self.end_time - self.start_time).total_seconds()
        successful = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - successful
        
        print(f"Total Runtime: {timedelta(seconds=int(total_time))}")
        print(f"Total Combinations: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(successful/len(self.results)*100):.1f}%")
        print(f"Output Directory: {self.output_base}")
        
        # Generate detailed text report
        self.generate_text_report()
        
        # Generate CSV report
        self.generate_csv_report()
        
        # Generate statistics report
        self.generate_statistics_report()
        
        # Generate comprehensive HTML report
        self.generate_html_report()
        
        # Show failures if any
        if failed > 0:
            self.generate_failure_report()
        
        print(f"\nDetailed reports saved in: {self.output_base}")
    
    def generate_text_report(self) -> None:
        """Generate detailed text report"""
        report_file = self.output_base / "comprehensive_test_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ImageDescriber Comprehensive Test Report\n")
            f.write("="*50 + "\n\n")
            
            f.write(f"Test Date: {self.start_time}\n")
            f.write(f"Image Path: {self.image_path}\n")
            f.write(f"Total Runtime: {self.end_time - self.start_time}\n")
            f.write(f"Total Combinations: {len(self.results)}\n")
            
            successful = sum(1 for r in self.results if r['success'])
            failed = len(self.results) - successful
            f.write(f"Successful: {successful}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Success Rate: {(successful/len(self.results)*100):.1f}%\n\n")
            
            # Detailed results
            f.write("Detailed Results:\n")
            f.write("-" * 50 + "\n")
            
            for result in self.results:
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                f.write(f"{status}: {result['model']} + {result['prompt']} ({result['duration']:.1f}s)\n")
                if not result['success']:
                    f.write(f"  Error: {result['error_message']}\n")
                f.write(f"  Output: {result['output_dir']}\n")
                
                # File creation summary
                files = result['created_files']
                f.write(f"  Created: ")
                created_items = []
                if files['descriptions']:
                    created_items.append(f"descriptions ({files['description_file_size']} bytes)")
                if files['html_reports']:
                    created_items.append(f"HTML ({files['html_file_count']} files)")
                if files['extracted_frames']:
                    created_items.append(f"frames ({files['frame_count']})")
                if files['converted_images']:
                    created_items.append(f"converted ({files['converted_count']})")
                if files['logs']:
                    created_items.append("logs")
                
                f.write(", ".join(created_items) if created_items else "none")
                f.write("\n\n")
        
        print(f"Text report saved: {report_file}")
    
    def generate_csv_report(self) -> None:
        """Generate CSV report for data analysis"""
        csv_file = self.output_base / "comprehensive_test_data.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Model', 'Prompt', 'Success', 'Duration_Seconds', 'Error_Message',
                'Output_Directory', 'Descriptions_Created', 'HTML_Created', 
                'Frames_Extracted', 'Images_Converted', 'Logs_Created',
                'Description_File_Size', 'HTML_File_Count', 'Frame_Count', 'Converted_Count'
            ])
            
            # Data rows
            for result in self.results:
                files = result['created_files']
                writer.writerow([
                    result['model'],
                    result['prompt'],
                    result['success'],
                    result['duration'],
                    result['error_message'] or '',
                    result['output_dir'],
                    files['descriptions'],
                    files['html_reports'],
                    files['extracted_frames'],
                    files['converted_images'],
                    files['logs'],
                    files['description_file_size'],
                    files['html_file_count'],
                    files['frame_count'],
                    files['converted_count']
                ])
        
        print(f"CSV data saved: {csv_file}")
    
    def generate_statistics_report(self) -> None:
        """Generate detailed statistics report"""
        stats_file = self.output_base / "test_statistics.txt"
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("ImageDescriber Test Statistics\n")
            f.write("="*40 + "\n\n")
            
            # Model statistics
            f.write("Model Performance Statistics:\n")
            f.write("-" * 40 + "\n")
            
            for model, stats in sorted(self.model_stats.items()):
                f.write(f"\n{model}:\n")
                f.write(f"  Total Time: {timedelta(seconds=int(stats['total_time']))}\n")
                f.write(f"  Average Time: {stats['avg_time']:.1f}s\n")
                f.write(f"  Successes: {stats['successes']}/{stats['total_runs']}\n")
                f.write(f"  Success Rate: {(stats['successes']/stats['total_runs']*100):.1f}%\n")
                
                f.write(f"  Per-prompt breakdown:\n")
                for prompt, prompt_data in stats['prompts'].items():
                    status = "✅" if prompt_data['success'] else "❌"
                    f.write(f"    {status} {prompt}: {prompt_data['time']:.1f}s\n")
            
            # Prompt statistics
            f.write(f"\n\nPrompt Style Statistics:\n")
            f.write("-" * 40 + "\n")
            
            for prompt, stats in sorted(self.prompt_stats.items()):
                f.write(f"\n{prompt}:\n")
                f.write(f"  Total Time: {timedelta(seconds=int(stats['total_time']))}\n")
                f.write(f"  Average Time: {stats['avg_time']:.1f}s\n")
                f.write(f"  Successes: {stats['successes']}/{stats['total_runs']}\n")
                f.write(f"  Success Rate: {(stats['successes']/stats['total_runs']*100):.1f}%\n")
        
        print(f"Statistics report saved: {stats_file}")
    
    def generate_failure_report(self) -> None:
        """Generate detailed failure analysis"""
        failures = [r for r in self.results if not r['success']]
        
        if not failures:
            return
        
        failure_file = self.output_base / "failure_analysis.txt"
        
        with open(failure_file, 'w', encoding='utf-8') as f:
            f.write("Failure Analysis Report\n")
            f.write("="*30 + "\n\n")
            
            f.write(f"Total Failures: {len(failures)}\n\n")
            
            # Group failures by error type
            error_groups = {}
            for failure in failures:
                error = failure['error_message'] or 'Unknown error'
                if error not in error_groups:
                    error_groups[error] = []
                error_groups[error].append(failure)
            
            f.write("Failures by Error Type:\n")
            f.write("-" * 30 + "\n")
            
            for error, failure_list in error_groups.items():
                f.write(f"\n{error} ({len(failure_list)} occurrences):\n")
                for failure in failure_list:
                    f.write(f"  - {failure['model']} + {failure['prompt']}\n")
                    if failure['stderr']:
                        f.write(f"    stderr: {failure['stderr'][:200]}...\n")
            
            f.write(f"\n\nDetailed Failure Information:\n")
            f.write("-" * 30 + "\n")
            
            for failure in failures:
                f.write(f"\n❌ {failure['model']} + {failure['prompt']}:\n")
                f.write(f"  Duration: {failure['duration']:.1f}s\n")
                f.write(f"  Error: {failure['error_message']}\n")
                f.write(f"  Output Dir: {failure['output_dir']}\n")
                if failure['stdout']:
                    f.write(f"  stdout: {failure['stdout'][:500]}...\n")
                if failure['stderr']:
                    f.write(f"  stderr: {failure['stderr'][:500]}...\n")
        
        print(f"Failure analysis saved: {failure_file}")
        
        # Also print summary to console
        print(f"\n❌ FAILURE SUMMARY:")
        error_groups = {}
        for failure in failures:
            error = failure['error_message'] or 'Unknown error'
            error_groups[error] = error_groups.get(error, 0) + 1
        
        for error, count in error_groups.items():
            print(f"  {error}: {count} occurrences")

    def generate_html_report(self) -> None:
        """Generate comprehensive HTML report with visual comparison of all results"""
        html_file = self.output_base / "comprehensive_test_visual_report.html"
        
        # Group results by prompt style, then by model
        results_by_prompt = {}
        successful_results = [r for r in self.results if r['success']]
        
        for result in successful_results:
            prompt = result['prompt']
            if prompt not in results_by_prompt:
                results_by_prompt[prompt] = []
            results_by_prompt[prompt].append(result)
        
        # Get list of image files from the test directory
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']:
            image_files.extend(self.image_path.glob(ext))
            image_files.extend(self.image_path.glob(ext.upper()))
        
        total_successful = len(successful_results)
        total_failed = len(self.results) - total_successful
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ImageDescriber Comprehensive Test Results</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .prompt-section {{
            margin-bottom: 50px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .prompt-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            font-size: 1.3em;
            font-weight: bold;
        }}
        .model-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }}
        .model-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            background: white;
        }}
        .model-header {{
            background: #f8f9fa;
            padding: 15px;
            font-weight: bold;
            color: #333;
            border-bottom: 1px solid #e0e0e0;
        }}
        .model-content {{
            padding: 15px;
        }}
        .timing-info {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }}
        .description {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #28a745;
            font-style: italic;
            margin-bottom: 15px;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        .image-item {{
            text-align: center;
        }}
        .image-item img {{
            max-width: 100%;
            height: 120px;
            object-fit: cover;
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
        .image-name {{
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }}
        .toc {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .toc h3 {{
            margin-top: 0;
        }}
        .toc ul {{
            list-style: none;
            padding: 0;
        }}
        .toc li {{
            margin: 8px 0;
        }}
        .toc a {{
            color: #007bff;
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}
        .toc a:hover {{
            background-color: #e3f2fd;
        }}
        .no-results {{
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 ImageDescriber Comprehensive Test Results</h1>
            <p><strong>Test Date:</strong> {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Image Path:</strong> {self.image_path}</p>
        </div>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-number">{len(self.results)}</div>
                <div class="stat-label">Total Combinations Tested</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_successful}</div>
                <div class="stat-label">Successful Tests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_failed}</div>
                <div class="stat-label">Failed Tests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{(total_successful/len(self.results)*100):.1f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
        </div>
        
        <div class="toc">
            <h3>📋 Table of Contents</h3>
            <ul>""")
            
            for prompt in sorted(results_by_prompt.keys()):
                f.write(f'                <li><a href="#prompt-{self.sanitize_name(prompt)}">🎯 {prompt.title()} Style ({len(results_by_prompt[prompt])} models)</a></li>\n')
            
            f.write("""            </ul>
        </div>
""")
            
            # Generate sections for each prompt style
            for prompt in sorted(results_by_prompt.keys()):
                prompt_results = results_by_prompt[prompt]
                f.write(f"""
        <div class="prompt-section" id="prompt-{self.sanitize_name(prompt)}">
            <div class="prompt-header">
                🎯 {prompt.title()} Style - {len(prompt_results)} Models Tested
            </div>
            <div class="model-grid">""")
                
                # Sort models by average duration for this prompt
                prompt_results.sort(key=lambda x: x['duration'])
                
                for result in prompt_results:
                    model = result['model']
                    duration = result['duration']
                    output_dir = Path(result['output_dir'])
                    
                    # Try to read the description file
                    desc_file = output_dir / "descriptions" / "image_descriptions.txt"
                    descriptions = {}
                    
                    if desc_file.exists():
                        try:
                            with open(desc_file, 'r', encoding='utf-8') as df:
                                content = df.read()
                                # Parse descriptions (assuming format: filename: description)
                                for line in content.split('\n'):
                                    if ':' in line and not line.startswith('='):
                                        filename, desc = line.split(':', 1)
                                        descriptions[filename.strip()] = desc.strip()
                        except Exception:
                            pass
                    
                    f.write(f"""
                <div class="model-card">
                    <div class="model-header">
                        🤖 {model}
                    </div>
                    <div class="model-content">
                        <div class="timing-info">
                            ⏱️ Processing Time: {duration:.1f} seconds
                        </div>""")
                    
                    # Show sample descriptions
                    if descriptions:
                        # Show first few descriptions as examples
                        sample_count = 0
                        for filename, desc in list(descriptions.items())[:2]:  # Show first 2
                            if desc and sample_count < 2:
                                f.write(f"""
                        <div class="description">
                            <strong>{filename}:</strong><br>
                            {desc[:200]}{'...' if len(desc) > 200 else ''}
                        </div>""")
                                sample_count += 1
                        
                        if len(descriptions) > 2:
                            f.write(f"""
                        <div style="text-align: center; color: #666; font-style: italic;">
                            ... and {len(descriptions) - 2} more descriptions
                        </div>""")
                    else:
                        f.write("""
                        <div class="description" style="border-left-color: #dc3545;">
                            No descriptions found or failed to read description file.
                        </div>""")
                    
                    f.write("""
                    </div>
                </div>""")
                
                f.write("""
            </div>
        </div>""")
            
            # Add test images section
            if image_files:
                f.write(f"""
        <div class="prompt-section">
            <div class="prompt-header">
                📸 Test Images Used ({len(image_files)} images)
            </div>
            <div style="padding: 20px;">
                <div class="image-grid">""")
                
                for img_file in image_files[:12]:  # Show first 12 images
                    # Create relative path for web display
                    rel_path = img_file.relative_to(self.image_path)
                    f.write(f"""
                    <div class="image-item">
                        <div class="image-name">{img_file.name}</div>
                    </div>""")
                
                f.write("""
                </div>
            </div>
        </div>""")
            
            f.write(f"""
        
        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666;">
            <p>Generated by ImageDescriber Comprehensive Testing Tool</p>
            <p>Total Runtime: {self.end_time - self.start_time} | {len(image_files)} test images processed</p>
        </div>
        
    </div>
</body>
</html>""")
        
        print(f"Comprehensive HTML report saved: {html_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Comprehensive testing for ImageDescriber workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script runs ALL available Ollama models with ALL available prompt styles
through the COMPLETE workflow pipeline:
  1. Video frame extraction
  2. Image conversion (HEIC to JPG)
  3. AI description generation
  4. HTML report creation

Example:
  python comprehensive_test.py "C:\\Photos\\test_images"
        """
    )
    
    parser.add_argument(
        "image_path",
        help="Path to directory containing test images"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Custom output directory for test results"
    )
    
    args = parser.parse_args()
    
    try:
        tester = ComprehensiveTester(args.image_path, args.output_dir)
        tester.run_comprehensive_test()
        
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
