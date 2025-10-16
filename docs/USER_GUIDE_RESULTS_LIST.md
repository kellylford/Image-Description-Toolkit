# Using the results-list Command

The `idt results-list` command scans your workflow results directory and creates a CSV catalog of all available workflows with convenient viewer commands.

## Basic Usage

```bash
# List all workflows in the default Descriptions directory
# Creates workflow_results.csv (or auto-increments if exists)
idt results-list

# List workflows in a specific directory
idt results-list --input-dir c:\path\to\descriptions

# Save to a custom output file
idt results-list --output my_workflows.csv

# Sort by different fields
idt results-list --sort-by model
idt results-list --sort-by name
idt results-list --sort-by provider
```

**Note:** If you don't specify `--output`, the command will automatically create `workflow_results.csv`, `workflow_results_1.csv`, `workflow_results_2.csv`, etc. to avoid overwriting existing files. If you do specify `--output`, it will respect your choice even if the file exists.

## CSV Output Format

The generated CSV contains these columns:

| Column | Description | Example |
|--------|-------------|---------|
| Name | Workflow name | `promptbaseline` |
| Provider | AI provider | `ollama`, `openai`, `claude` |
| Model | Model name | `qwen3-vl:235b-cloud` |
| Prompt | Prompt style used | `Simple`, `artistic`, `detailed` |
| Descriptions | Number of descriptions generated | `64`, `150`, `1077` |
| Timestamp | When workflow ran | `2025-10-16 07:46:07` |
| Viewer Command | Ready-to-use command | `idt viewer "Descriptions/wf_..."` |

### How Description Counts Are Determined

The command uses a three-method approach to accurately count descriptions:

1. **Primary**: Parses `logs/status.log` for "Image description complete (X descriptions)"
2. **Secondary**: Parses `logs/image_describer_progress.txt` for "Processed X of Y"
3. **Fallback**: Counts "File:" markers in `descriptions/image_descriptions.txt`

This ensures accurate counts even for workflows with thousands of images.

## Example Output

```csv
Name,Provider,Model,Prompt,Descriptions,Timestamp,Viewer Command
promptbaseline,ollama,qwen3-vl_235b-cloud,Simple,64,2025-10-16 07:46:07,"idt viewer ""Descriptions/wf_promptbaseline_ollama_qwen3-vl_235b-cloud_Simple_20251016_074607"""
promptbaseline,ollama,qwen3-vl_235b-cloud,artistic,64,2025-10-16 07:55:43,"idt viewer ""Descriptions/wf_promptbaseline_ollama_qwen3-vl_235b-cloud_artistic_20251016_075543"""
bigdaddyrun,ollama,qwen3-vl_235b-cloud,Simple,1077,2025-10-16 08:03:25,"idt viewer ""Descriptions/wf_bigdaddyrun_ollama_qwen3-vl_235b-cloud_Simple_20251016_080325"""
```

## Viewing Results

To view a specific workflow, simply:

1. Open the CSV in Excel or a text editor
2. Find the workflow you want to view
3. Copy the command from the "Viewer Command" column
4. Paste it into your command prompt and press Enter

Example:
```bash
idt viewer "Descriptions/wf_promptbaseline_ollama_qwen3-vl_235b-cloud_artistic_20251016_075543"
```

## Advanced Options

### Absolute Paths

By default, viewer commands use relative paths. For absolute paths:

```bash
idt results-list --absolute-paths
```

This generates commands like:
```bash
idt viewer "C:/idt/Descriptions/wf_promptbaseline_..."
```

### Custom Sort Order

```bash
# Sort by workflow name (alphabetical)
idt results-list --sort-by name

# Sort by timestamp (chronological, default)
idt results-list --sort-by timestamp

# Sort by provider
idt results-list --sort-by provider

# Sort by model
idt results-list --sort-by model
```

## Use Cases

### Research & Comparison

When running experiments with different prompts or models:

```bash
# Run multiple workflows
idt workflow --prompt-style Simple --name experiment1 images/
idt workflow --prompt-style artistic --name experiment1 images/
idt workflow --prompt-style technical --name experiment1 images/

# Generate catalog
idt results-list --output experiment1_catalog.csv

# Open in Excel to compare results
```

### Workflow Inventory

Keep track of all workflow runs:

```bash
# Monthly catalog
idt results-list --output workflows_october_2025.csv --sort-by timestamp

# Per-project catalog
idt results-list --input-dir projects/vacation_photos/descriptions --output vacation_workflows.csv
```

### Quick Access

Generate a "cheat sheet" of viewer commands:

```bash
idt results-list --output quick_access.csv
# Keep quick_access.csv handy for easy copy/paste access to all workflows
```

## Integration with Other Tools

The CSV output can be imported into:

- **Excel**: For filtering, sorting, and analysis
- **Database**: Import as table for querying
- **Scripts**: Parse with Python/PowerShell for automation
- **Documentation**: Include in reports or wikis

## Metadata Detection

The command attempts to read workflow metadata from:

1. **Primary**: `workflow_metadata.json` in each workflow directory
2. **Fallback**: Parse directory name (format: `wf_<name>_<provider>_<model>_<prompt>_<timestamp>`)

If a workflow directory doesn't have metadata, it will appear with "unknown" values in the CSV.

## File Management

### Auto-Increment Protection

When you run `idt results-list` without specifying `--output`, the command automatically prevents overwriting existing files:

```bash
# First run
idt results-list
# Creates: workflow_results.csv

# Second run
idt results-list
# Creates: workflow_results_1.csv

# Third run
idt results-list
# Creates: workflow_results_2.csv
```

This ensures you never accidentally lose previous catalogs. If you specify `--output`, the command respects your choice and may overwrite the file.

## Troubleshooting

### "No workflow results found"

- Check that you're pointing to the correct directory
- Ensure directory contains folders starting with `wf_`
- Verify workflows completed successfully

### "Directory does not exist"

- Provide full path or correct relative path
- Default looks for `Descriptions` directory relative to current location

### Missing metadata

- Workflows without `workflow_metadata.json` will have parsed names
- Consider re-running with current version to get full metadata

### Description count shows as 0

- Workflow may not have completed successfully
- Check `logs/status.log` in the workflow directory for errors
- Verify `descriptions/image_descriptions.txt` exists and has content
