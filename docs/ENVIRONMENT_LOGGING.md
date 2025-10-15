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
- Total and available RAM (if psutil installed)
- CPU frequency (if psutil installed)
- Disk space (if psutil installed)
- GPU information (Windows only, best effort)

### Environment
- Username
- Computer name
- Home directory
- Current working directory

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
  Memory Total Gb     : 16.0
  Memory Available Gb : 8.5

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
