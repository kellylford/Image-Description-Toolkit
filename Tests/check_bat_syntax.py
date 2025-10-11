#!/usr/bin/env python3
"""Check all batch files for common syntax issues"""

import os
import glob
import re

def check_batch_syntax(file_path):
    """Check a batch file for common syntax issues"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        issues = []
        in_if_block = False
        paren_stack = []
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check for unmatched parentheses in if statements
            if line_stripped.startswith('if ') and '(' in line:
                open_parens = line.count('(')
                close_parens = line.count(')')
                if open_parens > close_parens:
                    in_if_block = True
                    paren_stack.append(i)
                elif open_parens < close_parens:
                    issues.append(f"Line {i}: Extra closing parenthesis")
            
            # Check for closing of if blocks
            if in_if_block and line_stripped == ')':
                if paren_stack:
                    paren_stack.pop()
                    if not paren_stack:
                        in_if_block = False
                else:
                    issues.append(f"Line {i}: Unexpected closing parenthesis")
            
            # Check for missing exit statements in error conditions
            if 'not found' in line_stripped.lower() or 'error:' in line_stripped.lower():
                # Look ahead for exit statement
                has_exit = False
                for j in range(i, min(i+3, len(lines))):
                    if j < len(lines) and 'exit /b' in lines[j]:
                        has_exit = True
                        break
                if not has_exit and 'echo' in line_stripped:
                    issues.append(f"Line {i}: Error message without exit statement")
            
            # Check for unclosed quotes
            quote_count = line.count('"')
            if quote_count % 2 != 0:
                issues.append(f"Line {i}: Unclosed quotes")
            
            # Check for invalid variable syntax
            if re.search(r'%[^%\s]*[^%]$', line_stripped):
                issues.append(f"Line {i}: Potentially unclosed variable reference")
        
        # Check for unclosed if blocks
        if in_if_block and paren_stack:
            issues.append(f"Unclosed if block starting at line {paren_stack[0]}")
        
        return issues
        
    except Exception as e:
        return [f"Error reading file: {e}"]

def main():
    """Check all batch files for syntax issues"""
    bat_exe_dir = "bat_exe"
    
    if not os.path.exists(bat_exe_dir):
        print(f"Directory {bat_exe_dir} not found")
        return
    
    # Find all .bat files
    bat_files = glob.glob(os.path.join(bat_exe_dir, "*.bat"))
    
    if not bat_files:
        print(f"No .bat files found in {bat_exe_dir}")
        return
    
    print(f"Checking {len(bat_files)} batch files for syntax issues...")
    print("=" * 60)
    
    total_issues = 0
    files_with_issues = 0
    
    for bat_file in sorted(bat_files):
        file_name = os.path.basename(bat_file)
        issues = check_batch_syntax(bat_file)
        
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            print(f"❌ {file_name}:")
            for issue in issues:
                print(f"   • {issue}")
            print()
        else:
            print(f"✅ {file_name} - OK")
    
    print("=" * 60)
    print(f"Summary: {files_with_issues} files with issues, {total_issues} total issues found")
    
    if total_issues == 0:
        print("🎉 All batch files pass syntax check!")
    else:
        print("⚠️  Some batch files need attention")

if __name__ == "__main__":
    main()