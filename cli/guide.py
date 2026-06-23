"""
idt guideme — interactive wizard for building and running describe commands.

Screen-reader-first design:
  - Numbered choices, no Unicode art, no ANSI
  - Every question readable as plain text
  - 'b' goes back one step, 'e' exits cleanly
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Optional

_here = Path(__file__).parent.parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


# ------------------------------------------------------------------ #
# UI primitives                                                        #
# ------------------------------------------------------------------ #

def _header(text: str) -> None:
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)
    print()


def get_choice(
    prompt: str,
    options: list[str],
    default: Optional[int] = None,
    allow_back: bool = False,
) -> str:
    """
    Print a numbered list and wait for a valid choice.
    Returns the chosen string, 'BACK', or 'EXIT'.
    """
    print(prompt)
    for i, opt in enumerate(options, 1):
        marker = " (default)" if default == i else ""
        print(f"  {i}. {opt}{marker}")
    print()

    nav = []
    if allow_back:
        nav.append("b=back")
    nav.append("e=exit")
    nav_str = ", ".join(nav)
    range_str = f"1-{len(options)}"
    if default:
        prompt_str = f"Enter choice ({range_str}, {nav_str}, default={default}): "
    else:
        prompt_str = f"Enter choice ({range_str}, {nav_str}): "

    while True:
        raw = input(prompt_str).strip().lower()
        if not raw and default:
            return options[default - 1]
        if raw == "b" and allow_back:
            return "BACK"
        if raw == "e":
            return "EXIT"
        try:
            n = int(raw)
            if 1 <= n <= len(options):
                return options[n - 1]
            print(f"Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print(f"Please enter a number, 'b' for back, or 'e' to exit.")


def get_input(prompt: str, default: str = "", allow_empty: bool = False) -> str:
    if default:
        full = f"{prompt} (default: {default}): "
    else:
        full = f"{prompt}: "
    while True:
        raw = input(full).strip()
        if raw:
            return raw
        if default:
            return default
        if allow_empty:
            return ""
        print("This field is required.")


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """
    Ask a yes/no question as a numbered choice, for consistency with the rest
    of the wizard (screen-reader-first: everything is numbered).
    Returns True for Yes, False for No.
    """
    default_idx = 1 if default else 2
    print(prompt)
    print(f"  1. Yes{' (default)' if default_idx == 1 else ''}")
    print(f"  2. No{' (default)' if default_idx == 2 else ''}")
    print()
    while True:
        raw = input(f"Enter choice (1-2, default={default_idx}): ").strip().lower()
        if not raw:
            return default
        if raw == "1":
            return True
        if raw == "2":
            return False
        print("Please enter 1 for Yes or 2 for No.")


def _fix_win_encoding() -> None:
    if sys.platform.startswith("win"):
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, io.TextIOWrapper):
                try:
                    stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass


# ------------------------------------------------------------------ #
# Step helpers                                                         #
# ------------------------------------------------------------------ #

def _step_provider() -> str:
    _header("Step 1: AI Provider")
    print("Choose the AI provider to generate descriptions.")
    print("  ollama    - Local models on your machine (no API key)")
    print("  anthropic - Claude (requires ANTHROPIC_API_KEY)")
    print("  openai    - GPT-4o (requires OPENAI_API_KEY)")
    print("  florence  - Microsoft Florence-2 local model (no API key, GPU recommended)")
    print()
    providers = ["ollama", "anthropic", "openai", "florence"]
    choice = get_choice("Which provider?", providers, default=1)
    return choice


def _step_api_key(provider: str) -> bool:
    """
    Check API key availability. Returns True if key is present, False if missing.
    Warns but does not block — user can proceed without a key if they know what they're doing.
    """
    import os
    _header(f"Step 2: API Key — {provider.upper()}")

    env_var = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider)

    if not env_var:
        print(f"No API key required for {provider}.")
        return True

    if os.environ.get(env_var):
        val = os.environ[env_var]
        masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
        print(f"Found {env_var}: {masked}")
        return True

    print(f"Warning: {env_var} is not set.")
    print()
    print("Set it before running the command:")
    if sys.platform.startswith("win"):
        print(f'  $env:{env_var} = "your-key-here"')
    else:
        print(f'  export {env_var}="your-key-here"')
    print()
    cont = get_yes_no("Continue anyway?", default=False)
    return cont


def _ollama_pull(model: str) -> bool:
    """Pull an Ollama model, streaming progress to stdout. Returns True on success."""
    import subprocess
    print(f"Pulling {model} from Ollama (this may take a few minutes)...")
    print()
    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            check=False,
        )
        if result.returncode == 0:
            print(f"\nModel {model!r} is ready.")
            return True
        else:
            print(f"\nollama pull returned exit code {result.returncode}.")
            return False
    except FileNotFoundError:
        print("Could not find 'ollama' on PATH.")
        return False
    except Exception as exc:
        print(f"Pull failed: {exc}")
        return False


def _ensure_ollama_model(model: str, installed: list[str]) -> bool:
    """
    Check if *model* is in the installed list. If not, offer to pull it.
    Returns True if the model is ready (already installed or successfully pulled),
    False if the user declined or the pull failed.
    """
    # Normalize: strip tag for comparison
    base = model.split(":")[0]
    for m in installed:
        if m == model or m.split(":")[0] == base:
            return True  # already installed

    print()
    print(f"Model '{model}' is not currently installed in Ollama.")
    pull = get_yes_no(f"Pull '{model}' now?", default=True)
    if not pull:
        print("Skipping pull. The run will fail if the model is not available.")
        return False
    return _ollama_pull(model)


def _step_model(provider: str) -> str:
    _header("Step 3: Model")

    if provider == "ollama":
        print("Checking available Ollama models...")
        try:
            from idt_core.providers.ollama import OllamaProvider, DEFAULT_MODEL
            inst = OllamaProvider(model=DEFAULT_MODEL)
            installed = inst.list_models()
        except Exception:
            installed = []

        if installed:
            print(f"Found {len(installed)} installed model(s).")
            print()
            choice = get_choice("Select a model", installed, default=1, allow_back=True)
            if choice in ("BACK", "EXIT"):
                return choice
        else:
            print("No models found or Ollama is not running.")
            print("Common vision-capable models: minicpm-v4.6, llava, qwen2-vl:7b, moondream")
            from idt_core.config import DEFAULT_OLLAMA_MODEL
            choice = get_input("Enter model name", default=DEFAULT_OLLAMA_MODEL)

        _ensure_ollama_model(choice, installed)
        return choice

    if provider == "anthropic":
        from idt_core.providers.claude import CLAUDE_MODELS
        print("Available Claude models:")
        choice = get_choice("Select a model", CLAUDE_MODELS, default=1, allow_back=True)
        if choice in ("BACK", "EXIT"):
            return choice
        return choice

    if provider == "openai":
        from idt_core.providers.openai_provider import OPENAI_MODELS
        print("Available OpenAI models:")
        choice = get_choice("Select a model", OPENAI_MODELS, default=1, allow_back=True)
        if choice in ("BACK", "EXIT"):
            return choice
        return choice

    if provider == "florence":
        models = [
            "microsoft/Florence-2-base (230 MB, faster)",
            "microsoft/Florence-2-large (700 MB, better quality)",
        ]
        choice = get_choice("Select a Florence-2 model", models, default=1, allow_back=True)
        if choice in ("BACK", "EXIT"):
            return choice
        return choice.split()[0]  # strip description

    return get_input("Enter model name")


def _step_source() -> tuple[str, str]:
    """
    Returns (source_type, source_value) where source_type is 'dir' or 'url'.
    """
    _header("Step 4: Image Source")
    print("You can describe images in a local folder, or download and describe")
    print("images from a web page.")
    print()
    source_type = get_choice(
        "What is your image source?",
        ["Local folder", "Web page URL"],
        default=1,
        allow_back=True,
    )
    if source_type in ("BACK", "EXIT"):
        return source_type, ""

    if "URL" in source_type:
        url = get_input("Enter the URL")
        return "url", url

    # Local folder
    while True:
        path_str = get_input("Enter path to image folder")
        p = Path(path_str)
        if not p.exists():
            print(f"Not found: {p}")
            if not get_yes_no("Try again?"):
                return "EXIT", ""
            continue
        if not p.is_dir():
            print(f"That is not a directory: {p}")
            if not get_yes_no("Try again?"):
                return "EXIT", ""
            continue
        # Check for images and videos
        from idt_core.scanner import scan_images
        from idt_core.video import scan_videos
        try:
            first_img = next(scan_images(p))
            print(f"Found images (e.g. {first_img.name})")
        except StopIteration:
            first_img = None

        try:
            first_vid = next(scan_videos(p))
            print(f"Found videos (e.g. {first_vid.name}) — frames will be extracted automatically")
        except StopIteration:
            first_vid = None

        if first_img is None and first_vid is None:
            print("No image or video files found in that folder.")
            if not get_yes_no("Use it anyway?", default=False):
                continue
        return "dir", str(p)


def _step_prompt() -> tuple[str, str]:
    """Returns (prompt_name, prompt_text)."""
    _header("Step 5: Prompt Style")

    from idt_core.config import UserConfig, BUILT_IN_PROMPTS
    user_cfg = UserConfig.load()
    all_prompts = user_cfg.list_prompts()
    names = list(all_prompts.keys())

    print("Available prompts:")
    print()
    for name in names:
        text = all_prompts[name]
        preview = text[:80] + ("..." if len(text) > 80 else "")
        print(f"  {name}")
        print(f"    {preview}")
        print()

    default_name = user_cfg.default_prompt_name or "detailed"
    default_idx = names.index(default_name) + 1 if default_name in names else 1

    choice = get_choice(
        "Select a prompt style",
        names,
        default=default_idx,
        allow_back=True,
    )
    if choice in ("BACK", "EXIT"):
        return choice, ""

    return choice, all_prompts[choice]


def _step_metadata() -> tuple[bool, bool]:
    """Returns (extract_metadata, geocode)."""
    _header("Step 6: Metadata Options")

    print("IDT can read EXIF data from your images (date taken, camera, GPS)")
    print("and inject it into the AI prompt as context.")
    print()
    print('Example: "Context: Munich, Germany  Sep 12, 2025  iPhone 14 Pro"')
    print("This significantly improves description quality for photos with EXIF.")
    print()

    extract = get_yes_no("Enable EXIF metadata extraction?", default=True)
    if not extract:
        return False, False

    print()
    print("Geocoding converts GPS coordinates to a city/state/country name.")
    print("It requires internet access and adds about 1 second per unique location.")
    print("Results are cached so each location is only looked up once.")
    print()

    geocode = get_yes_no("Enable reverse geocoding?", default=False)
    return True, geocode


def _step_extra_options(source_type: str) -> dict:
    """Return dict of extra flags: limit, show_descriptions, embed, redescribe."""
    _header("Step 7: Additional Options")
    opts: dict = {}

    limit_str = get_input(
        "Limit to N images (useful for testing; press Enter for all)",
        allow_empty=True,
    )
    if limit_str:
        try:
            opts["limit"] = int(limit_str)
        except ValueError:
            print("Invalid number, no limit will be set.")

    opts["show_descriptions"] = get_yes_no(
        "Print each description to the screen as it is generated?", default=False
    )

    if source_type == "dir":
        opts["redescribe"] = get_yes_no(
            "Re-describe images that already have descriptions?", default=False
        )
        opts["embed"] = get_yes_no(
            "Embed descriptions into image copies after describing?", default=False
        )
    elif source_type == "url":
        opts["embed"] = get_yes_no(
            "Embed descriptions into downloaded image copies after describing?",
            default=False,
        )

    return opts


# ------------------------------------------------------------------ #
# Command builder                                                      #
# ------------------------------------------------------------------ #

def _build_command(
    source_type: str,
    source: str,
    provider: str,
    model: str,
    prompt_name: str,
    extract_metadata: bool,
    geocode: bool,
    extra: dict,
) -> list[str]:
    parts = ["idt"]

    if source_type == "url":
        parts += ["download", source, "--describe"]
        if extra.get("embed"):
            parts.append("--embed")
        parts += ["--provider", provider, "--model", model, "--prompt", prompt_name]
        if extra.get("limit"):
            parts += ["--max", str(extra["limit"])]
    else:
        parts += ["describe", source]
        parts += ["--provider", provider, "--model", model]
        parts += ["--prompt", prompt_name]
        if not extract_metadata:
            parts.append("--no-metadata")
        if geocode:
            parts.append("--geocode")
        if extra.get("limit"):
            parts += ["--limit", str(extra["limit"])]
        if extra.get("show_descriptions"):
            parts.append("--show-descriptions")
        if extra.get("redescribe"):
            parts.append("--redescribe")
        if extra.get("embed"):
            parts.append("--embed")

    return parts


def _format_command(parts: list[str]) -> str:
    out = []
    for p in parts:
        if " " in p or not p:
            out.append(f'"{p}"')
        else:
            out.append(p)
    return " ".join(out)


# ------------------------------------------------------------------ #
# Main wizard loop                                                     #
# ------------------------------------------------------------------ #

def run_guide() -> None:
    _fix_win_encoding()

    _header("Image Description Toolkit — Guided Setup")
    print("This wizard helps you describe a folder of images or download and")
    print("describe images from a web page.")
    print()
    print("At each step: enter a number to choose, 'b' to go back, 'e' to exit.")
    print("Press Ctrl+C at any time to quit.")
    print()

    # State machine: steps 1-7, each can go back
    step = 1
    state: dict = {}

    while True:
        try:
            if step == 1:
                result = _step_provider()
                if result == "EXIT":
                    print("Exiting.")
                    return
                state["provider"] = result
                step = 2

            elif step == 2:
                ok = _step_api_key(state["provider"])
                if not ok:
                    print("Exiting.")
                    return
                step = 3

            elif step == 3:
                result = _step_model(state["provider"])
                if result == "EXIT":
                    print("Exiting.")
                    return
                if result == "BACK":
                    step = 1
                    continue
                state["model"] = result
                step = 4

            elif step == 4:
                src_type, src_val = _step_source()
                if src_type == "EXIT":
                    print("Exiting.")
                    return
                if src_type == "BACK":
                    step = 3
                    continue
                state["source_type"] = src_type
                state["source"] = src_val
                step = 5

            elif step == 5:
                pname, ptext = _step_prompt()
                if pname == "EXIT":
                    print("Exiting.")
                    return
                if pname == "BACK":
                    step = 4
                    continue
                state["prompt_name"] = pname
                state["prompt_text"] = ptext
                step = 6

            elif step == 6:
                state["extract_metadata"], state["geocode"] = _step_metadata()
                step = 7

            elif step == 7:
                state["extra"] = _step_extra_options(state["source_type"])

                # Build and show the command
                cmd_parts = _build_command(
                    source_type=state["source_type"],
                    source=state["source"],
                    provider=state["provider"],
                    model=state["model"],
                    prompt_name=state["prompt_name"],
                    extract_metadata=state["extract_metadata"],
                    geocode=state["geocode"],
                    extra=state["extra"],
                )
                cmd_str = _format_command(cmd_parts)

                _header("Command Summary")
                print("Provider:   ", state["provider"])
                print("Model:      ", state["model"])
                print("Source:     ", state["source"])
                print("Prompt:     ", state["prompt_name"])
                meta_str = "yes" if state["extract_metadata"] else "no"
                if state["extract_metadata"] and state["geocode"]:
                    meta_str += " + geocoding"
                print("Metadata:   ", meta_str)
                if state["extra"].get("limit"):
                    print("Limit:      ", state["extra"]["limit"], "images")
                print()
                print("Command to run:")
                print()
                print(f"  {cmd_str}")
                print()

                action = get_choice(
                    "What would you like to do?",
                    [
                        "Run this command now",
                        "Copy command (just print it) and exit",
                        "Go back and change settings",
                    ],
                    default=1,
                    allow_back=False,
                )

                if action == "EXIT":
                    print("Exiting.")
                    return

                if action == "Copy command (just print it) and exit":
                    print()
                    print("Run this command:")
                    print()
                    print(f"  {cmd_str}")
                    print()
                    return

                if "back" in action.lower() or "change" in action.lower():
                    step = 1
                    state = {}
                    continue

                # Run it
                _header("Running")
                print(f"  {cmd_str}")
                print()
                _run_command(cmd_parts, state)
                return

        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return


def _offer_open_report(source_str: str) -> None:
    """After a describe run, find the HTML report and offer to open it."""
    import os
    from cli.main import _mirror_source_path
    from idt_core.config import UserConfig

    source = Path(source_str).resolve()
    root = UserConfig.load().workspace_root_path()
    ws_path = _mirror_source_path(source, root).with_suffix(".idtw")
    html_path = ws_path / "reports" / "descriptions.html"
    if not html_path.exists():
        return
    print()
    open_it = get_yes_no("Open the description report in your browser?", default=True)
    if not open_it:
        print(f"Report is at: {html_path}")
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(html_path))
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", str(html_path)], check=False)
        else:
            import subprocess
            subprocess.run(["xdg-open", str(html_path)], check=False)
    except Exception as exc:
        print(f"Could not open browser automatically: {exc}")
        print(f"Report is at: {html_path}")


def _run_command(parts: list[str], state: dict) -> None:
    """Execute the built command by directly calling the CLI handlers."""
    # Import here to avoid circular import
    from cli.main import (
        cmd_describe,
        cmd_download,
        _make_provider,
        _resolve_prompt,
    )
    import argparse

    # Build a minimal args namespace that matches what the handlers expect
    src_type = state["source_type"]
    extra = state.get("extra", {})

    if src_type == "url":
        from cli.main import cmd_download
        import types
        args = types.SimpleNamespace(
            url=state["source"],
            directory=None,
            max_images=extra.get("limit"),
            min_size=None,
            timeout=30,
            describe=True,
            embed=extra.get("embed", False),
            provider=state["provider"],
            model=state["model"],
            ollama_host="http://localhost:11434",
            prompt=state["prompt_name"],
            prompt_text=None,
            quiet=False,
        )
        cmd_download(args)
    else:
        import types
        args = types.SimpleNamespace(
            source=state["source"],
            stdin=False,
            project=None,
            provider=state["provider"],
            model=state["model"],
            ollama_host="http://localhost:11434",
            prompt=state["prompt_name"],
            prompt_text=None,
            extract_metadata=state["extract_metadata"],
            geocode=state["geocode"],
            redescribe=extra.get("redescribe", False),
            limit=extra.get("limit"),
            show_descriptions=extra.get("show_descriptions", False),
            embed=extra.get("embed", False),
            no_video=False,
            video_interval=5.0,
            no_export=False,
            quiet=False,
            _command_parts=parts,  # full command for workspace manifest logging
        )
        cmd_describe(args)
        _offer_open_report(state["source"])
