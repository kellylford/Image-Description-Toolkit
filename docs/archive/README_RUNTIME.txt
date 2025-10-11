Image Description Toolkit - Runtime Quick Guide
================================================

This file is for end users running the packaged executable.

1. Requirements
   - Windows 10/11
   - Ollama installed & running (unless using cloud providers)
   - (Optional) OpenAI or Claude API key if using cloud models

2. Fast Start
   ImageDescriptionToolkit.exe workflow C:\media --steps describe,html
   Open newest workflow_output_*/reports/image_descriptions.html

3. Common Flags
   --steps describe,html          Only run specific stages
   --model llava:7b               Force model
   --prompt-style artistic        Override prompt style for this run
   --output-dir C:\results        Custom output root
   --verbose                      More logging detail

4. Prompt / Model Defaults
   Edit scripts\image_describer_config.json (shipped copy), OR place
   image_describer_config.json next to the EXE for higher precedence, OR set:
     set IDT_IMAGE_DESCRIBER_CONFIG=C:\cfg\custom.json
   Directory override:
     set IDT_CONFIG_DIR=D:\shared_configs

5. Style Precedence
   CLI --prompt-style  >  default_prompt_style in resolved config  > fallback (detailed)

6. Cloud Keys
   OpenAI:   set OPENAI_API_KEY=sk-...
   Claude:   set ANTHROPIC_API_KEY=sk-ant-...
   (or use --api-key-file path.txt)

7. Verifying Config Override
   1. Remove --prompt-style
   2. Run once
   3. Open descriptions/image_descriptions.txt
   4. Check header: Prompt style: <expected>
   5. Re-run with --prompt-style anotherStyle to see override

8. Typical Output Tree
   workflow_output_YYYYMMDD_HHMMSS/
     logs/ extracted_frames/ converted_images/ descriptions/ reports/

9. Troubleshooting
   No model found (Ollama)   -> ollama pull llava:7b
   Style not changing        -> Check config path / env vars
   API key error             -> Set env var or use --api-key-file
   No descriptions produced  -> Ensure 'describe' in --steps
   Slow first run            -> Normal (extraction); subsequent faster

10. Safe to Edit
   scripts\*.json configs (prompts, workflow, video settings)
   NOT the executable or temp extraction folders.

11. When to Rebuild
   Prompt or default change:  NO (config override)
   Add new prompt variation:  NO (edit JSON)
   New provider / logic code: YES (modify Python + rebuild)

12. Example Session
   set IDT_IMAGE_DESCRIBER_CONFIG=C:\deploy\bright_prompts.json
   ImageDescriptionToolkit.exe workflow C:\photos --steps describe,html
   ImageDescriptionToolkit.exe workflow C:\photos --steps describe --prompt-style technical

For full docs see docs\CONFIG_OVERRIDES.md and docs\DISTRIBUTION.md.
