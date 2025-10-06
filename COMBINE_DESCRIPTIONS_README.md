# Workflow Description Combiner

## Overview

The `combine_workflow_descriptions.py` script combines image descriptions from multiple workflow directories into a single text file for easy comparison.

**Note:** The file uses `@` as the column delimiter (instead of comma) for better Excel compatibility.

**Output File:** `combineddescriptions.txt`

## What It Does

- Scans all `wf_*` directories in the project root
- Parses each workflow's `descriptions/image_descriptions.txt` file
- Creates a CSV file with `@` delimiter:
  - **Column 1**: Image Name (normalized filename)
  - **Columns 2-6**: Descriptions from each workflow (Claude Haiku, Claude Sonnet, Ollama LLaVA, ONNX LLaVA, OpenAI GPT-4o-mini)
- **Row Order**: Preserves the processing order from the first workflow (typically chronological by file modification time)

## Usage

Simply run the script from the project root:

```bash
python combine_workflow_descriptions.py
```

This will create `combined_workflow_descriptions.csv` in the project root.

## Output

The text file contains:
- **1,805 rows** (1 header + 1,804 images)
- **6 columns** (Image Name + 5 workflow descriptions)
- **Filename:** `combineddescriptions.txt`
- **Format:** Text file with `@` delimiter (can be imported as CSV)

### Current Coverage (as of run):

| Workflow | Images Completed | Coverage |
|----------|-----------------|----------|
| Claude Haiku | 1,804 | 100.0% |
| Claude Sonnet | 1,804 | 100.0% |
| Ollama LLaVA | 1,105 | 61.3% |
| ONNX LLaVA | 894 | 49.6% |
| OpenAI GPT-4o-mini | 1,804 | 100.0% |

## Re-running

You can re-run the script at any time to update the CSV with newly completed descriptions. The script will:
- Parse all workflow directories again
- Include any new descriptions that have been generated
- Overwrite the previous CSV file

## CSV Format

The file uses **`@` as the delimiter** instead of commas for better Excel compatibility.

### Example Format:

```
Image Name@Claude Haiku@Claude Sonnet@Ollama LLaVA@Onnx LLaVA@Openai GPT-4o-mini
IMG_3136.jpg@Description from Claude Haiku...@Description from Claude Sonnet...@Description from Ollama...@Description from ONNX...@Description from OpenAI...
```

### Importing into Excel:

1. Open Excel
2. Go to **Data → Get Data → From File → From Text/CSV**
3. Select `combineddescriptions.txt`
4. In the import dialog:
   - Change **Delimiter** from "Comma" to **"Other"**
   - Enter `@` in the "Other" field
   - Set **File Origin** to "UTF-8"
5. Click **Load**

Alternatively, if Excel prompts you to choose delimiter:
- Select **"Delimited"**
- Click **Next**
- Uncheck "Comma", check **"Other"** and enter `@`
- Click **Finish**

### Notes:

- Empty cells indicate the workflow hasn't processed that image yet
- All descriptions are on a single line (multi-line descriptions are joined with spaces)
- CSV is UTF-8 encoded to support all characters
- The `@` delimiter was chosen because it doesn't appear in any image descriptions

## Files

- **Input**: `wf_*/descriptions/image_descriptions.txt` (from each workflow directory)
- **Output**: `combined_workflow_descriptions.csv` (in project root)
- **Script**: `combine_workflow_descriptions.py`

## Notes

- The script automatically detects all workflow directories matching the pattern `wf_*`
- Image names are normalized (just the filename, regardless of subdirectory in the workflow)
- The script handles video frames and converted images (e.g., HEIC→JPEG conversions)
- Workflow labels are extracted from directory names for readable column headers
- **Row order**: Images are listed in the order they were processed in the first workflow (usually chronological by file date, oldest first)
- If any images appear in other workflows but not the first, they are added at the end in alphabetical order
