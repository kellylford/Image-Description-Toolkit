#!/usr/bin/env python3
"""
Real-time performance diagnostics for ImageDescriber
Run this WHILE a batch is processing to see what's slow

Usage:
    python diagnose_performance.py
"""

import psutil
import time
import sys
from pathlib import Path

def find_imagedescriber_process():
    """Find running ImageDescriber process (the actual worker, not the launcher stub)"""
    candidates = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            name = proc.info['name'] or ''
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            if 'imagedescriber' in name.lower() or 'imagedescriber' in cmdline.lower():
                mem_mb = proc.info['memory_info'].rss / 1024 / 1024
                candidates.append((proc, mem_mb))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Return the process with the most memory (that's the actual worker, not the launcher)
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    return None

def monitor_performance():
    """Monitor ImageDescriber performance in real-time"""
    proc = find_imagedescriber_process()
    
    if not proc:
        print("ImageDescriber not running or not found")
        print("Start ImageDescriber first, then run this script")
        return
    
    print(f"Found ImageDescriber (PID {proc.pid})")
    print(f"\nMonitoring performance (Ctrl+C to stop)...\n")
    print(f"{'Time':<12} {'CPU %':<8} {'Memory MB':<12} {'Threads':<10}")
    print("-" * 50)
    
    try:
        while True:
            try:
                # Get process stats
                cpu_percent = proc.cpu_percent(interval=1.0)
                mem_info = proc.memory_info()
                mem_mb = mem_info.rss / 1024 / 1024  # Convert to MB
                num_threads = proc.num_threads()
                
                # Print stats
                timestamp = time.strftime('%H:%M:%S')
                print(f"{timestamp:<12} {cpu_percent:>6.1f}% {mem_mb:>10.1f} MB {num_threads:>8}")
                
                # Warnings
                if cpu_percent > 80:
                    print("  ⚠️  HIGH CPU - UI operations may be blocking")
                if mem_mb > 2000:
                    print("  ⚠️  HIGH MEMORY - possible memory leak")
                if num_threads > 20:
                    print(f"  ⚠️  MANY THREADS ({num_threads}) - check for thread leaks")
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print("\nImageDescriber process terminated")
                break
                
    except KeyboardInterrupt:
        print("\n\nDiagnostics stopped")
        print("\nInterpretation:")
        print("- CPU spikes every few seconds = UI refresh operations (list rebuilds)")
        print("- Steady high CPU = Worker thread processing (normal)")
        print("- Growing memory = Possible leak or caching issue")

if __name__ == '__main__':
    monitor_performance()
