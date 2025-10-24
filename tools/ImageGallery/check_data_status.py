#!/usr/bin/env python3
"""
Data Collection Status Checker
Analyzes both relative and absolute description directories to determine
what configurations are complete vs missing from the expected 40-workflow matrix.
"""

import os
import glob
from pathlib import Path

def count_descriptions(workflow_dir):
    """Count valid description files in a workflow directory."""
    if not os.path.exists(workflow_dir):
        return 0
    # Look in the descriptions subdirectory
    desc_dir = os.path.join(workflow_dir, "descriptions")
    if not os.path.exists(desc_dir):
        return 0
    txt_files = glob.glob(os.path.join(desc_dir, "*.txt"))
    return len(txt_files)

def parse_workflow_name(workflow_name):
    """Parse workflow directory name to extract components."""
    # Format: wf_25imagetest_{provider}_{model}_{prompt}_{date}_{time}
    parts = workflow_name.split('_')
    if len(parts) < 6:
        return None, None, None
    
    provider = parts[2]
    
    # Model is everything between provider and the last 3 parts (prompt, date, time)
    model_parts = parts[3:-3]
    model = '_'.join(model_parts)
    
    # Prompt is third from the end
    prompt = parts[-3]
    
    return provider, model, prompt

def main():
    """Main analysis function."""
    print("="*70)
    print("IDT Data Collection Status Report")
    print("="*70)
    
    # Define expected configurations
    expected_configs = {
        'claude': {
            'claude-3-5-haiku-20241022': ['narrative', 'colorful', 'technical', 'detailed'],
            'claude-opus-4-20250514': ['narrative', 'colorful', 'technical', 'detailed'],
            'claude-sonnet-4-5-20250929': ['narrative', 'colorful', 'technical', 'detailed']
        },
        'openai': {
            'gpt-4o-mini': ['narrative', 'colorful', 'technical', 'detailed'],
            'gpt-4o': ['narrative', 'colorful', 'technical', 'detailed']
        },
        'ollama': {
            'gemma3:latest': ['narrative', 'colorful', 'technical', 'detailed'],
            'granite3.2-vision:latest': ['narrative', 'colorful', 'technical', 'detailed'],
            'llava:latest': ['narrative', 'colorful', 'technical', 'detailed'],
            'moondream:latest': ['narrative', 'colorful', 'technical', 'detailed'],
            'qwen3-vl:235b-cloud': ['narrative', 'colorful', 'technical', 'detailed']
        }
    }
    
    # Calculate total expected
    total_expected = sum(len(models) * 4 for models in expected_configs.values()) # 4 prompts each
    print(f"Expected configurations: {total_expected}")
    
    # Check both directories
    relative_dir = Path("Descriptions")
    absolute_dir = Path("c:/idt/descriptions")
    
    found_configs = {}
    failed_configs = []
    all_workflows = []
    
    # Scan both directories
    for base_dir in [relative_dir, absolute_dir]:
        if not base_dir.exists():
            print(f"Directory {base_dir} does not exist")
            continue
            
        print(f"\nScanning: {base_dir}")
        workflows = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith('wf_25imagetest_')]
        print(f"Found {len(workflows)} workflow directories")
        
        for wf_dir in workflows:
            wf_name = wf_dir.name
            all_workflows.append(wf_name)
            
            provider, model, prompt = parse_workflow_name(wf_name)
            if not all([provider, model, prompt]):
                print(f"  Warning: Could not parse {wf_name}")
                continue
            
            desc_count = count_descriptions(wf_dir)
            
            # Normalize model names for comparison
            if model.startswith('gemma3_latest'):
                model = 'gemma3:latest'
            elif model.startswith('granite3.2-vision_latest'):
                model = 'granite3.2-vision:latest'  
            elif model.startswith('llava_latest'):
                model = 'llava:latest'
            elif model.startswith('moondream_latest'):
                model = 'moondream:latest'
            elif model.startswith('qwen3-vl_235b-cloud'):
                model = 'qwen3-vl:235b-cloud'
            
            config_key = f"{provider}_{model}_{prompt}"
            
            if desc_count > 0:
                if config_key not in found_configs:
                    found_configs[config_key] = {
                        'provider': provider,
                        'model': model, 
                        'prompt': prompt,
                        'count': desc_count,
                        'location': str(base_dir),
                        'workflow': wf_name
                    }
                    print(f"  ✓ {config_key}: {desc_count} descriptions")
                else:
                    print(f"  ~ {config_key}: {desc_count} descriptions (duplicate, already found)")
            else:
                failed_configs.append({
                    'provider': provider,
                    'model': model,
                    'prompt': prompt,
                    'location': str(base_dir),
                    'workflow': wf_name
                })
                print(f"  ✗ {config_key}: 0 descriptions (FAILED)")
    
    # Summary report
    print(f"\n{'='*70}")
    print("SUMMARY REPORT")
    print(f"{'='*70}")
    print(f"Total workflow directories found: {len(set(all_workflows))}")
    print(f"Successful configurations: {len(found_configs)}")
    print(f"Failed configurations: {len(failed_configs)}")
    print(f"Expected configurations: {total_expected}")
    print(f"Missing configurations: {total_expected - len(found_configs)}")
    
    # Break down by provider and prompt
    provider_counts = {}
    prompt_counts = {}
    
    for config in found_configs.values():
        provider = config['provider']
        prompt = config['prompt']
        
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        prompt_counts[prompt] = prompt_counts.get(prompt, 0) + 1
    
    print(f"\nBy Provider:")
    for provider in ['claude', 'openai', 'ollama']:
        expected = sum(len(prompts) for prompts in expected_configs[provider].values())
        actual = provider_counts.get(provider, 0)
        print(f"  {provider}: {actual}/{expected} configurations")
    
    print(f"\nBy Prompt:")
    for prompt in ['narrative', 'colorful', 'technical', 'detailed']:
        expected = sum(len(models) for models in expected_configs.values())
        actual = prompt_counts.get(prompt, 0)
        print(f"  {prompt}: {actual}/{expected} configurations")
    
    # List failed configurations
    if failed_configs:
        print(f"\nFAILED CONFIGURATIONS ({len(failed_configs)}):")
        for config in failed_configs:
            print(f"  ✗ {config['provider']} {config['model']} {config['prompt']} - {config['location']}")
    
    # List missing configurations (expected but not found at all)
    missing_configs = []
    for provider, models in expected_configs.items():
        for model, prompts in models.items():
            for prompt in prompts:
                config_key = f"{provider}_{model}_{prompt}"
                if config_key not in found_configs:
                    # Check if it's in failed configs
                    is_failed = any(f['provider'] == provider and f['model'] == model and f['prompt'] == prompt 
                                  for f in failed_configs)
                    if not is_failed:
                        missing_configs.append(f"{provider} {model} {prompt}")
    
    if missing_configs:
        print(f"\nCOMPLETELY MISSING CONFIGURATIONS ({len(missing_configs)}):")
        for config in missing_configs:
            print(f"  ? {config}")
    
    print(f"\n{'='*70}")
    if len(found_configs) == total_expected:
        print("🎉 DATA COLLECTION COMPLETE!")
    else:
        print(f"📊 Data collection: {len(found_configs)}/{total_expected} configurations ready")
        if failed_configs:
            print(f"⚠️  {len(failed_configs)} configurations failed and need re-running")
        if missing_configs:
            print(f"❓ {len(missing_configs)} configurations never attempted")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()