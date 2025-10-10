See the next section for a full list of available prompt styles and what they do.

### Available Prompt Styles

| Style Name | Description |
|------------|-------------|
| detailed   | Describe this image in detail, including: Main subjects/objects, Setting/environment, Key colors and lighting, Notable activities or composition. Keep it comprehensive and informative for metadata. |
| concise    | Describe this image concisely, including: Main subjects/objects, Setting/environment, Key colors and lighting, Notable activities or composition. |
| narrative  | Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe. |
| artistic   | Analyze this image from an artistic perspective, describing: Visual composition and framing, Color palette and lighting mood, Artistic style or technique, Emotional tone or atmosphere, Subject matter and symbolism |
| technical  | Provide a technical analysis of this image: Camera settings and photographic technique, Lighting conditions and quality, Composition and framing, Image quality and clarity, Technical strengths or weaknesses |
| colorful   | Give me a rich, vivid description emphasizing colors, lighting, and visual atmosphere. Focus on the palette, color relationships, and how colors contribute to the mood and composition. |
| Simple     | Describe. |

> **Tip:** You can add your own custom styles by editing `scripts/image_describer_config.json`.

# Image Description Toolkit (IDT) - User Guide

## Overview
The Image Description Toolkit (IDT) is a powerful, AI-driven tool for generating natural language descriptions from images and videos. It supports both local (Ollama, ONNX) and cloud (OpenAI, Claude) AI providers, and is distributed as a standalone Windows executable—no Python installation required.

---

## Prompt Customization: Make It Your Own

IDT lets you control the *style* and *focus* of your image descriptions using **prompt styles**. Prompt customization is the easiest and most powerful way to tailor results to your needs—often more important than model selection!

**How to use prompt styles:**

- By default, IDT uses the `narrative` style, which gives a detailed, objective description.
- To choose a different style, add `--prompt-style STYLE_NAME` to your command. For example:
  ```
  idt.exe C:\Photos --prompt-style artistic
  ```
- You can also use batch files with a prompt style, e.g.:
  ```
  bat\run_ollama_llava7b.bat C:\Photos --prompt-style technical
  ```

**Why customize prompts?**

- Get concise, technical, artistic, or color-focused descriptions—whatever fits your project.
- Prompt style changes the *tone*, *detail*, and *focus* of the output, not just the length.

See the next section for a full list of available prompt styles and what they do.


## 1. Installation & Setup

### Step 1: Download & Extract
- Download the latest `ImageDescriptionToolkit_v[VERSION].zip` from GitHub Releases.
- Extract to a folder of your choice (e.g., `C:\IDT\`).

### Step 2: Install Ollama (for local models)
- Download Ollama from [https://ollama.ai/download/windows](https://ollama.ai/download/windows) or use `winget install Ollama.Ollama`.
- Run `ollama serve` to start the Ollama service.

### Step 3: Download the Moondream Model (Golden Path)
- Open a terminal and run:
  ```
  ollama pull moondream
  ```

---

## 2. The Simplest Use Case (Golden Path)

1. Put some images in a directory (e.g., `C:\Photos\`).
2. Open a terminal in the extracted folder.
3. Run:
   ```
   idt.exe C:\Photos
   ```
   (or `./idt.exe <your imagepath>`)
4. Results will appear in the `Descriptions/` folder. That's it!

> **Note:** This works out-of-the-box as long as you have downloaded the `moondream` model. No extra steps, flags, or configuration are needed for the default workflow.

---

## 3. Advanced Usage: Custom Steps & Models

You can specify advanced options, run individual workflow steps, or use other models/providers. For example:

```
idt.exe workflow C:\Photos --steps describe,html --model llava:7b
```

Or use the provided `.bat` files in the `bat/` directory for one-click runs with specific models:

```
bat\run_ollama_llava7b.bat C:\Photos
```

See the rest of this guide for cloud setup, configuration, and analysis features.

---

## 2. Running Your First Workflow

### Option 1: Using the Executable
- Place your images (or videos) in a folder (e.g., `C:\Photos\`).
- Open a terminal in the extracted folder.
- Run:
  ```
  idt.exe workflow C:\Photos --steps describe,html
  ```
- Results will appear in the `Descriptions/` folder. Open the generated HTML report for a visual summary.

### Option 2: Using Batch Files
- Use the provided `.bat` files in the `bat/` directory for one-click runs with specific models.
- Example:
  ```
  bat\run_ollama_llava7b.bat C:\Photos
  ```
- Each batch file targets a different model/provider and sets recommended options.

---

## 3. Cloud Provider Setup (OpenAI & Claude)

### OpenAI
- Get your API key from https://platform.openai.com/api-keys
- Set it in your terminal:
  ```
  set OPENAI_API_KEY=sk-...
  ```
- Or use the batch file `bat\setup_openai_key.bat` with a key file.

### Claude (Anthropic)
- Get your API key from https://console.anthropic.com/
- Set it in your terminal:
  ```
  set ANTHROPIC_API_KEY=sk-ant-...
  ```
- Or use the batch file `bat\setup_claude_key.bat` with a key file.

---

## 4. Configuration & Customization

- To override prompts, model defaults, or workflow settings, edit `scripts/image_describer_config.json` or place a custom `image_describer_config.json` next to the EXE.
- You can also set the environment variable:
  ```
  set IDT_IMAGE_DESCRIBER_CONFIG=C:\path\to\custom.json
  ```
- See `docs/CONFIG_OVERRIDES.md` for advanced configuration layering.

---

## 5. Analysis & Reporting

- Use the analysis scripts (via CLI or batch files) to generate statistics, review content, or combine descriptions:
  - `idt.exe stats` (workflow stats)
  - `idt.exe contentreview` (content analysis)
  - `idt.exe combinedescriptions` (merge results)
- Results are saved in the `analysis/` directory.

---

## 6. Troubleshooting & FAQ

- See `docs/EXECUTABLE_FAQ.md` and `docs/EXECUTABLE_DISTRIBUTION_GUIDE.md` for common issues and solutions.
- For Ollama errors, ensure the service is running and models are downloaded.
- For cloud errors, check your API key and internet connection.
- For advanced usage, see the full documentation in the `docs/` directory.

---

## 7. Further Resources
- [Cloud Providers Guide](docs/CLOUD_PROVIDERS_GUIDE.md)
- [Token Tracking Guide](docs/TOKEN_TRACKING_GUIDE.md)
- [Distribution Guide](docs/DISTRIBUTION.md)
- [Quick Start](QUICK_START.md)
- [Batch File Examples](docs/archive/BATCH_FILES_GUIDE.md)

---

## Support
- For help, bug reports, or feature requests, visit the GitHub repository: https://github.com/kellylford/Image-Description-Toolkit
