#!/usr/bin/env python3
"""
idt — Image Description Toolkit

Usage:
  idt describe <directory> [options]
  idt status   <directory>
  idt show     <directory|image>
  idt embed    <directory> [options]
  idt export   <directory> [options]
  idt watch    <directory> [options]
  idt prompts
  idt config   [--set key=value]
  idt --help

Run "idt <command> --help" for command-specific options.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Allow running as "python cli/main.py" during development without installing
_here = Path(__file__).parent.parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


# ------------------------------------------------------------------ #
# Provider factory                                                     #
# ------------------------------------------------------------------ #

def _make_provider(provider: str, model: Optional[str], ollama_host: str):
    """Instantiate the requested provider, giving a clear error if deps are missing."""
    from idt_core.config import BUILT_IN_PROMPTS  # noqa: side-effect free import check

    if provider == "anthropic":
        from idt_core.providers.claude import ClaudeProvider, DEFAULT_MODEL
        return ClaudeProvider(model=model or DEFAULT_MODEL)

    if provider == "ollama":
        from idt_core.providers.ollama import OllamaProvider, DEFAULT_MODEL
        return OllamaProvider(model=model or DEFAULT_MODEL, host=ollama_host)

    if provider == "openai":
        from idt_core.providers.openai_provider import OpenAIProvider, DEFAULT_MODEL
        return OpenAIProvider(model=model or DEFAULT_MODEL)

    if provider == "florence":
        from idt_core.providers.florence import FlorenceProvider, DEFAULT_MODEL
        return FlorenceProvider(model=model or DEFAULT_MODEL)

    print(f"Unknown provider: {provider!r}", file=sys.stderr)
    print("Valid providers: anthropic, ollama, openai, florence", file=sys.stderr)
    sys.exit(1)


def _resolve_prompt(args, project_config) -> tuple[str, str]:
    """
    Return (prompt_name, prompt_text).
    Priority: --prompt-text > --prompt > project default > user config default.
    """
    from idt_core.config import UserConfig, BUILT_IN_PROMPTS

    if args.prompt_text:
        return ("custom", args.prompt_text)

    user_cfg = UserConfig.load()
    name = getattr(args, "prompt", None) or project_config.default_prompt_name or user_cfg.default_prompt_name
    text = user_cfg.get_prompt_text(name) or BUILT_IN_PROMPTS.get("detailed", "")
    return (name, text)


# ------------------------------------------------------------------ #
# Commands                                                             #
# ------------------------------------------------------------------ #

def cmd_describe(args):
    from idt_core.project import Project
    from idt_core.pipeline import Pipeline, RunOptions
    from idt_core.progress import Progress
    from idt_core.config import UserConfig

    # ---- stdin mode ----
    # idt describe - [--project <dir>]  or  some_cmd | idt describe --stdin
    stdin_mode = getattr(args, "stdin", False) or args.source == "-"

    if stdin_mode:
        _cmd_describe_stdin(args)
        return

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    project = Project.open(source)
    user_cfg = UserConfig.load()

    provider_name = args.provider or project.config.default_provider or user_cfg.default_provider
    model = args.model or project.config.default_model or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, project.config)

    if not args.quiet:
        print(f"Source:   {source}")
        print(f"Project:  {project.idt_dir}")
        print(f"Provider: {provider_name}  model: {model}")
        print(f"Prompt:   {prompt_name}")
        print()

    provider = _make_provider(provider_name, model, args.ollama_host)

    options = RunOptions(
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        redescribe=args.redescribe,
        limit=args.limit,
    )

    queue = list(
        project.items() if args.redescribe else project.undescribed()
    )
    if args.limit:
        queue = queue[: args.limit]

    if not queue:
        if not args.quiet:
            st = project.status()
            print(
                f"All {st['described']} image{'s are' if st['described'] != 1 else ' is'} "
                f"already described."
            )
            print("Use --redescribe to generate additional descriptions.")
        return

    progress = Progress(total=len(queue), quiet=args.quiet)
    progress.start(f"{provider_name} / {model}")

    described = errors = 0
    pipeline = Pipeline(project, provider)

    for event in pipeline.run(options):
        if event.success:
            described += 1
            progress.update(event.item.display_name, success=True)
        else:
            errors += 1
            progress.update(event.item.display_name, success=False, error=event.error)

    progress.summary(described=described, errors=errors)


def _cmd_describe_stdin(args):
    """
    Describe a list of image paths read from stdin, one per line.
    All images must share a common ancestor directory (the project root).
    Use --project to specify where the .idt/ mirror should live if paths
    don't share an obvious common root.

    Pipeline use case:
      get_nyt_images.sh | idt describe - --prompt news --provider anthropic
    """
    from idt_core.project import Project
    from idt_core.image_item import ImageItem
    from idt_core.pipeline import Pipeline, RunOptions, PipelineEvent
    from idt_core.progress import Progress
    from idt_core.config import UserConfig
    from idt_core.converter import load_for_api
    from idt_core.image_item import Description

    paths = [
        Path(line.strip()).resolve()
        for line in sys.stdin
        if line.strip() and not line.startswith("#")
    ]
    if not paths:
        print("No image paths received on stdin.", file=sys.stderr)
        sys.exit(1)

    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"Warning: not found: {p}", file=sys.stderr)
        paths = [p for p in paths if p.exists()]
        if not paths:
            sys.exit(1)

    # Determine project root: explicit --project, or common ancestor of all paths
    if getattr(args, "project", None):
        source = Path(args.project).resolve()
    else:
        source = _common_ancestor(paths)

    project = Project.open(source)
    user_cfg = UserConfig.load()

    provider_name = args.provider or project.config.default_provider or user_cfg.default_provider
    model = args.model or project.config.default_model or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, project.config)
    provider = _make_provider(provider_name, model, args.ollama_host)

    if not args.quiet:
        print(f"Project:  {project.idt_dir}")
        print(f"Provider: {provider_name}  model: {model}")
        print(f"Images:   {len(paths)} from stdin")
        print()

    progress = Progress(total=len(paths), quiet=args.quiet)
    described = errors = 0

    for img_path in paths:
        # Build or load the ImageItem for this specific file
        try:
            rel = img_path.relative_to(source)
        except ValueError:
            print(f"Warning: {img_path} is outside project root {source} — skipping", file=sys.stderr)
            continue

        sidecar = project.sidecar_path(img_path)
        if sidecar.exists():
            item = ImageItem.load(sidecar)
        else:
            item = ImageItem(source_path=img_path, sidecar_path=sidecar)

        if item.described and not args.redescribe:
            progress.skip(img_path.name, "already described")
            continue

        try:
            image_bytes, mime_type = load_for_api(img_path)
            result = provider.describe(image_bytes, mime_type, prompt_text)
            desc = Description.create(
                text=result.text,
                model=result.model,
                provider=result.provider,
                prompt_name=prompt_name,
                prompt_text=prompt_text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            item.add_description(desc)
            item.save()
            described += 1
            progress.update(img_path.name, success=True)

            # In quiet mode, print filename TAB description for piping
            if args.quiet:
                print(f"{img_path}\t{result.text}")

        except Exception as exc:
            errors += 1
            progress.update(img_path.name, success=False, error=str(exc))

    progress.summary(described=described, errors=errors)


def _common_ancestor(paths: list[Path]) -> Path:
    """Return the deepest common directory ancestor of a list of paths."""
    if not paths:
        raise ValueError("No paths given")
    if len(paths) == 1:
        return paths[0].parent
    common = paths[0].parent
    for p in paths[1:]:
        while common != p and not str(p).startswith(str(common)):
            common = common.parent
    return common


def cmd_status(args):
    from idt_core.project import Project

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    project = Project.open(source)
    st = project.status()

    if args.json_out:
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return

    pct = int(st["described"] / st["total"] * 100) if st["total"] else 0

    print(f"Source:      {st['source']}")
    print(f"Project:     {st['idt_dir']}")
    print(f"Total:       {st['total']}")
    print(f"Described:   {st['described']}  ({pct}%)")
    print(f"Remaining:   {st['undescribed']}")
    if st["last_run"]:
        # Convert ISO timestamp to readable local form
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(st["last_run"]).astimezone()
            hour = dt.hour % 12 or 12
            ampm = "A" if dt.hour < 12 else "P"
            last = f"{dt.month}/{dt.day}/{dt.year} {hour}:{dt.minute:02d}{ampm}"
        except Exception:
            last = st["last_run"]
        print(f"Last run:    {last}")


def cmd_show(args):
    from idt_core.project import Project
    from idt_core.image_item import ImageItem

    target = Path(args.target).resolve()

    if target.is_file():
        _show_file(target, args)
    elif target.is_dir():
        _show_directory(target, args)
    else:
        print(f"Error: not found: {target}", file=sys.stderr)
        sys.exit(1)


def _show_file(target: Path, args):
    from idt_core.project import Project
    from idt_core.image_item import ImageItem

    # Walk up to find the source directory that has a matching .idt/ mirror
    candidate = target.parent
    while True:
        idt_dir = candidate.parent / (candidate.name + ".idt")
        if idt_dir.is_dir():
            project = Project.open(candidate)
            sidecar = project.sidecar_path(target)
            if sidecar.exists():
                item = ImageItem.load(sidecar)
                _print_item(item, args)
                return
        if candidate == candidate.parent:
            break
        candidate = candidate.parent

    if not args.quiet:
        print(f"No description found for: {target.name}", file=sys.stderr)
    sys.exit(1)


def _show_directory(target: Path, args):
    from idt_core.project import Project

    project = Project.open(target)
    items = list(project.described())
    if not items:
        if not args.quiet:
            print("No described images in this project yet.")
            print(f"Run:  idt describe {target}")
        return

    for item in items:
        _print_item(item, args)
        if not args.json_out:
            print()


def _print_item(item, args):
    from idt_core.image_item import ImageItem

    desc = item.active_description
    if args.json_out:
        out = {
            "file": item.display_name,
            "source": str(item.source_path),
            "described": item.described,
            "description": desc.text if desc else None,
            "model": desc.model if desc else None,
            "provider": desc.provider if desc else None,
            "timestamp": desc.timestamp if desc else None,
        }
        print(json.dumps(out, ensure_ascii=False))
        return

    if not desc:
        print(f"{item.display_name}: not described")
        return

    print(f"File:      {item.display_name}")
    print(f"Model:     {desc.model}  ({desc.provider})")
    print(f"Date:      {desc.timestamp[:10]}")
    if desc.output_tokens:
        print(f"Tokens:    {desc.output_tokens} out")
    print()
    print(desc.text)


def cmd_prompts(args):
    from idt_core.config import UserConfig, BUILT_IN_PROMPTS

    user_cfg = UserConfig.load()
    all_prompts = user_cfg.list_prompts()

    if args.json_out:
        print(json.dumps(all_prompts, indent=2, ensure_ascii=False))
        return

    print("Available prompts:\n")
    for name, text in all_prompts.items():
        marker = " (custom)" if name in user_cfg.custom_prompts else ""
        print(f"  {name}{marker}")
        # Show first 80 chars of prompt text as a preview
        preview = text[:80] + ("..." if len(text) > 80 else "")
        print(f"    {preview}")
        print()


def cmd_embed(args):
    from idt_core.project import Project
    from idt_core.embedder import Embedder

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    project = Project.open(source)
    embedder = Embedder(project)

    described = list(project.described())
    if not described:
        print("No described images found. Run 'idt describe' first.")
        return

    if not args.quiet:
        pending = [i for i in described if args.force or not i.embedded_at]
        already = len(described) - len(pending)
        print(f"Source:    {source}")
        print(f"Output:    {project.idt_dir / 'embedded'}")
        print(f"To embed:  {len(pending)}")
        if already:
            print(f"Already embedded (skipping): {already}  (use --force to re-embed)")
        if args.dry_run:
            print("\nDry run — no files will be written.")
        print()

    result = embedder.embed_all(force=args.force, dry_run=args.dry_run)

    if not args.quiet:
        for path in result.embedded:
            verb = "would embed" if args.dry_run else "embedded"
            print(f"  {verb}: {path.name}")
        for path, reason in result.skipped:
            if not reason.startswith("already"):
                print(f"  skipped: {path.name}  ({reason})")
        for path, msg in result.errors:
            print(f"  error: {path.name}  {msg}", file=sys.stderr)
        print()

    n = len(result.embedded)
    verb = "Would embed" if args.dry_run else "Embedded"
    print(f"{verb} {n} image{'s' if n != 1 else ''}.", end="")
    if result.errors:
        print(f"  {len(result.errors)} error(s).", end="")
    print()

    if not args.dry_run and not args.quiet and n > 0:
        print(f"\nEmbedded copies: {project.idt_dir / 'embedded'}")


def cmd_export(args):
    from idt_core.project import Project
    from idt_core.exporter import export_html, export_csv, export_txt

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    project = Project.open(source)
    fmt = args.format

    try:
        if fmt == "html":
            out = export_html(project)
        elif fmt == "csv":
            out = export_csv(project)
        elif fmt == "txt":
            out = export_txt(project)
        else:
            print(f"Unknown format: {fmt!r}", file=sys.stderr)
            sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"Exported {fmt.upper()}: {out}")
    else:
        print(str(out))


def cmd_watch(args):
    from idt_core.project import Project
    from idt_core.watcher import Watcher, WatchOptions
    from idt_core.config import UserConfig

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    project = Project.open(source)
    user_cfg = UserConfig.load()

    provider_name = args.provider or project.config.default_provider or user_cfg.default_provider
    model = args.model or project.config.default_model or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, project.config)
    provider = _make_provider(provider_name, model, args.ollama_host)

    if not args.quiet:
        print(f"Watching: {source}")
        print(f"Provider: {provider_name}  model: {model}")
        print(f"Interval: {args.interval}s  prompt: {prompt_name}")
        print("Press Ctrl+C to stop.\n")

    def _on_poll(remaining: int) -> None:
        if not args.quiet and remaining % 30 == 0:
            print(f"  ... next scan in {remaining}s", flush=True)

    options = WatchOptions(
        interval_seconds=args.interval,
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        on_poll=_on_poll,
    )

    watcher = Watcher(project, provider, options)
    try:
        for event in watcher.run():
            if event.success:
                desc = event.item.active_description
                if not args.quiet:
                    print(f"Described: {event.item.display_name}")
                    if desc:
                        print(f"  {desc.text[:120]}{'...' if len(desc.text) > 120 else ''}")
                        print()
                else:
                    # --quiet: print just the filename and description for piping
                    if desc:
                        print(f"{event.item.display_name}\t{desc.text}")
            else:
                print(f"Error: {event.item.display_name}: {event.error}", file=sys.stderr)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nWatcher stopped.")


def cmd_config(args):
    from idt_core.config import UserConfig

    cfg = UserConfig.load()

    if args.set_value:
        key, _, value = args.set_value.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "default_provider":
            cfg.default_provider = value
        elif key == "default_model":
            cfg.default_model = value
        elif key == "default_prompt_name":
            cfg.default_prompt_name = value
        else:
            print(f"Unknown config key: {key!r}", file=sys.stderr)
            print("Valid keys: default_provider, default_model, default_prompt_name", file=sys.stderr)
            sys.exit(1)
        cfg.save()
        print(f"Set {key} = {value}")
        return

    # Show current config
    print(f"Config file:      {Path.home() / '.idt' / 'config.json'}")
    print(f"default_provider: {cfg.default_provider}")
    print(f"default_model:    {cfg.default_model}")
    print(f"default_prompt:   {cfg.default_prompt_name}")
    if cfg.custom_prompts:
        print(f"custom_prompts:   {', '.join(cfg.custom_prompts.keys())}")


# ------------------------------------------------------------------ #
# Argument parser                                                      #
# ------------------------------------------------------------------ #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idt",
        description="Image Description Toolkit — AI-powered image descriptions for accessibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  idt describe ~/Pictures/Vacation/
  idt describe ~/Pictures/Vacation/ --model claude-opus-4-6
  idt describe ~/Pictures/Vacation/ --provider ollama --model llava
  idt describe ~/Pictures/Vacation/ --prompt brief --limit 10
  idt describe ~/Pictures/NYT/ --prompt news --quiet
  idt status ~/Pictures/Vacation/
  idt show ~/Pictures/Vacation/morning.jpg
  idt show ~/Pictures/Vacation/ --json | grep -i "sunset"
  idt embed ~/Pictures/Vacation/
  idt embed ~/Pictures/Vacation/ --dry-run
  idt export ~/Pictures/Vacation/
  idt export ~/Pictures/Vacation/ --format csv
  idt watch ~/Downloads/NYT/ --interval 60 --prompt news
  idt watch ~/Downloads/NYT/ --quiet >> ~/nyt_descriptions.tsv
  get_nyt_images.sh | idt describe - --prompt news --provider anthropic
  idt describe - --provider florence < image_list.txt
  idt prompts
  idt config --set default_provider=anthropic

Supported providers:
  anthropic  Claude (requires ANTHROPIC_API_KEY environment variable)
  openai     GPT-4o (requires OPENAI_API_KEY environment variable)
  ollama     Local models via Ollama (no API key needed)
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # ---- describe ---- #
    p_desc = sub.add_parser(
        "describe",
        help="Generate AI descriptions for images in a directory",
        description="Describe images in a directory. Creates a .idt/ mirror directory next to "
                    "the source to store descriptions. Originals are never modified.",
    )
    p_desc.add_argument(
        "source",
        help="Directory containing images, or '-' to read image paths from stdin",
    )
    p_desc.add_argument(
        "--stdin", action="store_true",
        help="Read image file paths from stdin (one per line). Same as passing '-' as source.",
    )
    p_desc.add_argument(
        "--project", metavar="DIR",
        help="Project directory to use when reading from stdin (default: common ancestor of input paths)",
    )
    p_desc.add_argument(
        "--provider", choices=["anthropic", "ollama", "openai", "florence"],
        help="AI provider (default: from project config, then ~/.idt/config.json, then anthropic)",
    )
    p_desc.add_argument("--model", metavar="NAME", help="Model name")
    p_desc.add_argument(
        "--prompt", metavar="NAME",
        help=f"Named prompt to use (see 'idt prompts' for options)",
    )
    p_desc.add_argument(
        "--prompt-text", metavar="TEXT",
        help="Prompt text (overrides --prompt)",
    )
    p_desc.add_argument(
        "--ollama-host", metavar="URL", default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )
    p_desc.add_argument(
        "--redescribe", action="store_true",
        help="Generate a new description for images that already have one",
    )
    p_desc.add_argument(
        "--limit", type=int, metavar="N",
        help="Stop after describing N images",
    )
    p_desc.add_argument(
        "--quiet", "-q", action="store_true",
        help="Minimal output — only errors",
    )
    p_desc.set_defaults(func=cmd_describe)

    # ---- status ---- #
    p_status = sub.add_parser(
        "status",
        help="Show how many images have been described",
    )
    p_status.add_argument("source", help="Source directory")
    p_status.add_argument("--json", dest="json_out", action="store_true", help="Output as JSON")
    p_status.set_defaults(func=cmd_status)

    # ---- show ---- #
    p_show = sub.add_parser(
        "show",
        help="Print descriptions to stdout",
        description="Print the description for one image file, or all described images in a directory.",
    )
    p_show.add_argument("target", help="Image file or source directory")
    p_show.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Output as JSON (one object per line — pipeable to jq)",
    )
    p_show.add_argument("--quiet", "-q", action="store_true", help="Suppress informational messages")
    p_show.set_defaults(func=cmd_show)

    # ---- embed ---- #
    p_embed = sub.add_parser(
        "embed",
        help="Write descriptions into image metadata copies",
        description="Copy described images to .idt/embedded/ and write the description into "
                    "both EXIF ImageDescription and XMP dc:description. Source files are never "
                    "modified. HEIC files are converted to JPEG in the copy.",
    )
    p_embed.add_argument("source", help="Source directory (must already have described images)")
    p_embed.add_argument(
        "--force", action="store_true",
        help="Re-embed even if images were already embedded",
    )
    p_embed.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be embedded without writing anything",
    )
    p_embed.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    p_embed.set_defaults(func=cmd_embed)

    # ---- export ---- #
    p_export = sub.add_parser(
        "export",
        help="Export descriptions to HTML, CSV, or plain text",
        description="Generate a report from described images. Output goes to .idt/reports/.",
    )
    p_export.add_argument("source", help="Source directory")
    p_export.add_argument(
        "--format", choices=["html", "csv", "txt"], default="html",
        help="Output format (default: html)",
    )
    p_export.add_argument("--quiet", "-q", action="store_true",
                          help="Print only the output file path")
    p_export.set_defaults(func=cmd_export)

    # ---- watch ---- #
    p_watch = sub.add_parser(
        "watch",
        help="Monitor a directory and describe new images automatically",
        description="Describes existing undescribed images, then polls for new arrivals. "
                    "Useful for automation pipelines (e.g. download NYT images, auto-describe). "
                    "Press Ctrl+C to stop.",
    )
    p_watch.add_argument("source", help="Directory to watch")
    p_watch.add_argument(
        "--interval", type=int, default=30, metavar="SECONDS",
        help="Polling interval in seconds (default: 30)",
    )
    p_watch.add_argument(
        "--provider", choices=["anthropic", "ollama", "openai", "florence"],
        help="AI provider",
    )
    p_watch.add_argument("--model", metavar="NAME", help="Model name")
    p_watch.add_argument("--prompt", metavar="NAME", help="Named prompt")
    p_watch.add_argument("--prompt-text", metavar="TEXT", help="Prompt text")
    p_watch.add_argument(
        "--ollama-host", metavar="URL", default="http://localhost:11434",
    )
    p_watch.add_argument(
        "--quiet", "-q", action="store_true",
        help="Output tab-separated filename/description lines (for piping)",
    )
    p_watch.set_defaults(func=cmd_watch)

    # ---- prompts ---- #
    p_prompts = sub.add_parser("prompts", help="List available prompts")
    p_prompts.add_argument("--json", dest="json_out", action="store_true", help="Output as JSON")
    p_prompts.set_defaults(func=cmd_prompts)

    # ---- config ---- #
    p_config = sub.add_parser("config", help="View or set default configuration")
    p_config.add_argument(
        "--set", dest="set_value", metavar="KEY=VALUE",
        help="Set a config value (e.g. --set default_provider=anthropic)",
    )
    p_config.set_defaults(func=cmd_config)

    return parser


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
