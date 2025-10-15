# Environment Logging

## Overview

Starting with the ImageDescriber branch updates (October 2025), IDT automatically logs comprehensive environment and machine information whenever a workflow runs. This helps with:

- **Performance Analysis**: Compare Ollama performance across different hardware (NPU vs GPU vs CPU)
- **Troubleshooting**: Identify environment-specific issues
- **Research**: Understand which hardware configurations work best for different models
- **Reproducibility**: Document the exact environment where descriptions were generated

## What Gets Logged

### System Information
- Hostname and fully qualified domain name
- Operating system (Windows, Linux, macOS) and version
- System architecture (ARM64, AMD64, x86_64, etc.)
- Processor information

### Python Information
- Python version
- Implementation (CPython, PyPy, etc.)
- Compiler information
- Whether running as frozen executable or script

### Hardware Information
- CPU core count
- Total RAM (detected via PowerShell on Windows even without psutil)
- Available RAM and usage percentage (if psutil installed)
- CPU frequency (if psutil installed)
- CPU load at workflow start (if psutil installed)
- Disk space and usage (if psutil installed)
- GPU/Display adapter information (Windows, Linux, macOS)
- **NPU Detection**: Automatically detects Copilot+ PC NPU indicators (Qualcomm, Snapdragon, Neural Processing)
- **Copilot+ PC Identification**: Flags likely Copilot+ PCs based on NPU presence

### Environment
- Username
- Computer name
- Home directory
- Current working directory

### Software
- Ollama version (if installed)

## Log Location

Environment logs are saved in the workflow's `logs/` directory with the format:

```
environment_<workflow_name>_<timestamp>.log
```

Example:
```
wf_europe_claude_claude-3-haiku-20240307_narrative_20251015_001947/
  logs/
    environment_europe_20251015_001947.log
    workflow_20251015_001947.log
    image_describer_20251015_002130.log
```

## Log Format

The log file contains two sections:

1. **Human-Readable Format**: Nicely formatted text with sections for easy reading
2. **JSON Data**: Raw JSON at the end for machine parsing and analysis

Example log output:

```
================================================================================
IMAGE DESCRIPTION TOOLKIT - ENVIRONMENT LOG
================================================================================

Timestamp: 2025-10-15T15:04:08.936956
Workflow:  europe

--------------------------------------------------------------------------------
SYSTEM INFORMATION
--------------------------------------------------------------------------------
  Hostname            : SurfacePro7
  Os                  : Windows
  Os Release          : 11
  Architecture        : ARM64
  Processor           : ARMv8 (64-bit) Family 8 Model 1 Revision 201, Qualcomm Technologies Inc

--------------------------------------------------------------------------------
PYTHON INFORMATION
--------------------------------------------------------------------------------
  Version             : 3.13.9
  Implementation      : CPython
  Frozen              : False

--------------------------------------------------------------------------------
HARDWARE INFORMATION
--------------------------------------------------------------------------------
  Cpu Count           : 12
  Memory Total Gb     : 32.0
  Memory Available Gb : 24.5
  Memory Percent Used : 23.4
  Cpu Freq Current Mhz: 3000.0
  Cpu Percent At Start: 15.2
  GPU                 :
    - Qualcomm(R) Adreno(TM) X1-85 GPU (Qualcomm(R) Adreno(TM) Graphics)
  Npu Detected        : True
  Copilot Plus Pc     : Likely (NPU indicators found in GPU info)

--------------------------------------------------------------------------------
SOFTWARE INFORMATION
--------------------------------------------------------------------------------
  Ollama Version      : ollama version is 0.12.5

--------------------------------------------------------------------------------
ENVIRONMENT
--------------------------------------------------------------------------------
  Username            : kelly
  Computername        : SURFACEPRO7

================================================================================
RAW JSON DATA (for machine parsing)
================================================================================
{
  "timestamp": "2025-10-15T15:04:08.936956",
  "workflow_name": "europe",
  "system": {
    "hostname": "SurfacePro7",
    "os": "Windows",
    "architecture": "ARM64",
    ...
  },
  ...
}
```

## Use Cases

### Comparing Ollama Performance Across Machines

When analyzing stats, you can correlate performance with hardware:

```bash
# Run workflow on Copilot+ PC (NPU)
python workflow.py photos --model llama3.2-vision

# Run same workflow on desktop PC (GPU)
python workflow.py photos --model llama3.2-vision

# Compare in stats analysis - environment logs show the difference
python analysis/stats_analysis.py --input-dir descriptions/
```

The stats analyzer could be enhanced to automatically include environment info in comparisons.

### Identifying ARM64 vs AMD64 Issues

Some models or features may behave differently on ARM64 (Copilot+ PCs) vs AMD64 (traditional PCs). The environment log documents the architecture.

### Verifying Frozen vs Script Execution

The `frozen` field shows whether the workflow was run as:
- `true`: Frozen executable (idt.exe)
- `false`: Python script (workflow.py)

This helps troubleshoot differences between development and production environments.

## Hardware Detection

### GPU/NPU Detection

IDT now uses modern PowerShell commands for GPU detection on Windows instead of the deprecated `wmic` tool. This provides:

- **Better accuracy** on Windows 11 and modern systems
- **NPU detection** for Copilot+ PCs (detects Qualcomm, Snapdragon, Neural Processing indicators)
- **Cross-platform support** (Windows PowerShell, Linux lspci, macOS system_profiler)
- **Detailed GPU info** including driver version and video processor

### Memory Detection

Even without psutil installed, IDT can detect total RAM on Windows using PowerShell:

```powershell
(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property capacity -Sum).sum / 1GB
```

For full memory details (available RAM, usage percentage), install psutil:

```bash
pip install psutil
```

### Copilot+ PC Detection

The environment logger automatically identifies likely Copilot+ PCs by looking for NPU indicators in GPU information:

- Qualcomm processor (ARM64)
- Adreno GPU
- Terms like "Snapdragon", "Neural", "NPU", "Hexagon"

When detected, the log includes:
```
Npu Detected        : True
Copilot Plus Pc     : Likely (NPU indicators found in GPU info)
```

This is valuable for comparing Ollama performance between NPU-accelerated and traditional hardware.

## Optional Enhancement: psutil

For extended hardware information (RAM, CPU frequency, disk space), install psutil:

```bash
pip install psutil
```

IDT works fine without it - you'll just see a note in the hardware section:
```
Note: Install psutil for extended hardware information
```

## Future Enhancements

Potential additions to environment logging:

- **GPU/NPU Detection**: Better detection of NPU capabilities on Copilot+ PCs
- **Ollama Version**: Detect installed Ollama version for local models
- **Network Info**: Public IP, network speed for cloud API performance analysis
- **Stats Integration**: Automatically include environment info in stats comparisons
- **Environment Diff**: Tool to compare environments between workflows

## Privacy Note

Environment logs contain your username and computer name. If sharing workflow results publicly, you may want to redact this information from the environment logs. The logs are saved locally and never transmitted anywhere.

## Related Documentation

- [Stats Analysis](../analysis/README.md) - Analyzing workflow performance
- [Workflow Configuration](WORKFLOW_CONFIGURATION.md) - Setting up workflows
- [File Counting Fix](FILE_COUNTING_FIX.md) - Understanding file counts in workflows
