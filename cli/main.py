#!/usr/bin/env python3
"""
idt — Image Description Toolkit CLI

Usage:
  idt guide                         Interactive setup wizard (start here)
  idt describe <directory> [options]
  idt download <url> [directory] [options]
  idt status   <directory>
  idt show     <directory|image>
  idt embed    <directory> [options]
  idt export   <directory> [options]
  idt watch    <directory> [options]
  idt combine  <directory> [options]
  idt video    <directory> [options]
  idt models   [--provider NAME]
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
    """Instantiate the requested provider with a clear error if deps are missing."""
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

    if getattr(args, "prompt_text", None):
        return ("custom", args.prompt_text)

    user_cfg = UserConfig.load()
    # Accept either a WorkspaceDefaults (.prompt_name) or legacy ProjectConfig
    # (.default_prompt_name).
    cfg_default = None
    if project_config is not None:
        cfg_default = (
            getattr(project_config, "prompt_name", None)
            or getattr(project_config, "default_prompt_name", None)
        )
    name = (
        getattr(args, "prompt", None)
        or cfg_default
        or user_cfg.default_prompt_name
    )
    text = user_cfg.get_prompt_text(name) or BUILT_IN_PROMPTS.get("detailed", "")
    return (name, text)


def _provider_args(p: argparse.ArgumentParser) -> None:
    """Add the standard provider/model/ollama-host arguments."""
    p.add_argument(
        "--provider", choices=["anthropic", "ollama", "openai", "florence"],
        help="AI provider (default: from config, else ollama)",
    )
    p.add_argument("--model", metavar="NAME", help="Model name")
    p.add_argument(
        "--ollama-host", metavar="URL", default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )


def _prompt_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--prompt", metavar="NAME",
                   help="Named prompt to use (see 'idt prompts')")
    p.add_argument("--prompt-text", metavar="TEXT",
                   help="Custom prompt text (overrides --prompt)")


def _metadata_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--no-metadata", dest="extract_metadata", action="store_false",
        default=True,
        help="Disable EXIF metadata extraction (don't inject date/location context into prompt)",
    )
    p.add_argument(
        "--geocode", action="store_true",
        help="Reverse-geocode GPS coordinates to city/state (requires internet; adds 1s/photo delay)",
    )


# ------------------------------------------------------------------ #
# Workspace resolution                                                 #
# ------------------------------------------------------------------ #

def _open_or_create_workspace(source: Path, workspace_arg: Optional[str]):
    """
    Resolve the .idtw bundle for a describe run.
      --workspace PATH  (contains a separator or ends in .idtw) -> that exact path
      --workspace NAME  (bare name)                              -> NAME.idtw next to source
      (omitted)                                                  -> <source>.idtw next to source
    """
    from idt_core.workspace import Workspace, BUNDLE_EXT

    if workspace_arg:
        wp = Path(workspace_arg).expanduser()
        is_bare_name = (wp.parent == Path(".")) and (BUNDLE_EXT not in workspace_arg)
        if is_bare_name:
            wp = source.parent / workspace_arg
    else:
        wp = source.parent / source.name  # Workspace.open appends .idtw
    return Workspace.open(wp)


def _find_workspace(arg: str):
    """
    For read commands: locate an existing bundle from a user-supplied path.
    Accepts a .idtw bundle directly, or a source folder whose sibling bundle exists.
    Returns a Workspace or None.
    """
    from idt_core.workspace import Workspace

    p = Path(arg).expanduser().resolve()
    if Workspace.is_bundle(p):
        return Workspace.open(p)
    sibling = p.parent / (p.name + ".idtw")
    if Workspace.is_bundle(sibling):
        return Workspace.open(sibling)
    return None


# ------------------------------------------------------------------ #
# describe                                                             #
# ------------------------------------------------------------------ #

def cmd_describe(args):
    from idt_core.pipeline import WorkspacePipeline, RunOptions
    from idt_core.progress import Progress
    from idt_core.config import UserConfig

    stdin_mode = getattr(args, "stdin", False) or args.source == "-"
    if stdin_mode:
        _cmd_describe_stdin(args)
        return

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    ws = _open_or_create_workspace(source, getattr(args, "workspace", None))
    user_cfg = UserConfig.load()

    provider_name = args.provider or ws.defaults.provider or user_cfg.default_provider
    model = args.model or ws.defaults.model or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, ws.defaults)

    # Copy this run's source images into the bundle (idempotent; originals untouched)
    if not args.quiet:
        print(f"Source:     {source}")
        print(f"Workspace:  {ws.path}")
    added = ws.add_source_folder(source, recursive=True)
    if not args.quiet:
        print(f"Images:     {len(added)} in workspace")
        print(f"Provider:   {provider_name}  model: {model}")
        print(f"Prompt:     {prompt_name}")
        if args.extract_metadata:
            gcstr = " + geocoding" if args.geocode else ""
            print(f"Metadata:   EXIF extraction enabled{gcstr}")
        print()

    # Persist the chosen defaults on the workspace
    ws.defaults.provider = provider_name
    ws.defaults.model = model
    ws.defaults.prompt_name = prompt_name
    ws.geocode_enabled = bool(args.geocode)
    ws.save_manifest()

    provider = _make_provider(provider_name, model, args.ollama_host)

    options = RunOptions(
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        redescribe=args.redescribe,
        limit=args.limit,
        extract_metadata=args.extract_metadata,
        geocode=args.geocode,
    )

    all_items = ws.items()
    queue = all_items if args.redescribe else [i for i in all_items if not i.described]
    if args.limit:
        queue = queue[: args.limit]

    if not queue:
        if not args.quiet:
            st = ws.status()
            n = st["described"]
            print(f"All {n} image{'s are' if n != 1 else ' is'} already described.")
            print("Use --redescribe to generate additional descriptions.")
        return

    progress = Progress(total=len(queue), quiet=args.quiet)
    progress.start(f"{provider_name} / {model}")

    described = errors = 0
    pipeline = WorkspacePipeline(ws, provider)

    for event in pipeline.run(options):
        if event.success:
            described += 1
            extra = ""
            if not args.quiet and event.metadata:
                ctx = event.metadata.prompt_context()
                if ctx:
                    extra = f"  [{ctx}]"
            progress.update(event.item.display_name, success=True, note=extra)
        else:
            errors += 1
            progress.update(event.item.display_name, success=False, error=event.error)

    progress.summary(described=described, errors=errors)

    if args.embed and described > 0:
        print()
        _do_embed_workspace(ws, force=False, dry_run=False, quiet=args.quiet)


def _cmd_describe_stdin(args):
    """
    Describe image paths read from stdin, one per line.
    Pipeline use: get_nyt_images.sh | idt describe - --prompt news
    """
    from idt_core.project import Project
    from idt_core.image_item import ImageItem, Description
    from idt_core.progress import Progress
    from idt_core.config import UserConfig
    from idt_core.converter import load_for_api
    from idt_core.metadata import MetadataExtractor, NominatimGeocoder

    import io
    stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig")
    paths = [
        Path(line.strip()).resolve()
        for line in stdin
        if line.strip() and not line.strip().startswith("#")
    ]
    if not paths:
        print("No image paths received on stdin.", file=sys.stderr)
        sys.exit(1)

    missing = [p for p in paths if not p.exists()]
    for p in missing:
        print(f"Warning: not found: {p}", file=sys.stderr)
    paths = [p for p in paths if p.exists()]
    if not paths:
        sys.exit(1)

    source = Path(getattr(args, "project", None) or "").resolve() if getattr(args, "project", None) else _common_ancestor(paths)
    project = Project.open(source)
    user_cfg = UserConfig.load()

    provider_name = args.provider or project.config.default_provider or user_cfg.default_provider
    model = args.model or project.config.default_model or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, project.config)
    provider = _make_provider(provider_name, model, args.ollama_host)

    extractor = MetadataExtractor() if args.extract_metadata else None
    geocoder = None
    if extractor and args.geocode:
        geocoder = NominatimGeocoder(
            cache_path=Path.home() / ".idt" / "geocode_cache.json"
        )

    if not args.quiet:
        print(f"Project:   {project.idt_dir}")
        print(f"Provider:  {provider_name}  model: {model}")
        print(f"Images:    {len(paths)} from stdin")
        print()

    progress = Progress(total=len(paths), quiet=args.quiet)
    described = errors = 0

    for img_path in paths:
        try:
            rel = img_path.relative_to(source)
        except ValueError:
            print(f"Warning: {img_path} is outside project root {source} — skipping", file=sys.stderr)
            continue

        sidecar = project.sidecar_path(img_path)
        item = ImageItem.load(sidecar) if sidecar.exists() else ImageItem(source_path=img_path, sidecar_path=sidecar)

        if item.described and not args.redescribe:
            progress.skip(img_path.name, "already described")
            continue

        try:
            # Metadata extraction
            meta_context = ""
            if extractor:
                meta = extractor.extract(img_path)
                if geocoder:
                    meta = geocoder.enrich(meta)
                meta_context = meta.prompt_context()
                item.metadata = meta.to_dict()

            effective_prompt = prompt_text
            if meta_context and effective_prompt:
                effective_prompt = f"Context: {meta_context}\n\n{effective_prompt}"
            elif meta_context:
                effective_prompt = f"Context: {meta_context}\n\n"

            image_bytes, mime_type = load_for_api(img_path)
            result = provider.describe(image_bytes, mime_type, effective_prompt)
            desc = Description.create(
                text=result.text,
                model=result.model,
                provider=result.provider,
                prompt_name=prompt_name,
                prompt_text=prompt_text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                metadata_context=meta_context or None,
            )
            item.add_description(desc)
            item.save()
            described += 1
            progress.update(img_path.name, success=True)

            if args.quiet:
                print(f"{img_path}\t{result.text}")

        except Exception as exc:
            errors += 1
            progress.update(img_path.name, success=False, error=str(exc))

    progress.summary(described=described, errors=errors)


def _common_ancestor(paths: list[Path]) -> Path:
    if not paths:
        raise ValueError("No paths given")
    if len(paths) == 1:
        return paths[0].parent
    common = paths[0].parent
    for p in paths[1:]:
        while common != p and not str(p).startswith(str(common)):
            common = common.parent
    return common


# ------------------------------------------------------------------ #
# download                                                             #
# ------------------------------------------------------------------ #

def cmd_download(args):
    """
    Download images from a URL and optionally describe them.

    idt download https://www.nytimes.com/ --max 20 --describe --prompt news
    """
    from idt_core.project import Project
    from idt_core.downloader import Downloader

    # Determine target directory
    target = Path(args.directory).resolve() if args.directory else Path.cwd()
    target.mkdir(parents=True, exist_ok=True)
    project = Project.open(target)

    if not args.quiet:
        print(f"URL:       {args.url}")
        print(f"Project:   {project.idt_dir}")
        print()

    min_w = min_h = 0
    if args.min_size:
        parts = args.min_size.lower().split("x")
        if len(parts) == 2:
            try:
                min_w, min_h = int(parts[0]), int(parts[1])
            except ValueError:
                print(f"Invalid --min-size format (use WIDTHxHEIGHT, e.g. 200x200)", file=sys.stderr)
                sys.exit(1)

    total_started = [0]
    def _on_progress(i: int, total: int, url: str) -> None:
        if not args.quiet:
            pct = int(i / total * 100) if total else 0
            print(f"  {i} of {total}  {pct}%  {url[:60]}", end="\r", flush=True)
        total_started[0] = total

    downloader = Downloader(
        project=project,
        min_width=min_w,
        min_height=min_h,
        timeout=args.timeout,
        on_progress=_on_progress,
    )

    try:
        result = downloader.download(args.url, max_images=args.max_images)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Install with: pip install requests beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print()  # clear progress line

    print(f"Downloaded: {result.downloaded} images  skipped: {result.skipped}  failed: {result.failed}")
    print(f"Location:  {result.download_dir}")

    if result.alt_texts and not args.quiet:
        print(f"Alt texts: {len(result.alt_texts)} images had existing alt text from the site")

    # Auto-describe the downloaded images if requested
    if args.describe and result.downloaded > 0:
        print()
        # Treat the download dir as a new project source
        dl_project = Project.open(result.download_dir)

        # Seed alt text into sidecars before describing
        if result.alt_texts:
            from idt_core.image_item import ImageItem
            for fname, alt in result.alt_texts.items():
                img_path = result.download_dir / fname
                if img_path.exists():
                    sp = dl_project.sidecar_path(img_path)
                    item = ImageItem.load(sp) if sp.exists() else ImageItem(source_path=img_path, sidecar_path=sp)
                    item.alt_text = alt
                    item.save()

        from idt_core.pipeline import Pipeline, RunOptions
        from idt_core.progress import Progress
        from idt_core.config import UserConfig

        user_cfg = UserConfig.load()
        provider_name = args.provider or user_cfg.default_provider
        model = args.model or user_cfg.default_model
        prompt_name, prompt_text = _resolve_prompt(args, dl_project.config)
        provider = _make_provider(provider_name, model, args.ollama_host)

        if not args.quiet:
            print(f"Describing {result.downloaded} images with {provider_name} / {model}...")
            print()

        options = RunOptions(
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            extract_metadata=False,  # downloaded images don't have EXIF
        )
        progress = Progress(total=result.downloaded, quiet=args.quiet)
        described = errors = 0
        pipeline = Pipeline(dl_project, provider)

        for event in pipeline.run(options):
            if event.success:
                described += 1
                progress.update(event.item.display_name, success=True)
            else:
                errors += 1
                progress.update(event.item.display_name, success=False, error=event.error)

        progress.summary(described=described, errors=errors)

        if described > 0 and args.embed:
            print()
            _do_embed(dl_project, force=False, dry_run=False, quiet=args.quiet)


# ------------------------------------------------------------------ #
# video                                                                #
# ------------------------------------------------------------------ #

def cmd_video(args):
    """
    Extract frames from video files and optionally describe them.

    idt video ~/Movies/concert.mp4 --interval 5 --describe
    idt video ~/Movies/events/ --scene 30 --describe --prompt detailed
    """
    from idt_core.project import Project
    from idt_core.video import VideoExtractor, VideoExtractionOptions, scan_videos
    from idt_core.scanner import is_video

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Error: not found: {source}", file=sys.stderr)
        sys.exit(1)

    project = Project.open(source if source.is_dir() else source.parent)

    # Find videos to process
    if source.is_file():
        if not is_video(source):
            print(f"Error: not a video file: {source}", file=sys.stderr)
            sys.exit(1)
        videos = [source]
    else:
        videos = list(scan_videos(source))
        if not videos:
            print(f"No video files found in: {source}", file=sys.stderr)
            sys.exit(1)

    mode = "scene" if args.scene else "interval"
    opts = VideoExtractionOptions(
        mode=mode,
        interval_seconds=args.interval,
        scene_threshold=args.scene,
        max_frames=args.max_frames,
    )

    if not args.quiet:
        print(f"Source:    {source}")
        print(f"Videos:    {len(videos)}")
        print(f"Mode:      {mode}  ({'every ' + str(args.interval) + 's' if mode == 'interval' else 'threshold ' + str(args.scene)})")
        print()

    extractor = VideoExtractor(project)
    all_frame_paths = []
    all_frame_dirs = []

    for video in videos:
        if not args.quiet:
            print(f"  Extracting frames: {video.name}")
        try:
            result = extractor.extract(video, opts)
            all_frame_paths.extend(result.frame_paths)
            all_frame_dirs.append(result.frames_dir)
            if not args.quiet:
                print(f"    {len(result.frame_paths)} frames → {result.frames_dir}")
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("Install with: pip install opencv-python", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"  Error processing {video.name}: {e}", file=sys.stderr)

    total_frames = len(all_frame_paths)
    if not args.quiet:
        print(f"\nExtracted {total_frames} frames total.")

    if args.describe and total_frames > 0:
        print()
        from idt_core.pipeline import Pipeline, RunOptions
        from idt_core.progress import Progress
        from idt_core.config import UserConfig

        user_cfg = UserConfig.load()
        provider_name = args.provider or user_cfg.default_provider
        model = args.model or user_cfg.default_model
        prompt_name, prompt_text = _resolve_prompt(args, project.config)
        provider = _make_provider(provider_name, model, args.ollama_host)

        if not args.quiet:
            print(f"Describing {total_frames} frames with {provider_name} / {model}...")
            print()

        described = errors = 0

        for frames_dir in all_frame_dirs:
            frame_project = Project.open(frames_dir)
            options = RunOptions(
                prompt_name=prompt_name,
                prompt_text=prompt_text,
                extract_metadata=False,
            )
            progress = Progress(total=len(list(frame_project.undescribed())), quiet=args.quiet)
            pipeline = Pipeline(frame_project, provider)
            for event in pipeline.run(options):
                if event.success:
                    described += 1
                    progress.update(event.item.display_name, success=True)
                else:
                    errors += 1
                    progress.update(event.item.display_name, success=False, error=event.error)
            progress.summary(described=described, errors=errors)


# ------------------------------------------------------------------ #
# status                                                               #
# ------------------------------------------------------------------ #

def cmd_status(args):
    source = Path(args.source).resolve()

    # If given a parent dir, scan for all workspaces/projects underneath it
    if args.all:
        _cmd_status_all(source, args)
        return

    ws = _find_workspace(args.source)
    if ws is not None:
        st = ws.status()
        if args.json_out:
            print(json.dumps(st, indent=2, ensure_ascii=False))
            return
        pct = int(st["described"] / st["total"] * 100) if st["total"] else 0
        print(f"Workspace:   {st['path']}")
        if st["sources"]:
            print(f"Sources:     {', '.join(st['sources'])}")
        print(f"Total:       {st['total']}")
        print(f"Described:   {st['described']}  ({pct}%)")
        print(f"Remaining:   {st['undescribed']}")
        return

    # Legacy fallback: an old sibling .idt/ project
    from idt_core.project import Project
    if not source.is_dir():
        print(f"Error: no workspace found at: {source}", file=sys.stderr)
        sys.exit(1)
    project = Project.open(source)
    st = project.status()
    if args.json_out:
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return
    pct = int(st["described"] / st["total"] * 100) if st["total"] else 0
    print(f"Source:      {st['source']}")
    print(f"Project:     {st['idt_dir']}  (legacy .idt — re-run 'idt describe' to migrate)")
    print(f"Total:       {st['total']}")
    print(f"Described:   {st['described']}  ({pct}%)")
    print(f"Remaining:   {st['undescribed']}")


def _cmd_status_all(root: Path, args) -> None:
    """Find all .idtw bundles (and legacy .idt/ projects) under root and summarize them."""
    from idt_core.project import Project
    from idt_core.workspace import Workspace

    rows = []

    # New-style .idtw bundles
    for bundle in sorted(root.rglob("*.idtw")):
        if not Workspace.is_bundle(bundle):
            continue
        try:
            st = Workspace.open(bundle).status()
            # normalize keys to match the legacy rows used below
            rows.append({"total": st["total"], "described": st["described"],
                         "source": st["path"]})
        except Exception:
            continue

    # Legacy sibling .idt/ projects
    for idt_dir in sorted(root.rglob("*.idt")):
        source = idt_dir.parent / idt_dir.stem
        if not source.is_dir():
            continue
        try:
            st = Project.open(source).status()
            rows.append(st)
        except Exception:
            continue

    if not rows:
        print(f"No IDT workspaces found under: {root}")
        return

    if args.json_out:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    total_images = sum(r["total"] for r in rows)
    total_desc = sum(r["described"] for r in rows)
    print(f"Projects found: {len(rows)}  under {root}")
    print(f"Total images:   {total_images}  Described: {total_desc}  ({int(total_desc/total_images*100) if total_images else 0}%)")
    print()
    for r in rows:
        pct = int(r["described"] / r["total"] * 100) if r["total"] else 0
        src = Path(r["source"])
        print(f"  {src.name:40s}  {r['described']:5d}/{r['total']:5d}  {pct:3d}%")


# ------------------------------------------------------------------ #
# show                                                                 #
# ------------------------------------------------------------------ #

def cmd_show(args):
    target = Path(args.target).resolve()

    if target.is_file():
        _show_file(target, args)
    elif target.is_dir() or Path(args.target).suffix.lower() == ".idtw":
        _show_directory(target, args)
    else:
        print(f"Error: not found: {target}", file=sys.stderr)
        sys.exit(1)


def _show_file(target: Path, args):
    from idt_core.workspace import Workspace
    from idt_core.project import Project
    from idt_core.image_item import ImageItem

    # Prefer a .idtw bundle: walk up looking for a sibling bundle whose items
    # have this original as their source_path.
    candidate = target.parent
    target_str = str(target)
    while True:
        sibling = candidate.parent / (candidate.name + ".idtw")
        if Workspace.is_bundle(sibling):
            ws = Workspace.open(sibling)
            for item in ws.items():
                if item.source_path == target_str or item.image == target.name:
                    _print_item(item, args)
                    return
        # Legacy sibling .idt/ project
        idt_dir = candidate.parent / (candidate.name + ".idt")
        if idt_dir.is_dir():
            project = Project.open(candidate)
            sidecar = project.sidecar_path(target)
            if sidecar.exists():
                _print_item(ImageItem.load(sidecar), args)
                return
        if candidate == candidate.parent:
            break
        candidate = candidate.parent

    if not args.quiet:
        print(f"No description found for: {target.name}", file=sys.stderr)
    sys.exit(1)


def _show_directory(target: Path, args):
    # Prefer a .idtw bundle (the target itself, or its sibling)
    ws = _find_workspace(str(target))
    if ws is not None:
        items = [i for i in ws.items() if i.described]
        if not items:
            if not args.quiet:
                print("No described images in this workspace yet.")
                print(f"Run:  idt describe {target}")
            return
        for item in items:
            _print_item(item, args)
            if not args.json_out:
                print()
        return

    # Legacy fallback
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


def _desc_when(desc) -> str:
    """Timestamp accessor that works for both Description (.timestamp) and
    WorkspaceDescription (.created)."""
    return getattr(desc, "timestamp", None) or getattr(desc, "created", "") or ""


def _print_item(item, args):
    desc = item.active_description
    if args.json_out:
        out = {
            "file": item.display_name,
            "source": str(item.source_path),
            "described": item.described,
            "description": desc.text if desc else None,
            "model": desc.model if desc else None,
            "provider": desc.provider if desc else None,
            "timestamp": _desc_when(desc) if desc else None,
            "metadata_context": desc.metadata_context if desc else None,
        }
        if item.metadata:
            out["metadata"] = item.metadata
        if item.alt_text:
            out["alt_text"] = item.alt_text
        print(json.dumps(out, ensure_ascii=False))
        return

    if not desc:
        print(f"{item.display_name}: not described")
        return

    print(f"File:      {item.display_name}")
    print(f"Model:     {desc.model}  ({desc.provider})")
    if desc.metadata_context:
        print(f"Context:   {desc.metadata_context}")
    if item.alt_text:
        print(f"Alt text:  {item.alt_text}")
    when = _desc_when(desc)
    if when:
        print(f"Date:      {when[:10]}")
    if desc.output_tokens:
        print(f"Tokens:    {desc.output_tokens} out")
    print()
    print(desc.text)


# ------------------------------------------------------------------ #
# embed                                                                #
# ------------------------------------------------------------------ #

def _do_embed_workspace(ws, force: bool, dry_run: bool, quiet: bool) -> None:
    """Embed each described image's active description into a copy in <bundle>/embedded/."""
    from datetime import datetime, timezone
    from idt_core.embedder import embed_image_file

    out_dir = ws.path / "embedded"
    described = [i for i in ws.items() if i.described]
    pending = [i for i in described if force or not i.embedded_at]

    n = 0
    errors = []
    for item in pending:
        desc = item.active_description
        if not desc:
            continue
        if dry_run:
            n += 1
            continue
        try:
            embed_image_file(ws.image_path(item), desc.text, out_dir / item.image)
            item.embedded_at = datetime.now(timezone.utc).isoformat()
            ws.save_item(item)
            n += 1
        except Exception as exc:
            errors.append(f"{item.display_name}: {exc}")

    verb = "Would embed" if dry_run else "Embedded"
    print(f"{verb} {n} image{'s' if n != 1 else ''}.", end="")
    if errors:
        print(f"  {len(errors)} error(s).", end="")
    print()
    if not dry_run and not quiet and n > 0:
        print(f"Embedded copies: {out_dir}")


def cmd_embed(args):
    source = Path(args.source).resolve()
    ws = _find_workspace(args.source)
    if ws is None and not source.is_dir():
        print(f"Error: not a workspace or directory: {source}", file=sys.stderr)
        sys.exit(1)
    if ws is None:
        # Source folder given but no bundle exists yet — describe must run first
        print("No workspace found. Run 'idt describe' on this folder first.")
        return

    described = [i for i in ws.items() if i.described]
    if not described:
        print("No described images found. Run 'idt describe' first.")
        return

    if not args.quiet:
        pending = [i for i in described if args.force or not i.embedded_at]
        already = len(described) - len(pending)
        print(f"Workspace: {ws.path}")
        print(f"Output:    {ws.path / 'embedded'}")
        print(f"To embed:  {len(pending)}")
        if already:
            print(f"Already embedded: {already}  (use --force to re-embed)")
        if args.dry_run:
            print("\nDry run — no files will be written.")
        print()

    _do_embed_workspace(ws, force=args.force, dry_run=args.dry_run, quiet=args.quiet)


# ------------------------------------------------------------------ #
# export                                                               #
# ------------------------------------------------------------------ #

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

    print(str(out)) if args.quiet else print(f"Exported {fmt.upper()}: {out}")


# ------------------------------------------------------------------ #
# combine                                                              #
# ------------------------------------------------------------------ #

def cmd_combine(args):
    """
    Merge descriptions from multiple .idt/ projects into a single CSV or TSV.

    Walks the input directory looking for *.idt/ project mirrors.
    Useful for building a complete picture across many directories.

    idt combine ~/Pictures/ --output all_descriptions.csv
    idt combine ~/Pictures/ --format tsv | sort -k3 > sorted.tsv
    """
    import csv
    from idt_core.project import Project

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    idt_dirs = sorted(root.rglob("*.idt"))
    if not idt_dirs:
        print(f"No IDT projects found under: {root}")
        sys.exit(1)

    rows = []
    for idt_dir in idt_dirs:
        source = idt_dir.parent / idt_dir.stem
        if not source.is_dir():
            continue
        try:
            project = Project.open(source)
            for item in project.described():
                desc = item.active_description
                if not desc:
                    continue
                rows.append({
                    "file": item.display_name,
                    "source_path": str(item.source_path),
                    "project": str(source),
                    "description": desc.text,
                    "model": desc.model,
                    "provider": desc.provider,
                    "prompt_name": desc.prompt_name,
                    "timestamp": desc.timestamp,
                    "metadata_context": desc.metadata_context or "",
                    "input_tokens": desc.input_tokens or "",
                    "output_tokens": desc.output_tokens or "",
                    "alt_text": item.alt_text or "",
                })
        except Exception as e:
            print(f"Warning: could not read {idt_dir}: {e}", file=sys.stderr)

    if not rows:
        print("No described images found.")
        return

    # Sort by timestamp or metadata date
    sort_key = args.sort
    if sort_key == "date":
        rows.sort(key=lambda r: r.get("metadata_context", "") or r.get("timestamp", ""))
    elif sort_key == "file":
        rows.sort(key=lambda r: r["file"].lower())
    else:
        rows.sort(key=lambda r: r["timestamp"])

    delimiter = "\t" if args.format == "tsv" else ","

    if args.output:
        out_path = Path(args.output).resolve()
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Combined {len(rows)} descriptions → {out_path}")
    else:
        # Stdout
        import sys as _sys
        writer = csv.DictWriter(_sys.stdout, fieldnames=list(rows[0].keys()), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


# ------------------------------------------------------------------ #
# models                                                               #
# ------------------------------------------------------------------ #

def cmd_models(args):
    """
    Check which AI models are available.

    idt models                     — check all providers
    idt models --provider ollama   — list Ollama models
    idt models --provider anthropic — verify Claude API access
    """
    results = {}

    # Ollama
    if not args.provider or args.provider == "ollama":
        try:
            from idt_core.providers.ollama import OllamaProvider, DEFAULT_MODEL
            provider_inst = OllamaProvider(model=DEFAULT_MODEL, host=args.ollama_host)
            models = provider_inst.list_models()
            results["ollama"] = {"status": "ok", "models": models}
        except Exception as e:
            results["ollama"] = {"status": "error", "error": str(e)}

    # Anthropic
    if not args.provider or args.provider == "anthropic":
        import os
        if os.environ.get("ANTHROPIC_API_KEY"):
            from idt_core.providers.claude import CLAUDE_MODELS
            results["anthropic"] = {"status": "key_found", "models": CLAUDE_MODELS}
        else:
            results["anthropic"] = {"status": "no_key", "models": []}

    # OpenAI
    if not args.provider or args.provider == "openai":
        import os
        if os.environ.get("OPENAI_API_KEY"):
            from idt_core.providers.openai_provider import OPENAI_MODELS
            results["openai"] = {"status": "key_found", "models": OPENAI_MODELS}
        else:
            results["openai"] = {"status": "no_key", "models": []}

    if args.json_out:
        print(json.dumps(results, indent=2))
        return

    for provider, info in results.items():
        status = info["status"]
        models = info.get("models", [])
        if status == "ok":
            print(f"\n{provider} ({len(models)} models available):")
            for m in models:
                print(f"    {m}")
        elif status == "key_found":
            print(f"\n{provider} (API key found, {len(models)} known models):")
            for m in models:
                print(f"    {m}")
        elif status == "no_key":
            key = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
            print(f"\n{provider}: no API key ({key} not set)")
        else:
            print(f"\n{provider}: error — {info.get('error', 'unknown')}")


# ------------------------------------------------------------------ #
# watch                                                                #
# ------------------------------------------------------------------ #

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
        print(f"Watching:  {source}")
        print(f"Provider:  {provider_name}  model: {model}")
        print(f"Interval:  {args.interval}s  prompt: {prompt_name}")
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
                        preview = desc.text[:120] + ("..." if len(desc.text) > 120 else "")
                        print(f"  {preview}\n")
                else:
                    if desc:
                        print(f"{event.item.display_name}\t{desc.text}")
            else:
                print(f"Error: {event.item.display_name}: {event.error}", file=sys.stderr)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nWatcher stopped.")


# ------------------------------------------------------------------ #
# prompts                                                              #
# ------------------------------------------------------------------ #

def cmd_prompts(args):
    from idt_core.config import UserConfig

    user_cfg = UserConfig.load()
    all_prompts = user_cfg.list_prompts()

    if args.json_out:
        print(json.dumps(all_prompts, indent=2, ensure_ascii=False))
        return

    print("Available prompts:\n")
    for name, text in all_prompts.items():
        marker = " (custom)" if name in user_cfg.custom_prompts else ""
        print(f"  {name}{marker}")
        preview = text[:80] + ("..." if len(text) > 80 else "")
        print(f"    {preview}\n")


# ------------------------------------------------------------------ #
# config                                                               #
# ------------------------------------------------------------------ #

def cmd_stats(args):
    """
    Show token usage and cost estimates across a project.

    idt stats ~/Pictures/Vacation/
    idt stats ~/Pictures/ --all
    idt stats ~/Pictures/Vacation/ --json
    """
    from idt_core.project import Project

    root = Path(args.source).resolve()

    if args.all:
        idt_dirs = sorted(root.rglob("*.idt"))
        projects = []
        for idt_dir in idt_dirs:
            source = idt_dir.parent / idt_dir.stem
            if source.is_dir():
                try:
                    projects.append(Project.open(source))
                except Exception:
                    pass
        if not projects:
            print(f"No IDT projects found under: {root}")
            return
    else:
        if not root.is_dir():
            print(f"Error: not a directory: {root}", file=sys.stderr)
            sys.exit(1)
        projects = [Project.open(root)]

    # Accumulate stats per provider+model
    totals: dict = {}  # (provider, model) -> {images, input_tokens, output_tokens}
    grand_images = grand_in = grand_out = 0
    no_token_count = 0

    for project in projects:
        for item in project.described():
            desc = item.active_description
            if not desc:
                continue
            key = (desc.provider or "unknown", desc.model or "unknown")
            if key not in totals:
                totals[key] = {"images": 0, "input_tokens": 0, "output_tokens": 0}
            totals[key]["images"] += 1
            grand_images += 1
            if desc.input_tokens:
                totals[key]["input_tokens"] += desc.input_tokens
                grand_in += desc.input_tokens
            else:
                no_token_count += 1
            if desc.output_tokens:
                totals[key]["output_tokens"] += desc.output_tokens
                grand_out += desc.output_tokens

    if not totals:
        print("No described images found.")
        return

    # Rough cost table (USD per 1M tokens, input/output)
    COST_TABLE = {
        "claude-opus-4-8":             (15.0,  75.0),
        "claude-opus-4-6":             (15.0,  75.0),
        "claude-sonnet-4-6":           (3.0,   15.0),
        "claude-haiku-4-5-20251001":   (0.8,   4.0),
        "claude-haiku-3-5-20241022":   (0.8,   4.0),
        "gpt-4o":                      (2.5,   10.0),
        "gpt-4o-mini":                 (0.15,  0.6),
    }

    if args.json_out:
        rows = []
        for (prov, model), d in sorted(totals.items()):
            cost_in, cost_out = COST_TABLE.get(model, (0, 0))
            cost = (d["input_tokens"] / 1_000_000 * cost_in +
                    d["output_tokens"] / 1_000_000 * cost_out)
            rows.append({
                "provider": prov, "model": model,
                "images": d["images"],
                "input_tokens": d["input_tokens"],
                "output_tokens": d["output_tokens"],
                "estimated_cost_usd": round(cost, 4) if cost else None,
            })
        print(json.dumps(rows, indent=2))
        return

    print(f"Described images: {grand_images}")
    if no_token_count:
        print(f"  (Token data missing for {no_token_count} images — local models don't report tokens)")
    print()
    print(f"{'Provider':<12} {'Model':<35} {'Images':>7} {'Input tok':>10} {'Output tok':>11} {'Est. cost':>10}")
    print("-" * 90)

    for (prov, model), d in sorted(totals.items()):
        cost_in_rate, cost_out_rate = COST_TABLE.get(model, (0, 0))
        cost = (d["input_tokens"] / 1_000_000 * cost_in_rate +
                d["output_tokens"] / 1_000_000 * cost_out_rate)
        cost_str = f"${cost:.4f}" if cost else "n/a"
        in_str = f"{d['input_tokens']:,}" if d["input_tokens"] else "n/a"
        out_str = f"{d['output_tokens']:,}" if d["output_tokens"] else "n/a"
        print(f"{prov:<12} {model:<35} {d['images']:>7} {in_str:>10} {out_str:>11} {cost_str:>10}")

    if len(totals) > 1:
        total_cost_str = ""
        total_in_str = f"{grand_in:,}" if grand_in else "n/a"
        total_out_str = f"{grand_out:,}" if grand_out else "n/a"
        print("-" * 90)
        print(f"{'TOTAL':<12} {'':<35} {grand_images:>7} {total_in_str:>10} {total_out_str:>11} {total_cost_str:>10}")


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

    print(f"Config file:      {Path.home() / '.idt' / 'config.json'}")
    print(f"default_provider: {cfg.default_provider}")
    print(f"default_model:    {cfg.default_model}")
    print(f"default_prompt:   {cfg.default_prompt_name}")
    if cfg.custom_prompts:
        print(f"custom_prompts:   {', '.join(cfg.custom_prompts.keys())}")


# ------------------------------------------------------------------ #
# guide                                                                #
# ------------------------------------------------------------------ #

def cmd_guide(args):
    from cli.guide import run_guide
    run_guide()


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
  idt guide                                              # start here — interactive wizard
  idt describe ~/Pictures/Vacation/
  idt describe ~/Pictures/Vacation/ --provider anthropic --model claude-opus-4-6
  idt describe ~/Pictures/Vacation/ --provider ollama --model llava
  idt describe ~/Pictures/Vacation/ --prompt brief --limit 10 --embed
  idt describe ~/Pictures/Vacation/ --geocode            # add city/state to prompt context
  idt describe ~/Pictures/NYT/ --prompt news --quiet
  idt download https://www.nytimes.com/ --max 20 --describe --prompt news
  idt download https://example.com/gallery ~/Photos/web --max 50
  idt status ~/Pictures/Vacation/
  idt status ~/Pictures/ --all                          # show all projects under a directory
  idt show ~/Pictures/Vacation/morning.jpg
  idt show ~/Pictures/Vacation/ --json | python -c "import sys,json; [print(r['description']) for r in map(json.loads, sys.stdin)]"
  idt embed ~/Pictures/Vacation/
  idt embed ~/Pictures/Vacation/ --dry-run
  idt export ~/Pictures/Vacation/
  idt export ~/Pictures/Vacation/ --format csv
  idt combine ~/Pictures/ --output all_descriptions.csv
  idt combine ~/Pictures/ --sort date --format tsv > by_date.tsv
  idt video ~/Movies/concert.mp4 --interval 5 --describe
  idt video ~/Movies/ --scene 30 --describe --prompt detailed
  idt watch ~/Downloads/NYT/ --interval 60 --prompt news
  idt watch ~/Downloads/NYT/ --quiet >> ~/nyt.tsv
  get_nyt_images.sh | idt describe - --prompt news --provider anthropic
  idt describe - --provider florence < image_list.txt
  idt models
  idt models --provider ollama
  idt prompts
  idt stats ~/Pictures/Vacation/
  idt stats ~/Pictures/ --all                           # across entire photo library
  idt config --set default_provider=anthropic
  idt config --set default_model=claude-opus-4-6

Supported providers:
  anthropic  Claude (requires ANTHROPIC_API_KEY)
  openai     GPT-4o (requires OPENAI_API_KEY)
  ollama     Local models via Ollama (no API key)
  florence   Microsoft Florence-2 local model (no API key, GPU recommended)
        """,
    )

    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # ---------------------------------------------------------------- #
    # describe                                                           #
    # ---------------------------------------------------------------- #
    p_desc = sub.add_parser(
        "describe",
        help="Generate AI descriptions for images in a directory",
        description=(
            "Describe images in a directory. Creates a self-contained .idtw "
            "workspace bundle that holds copies of the images and their "
            "descriptions. Your original files are never modified. By default "
            "the bundle is named '<folder>.idtw' next to the source folder; use "
            "--workspace to choose a different name or location."
        ),
    )
    p_desc.add_argument(
        "source",
        help="Directory containing images, or '-' to read image paths from stdin",
    )
    p_desc.add_argument("--workspace", "-w", metavar="NAME|PATH",
                        help="Workspace bundle to create/use (default: <source>.idtw next to the folder)")
    p_desc.add_argument("--stdin", action="store_true",
                        help="Read image paths from stdin (same as passing '-' as source)")
    p_desc.add_argument("--project", metavar="DIR",
                        help="Project root when reading from stdin")
    _provider_args(p_desc)
    _prompt_args(p_desc)
    _metadata_args(p_desc)
    p_desc.add_argument("--redescribe", action="store_true",
                        help="Generate a new description even for already-described images")
    p_desc.add_argument("--limit", type=int, metavar="N",
                        help="Stop after describing N images")
    p_desc.add_argument("--embed", action="store_true",
                        help="Automatically embed descriptions into image copies after describing")
    p_desc.add_argument("--quiet", "-q", action="store_true",
                        help="Minimal output; in stdin mode, prints filename TAB description")
    p_desc.set_defaults(func=cmd_describe)

    # ---------------------------------------------------------------- #
    # download                                                           #
    # ---------------------------------------------------------------- #
    p_dl = sub.add_parser(
        "download",
        help="Download images from a URL",
        description=(
            "Download images from a web page into the .idt/downloads/ directory. "
            "Captures HTML alt text alongside each image. Use --describe to "
            "describe downloaded images immediately."
        ),
    )
    p_dl.add_argument("url", help="URL to download images from")
    p_dl.add_argument("directory", nargs="?",
                      help="Target directory (default: current directory)")
    p_dl.add_argument("--max", dest="max_images", type=int, metavar="N",
                      help="Maximum number of images to download")
    p_dl.add_argument("--min-size", metavar="WxH",
                      help="Minimum image size to download (e.g. 200x200)")
    p_dl.add_argument("--timeout", type=int, default=30,
                      help="Request timeout in seconds (default: 30)")
    p_dl.add_argument("--describe", action="store_true",
                      help="Describe downloaded images immediately")
    p_dl.add_argument("--embed", action="store_true",
                      help="Embed descriptions after describing (requires --describe)")
    _provider_args(p_dl)
    _prompt_args(p_dl)
    p_dl.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    p_dl.set_defaults(func=cmd_download)

    # ---------------------------------------------------------------- #
    # video                                                              #
    # ---------------------------------------------------------------- #
    p_vid = sub.add_parser(
        "video",
        help="Extract frames from video files and optionally describe them",
        description=(
            "Extract frames from video files into .idt/frames/. "
            "Supports interval mode (one frame every N seconds) and scene-change "
            "detection. Use --describe to describe the extracted frames."
        ),
    )
    p_vid.add_argument("source", help="Video file or directory containing video files")
    p_vid.add_argument(
        "--interval", type=float, default=5.0, metavar="SECONDS",
        help="Extract one frame every N seconds (default: 5.0)",
    )
    p_vid.add_argument(
        "--scene", type=float, default=0.0, metavar="THRESHOLD",
        help="Scene-change extraction; threshold 0-100, lower=more sensitive (e.g. --scene 30). "
             "Mutually exclusive with --interval.",
    )
    p_vid.add_argument("--max-frames", type=int, metavar="N",
                       help="Maximum frames to extract per video")
    p_vid.add_argument("--describe", action="store_true",
                       help="Describe extracted frames after extraction")
    _provider_args(p_vid)
    _prompt_args(p_vid)
    p_vid.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    p_vid.set_defaults(func=cmd_video)

    # ---------------------------------------------------------------- #
    # status                                                             #
    # ---------------------------------------------------------------- #
    p_status = sub.add_parser("status", help="Show description progress for a project")
    p_status.add_argument("source", help="Source directory")
    p_status.add_argument("--all", action="store_true",
                          help="Show all IDT projects found under this directory")
    p_status.add_argument("--json", dest="json_out", action="store_true",
                          help="Output as JSON")
    p_status.set_defaults(func=cmd_status)

    # ---------------------------------------------------------------- #
    # show                                                               #
    # ---------------------------------------------------------------- #
    p_show = sub.add_parser(
        "show",
        help="Print descriptions to stdout",
        description="Print the description for one image or all images in a directory.",
    )
    p_show.add_argument("target", help="Image file or source directory")
    p_show.add_argument("--json", dest="json_out", action="store_true",
                        help="Output as JSON (one object per line)")
    p_show.add_argument("--quiet", "-q", action="store_true")
    p_show.set_defaults(func=cmd_show)

    # ---------------------------------------------------------------- #
    # embed                                                              #
    # ---------------------------------------------------------------- #
    p_embed = sub.add_parser(
        "embed",
        help="Write descriptions into image metadata copies",
        description=(
            "Copy described images to .idt/embedded/ and write the description "
            "into EXIF ImageDescription and XMP dc:description. Source files are "
            "never modified. HEIC files are converted to JPEG in the copy."
        ),
    )
    p_embed.add_argument("source", help="Source directory")
    p_embed.add_argument("--force", action="store_true",
                         help="Re-embed even for already-embedded images")
    p_embed.add_argument("--dry-run", action="store_true",
                         help="Show what would be embedded without writing")
    p_embed.add_argument("--quiet", "-q", action="store_true")
    p_embed.set_defaults(func=cmd_embed)

    # ---------------------------------------------------------------- #
    # export                                                             #
    # ---------------------------------------------------------------- #
    p_export = sub.add_parser(
        "export",
        help="Export descriptions to HTML, CSV, or plain text",
        description="Generate a report from described images. Output goes to .idt/reports/.",
    )
    p_export.add_argument("source", help="Source directory")
    p_export.add_argument("--format", choices=["html", "csv", "txt"], default="html",
                          help="Output format (default: html)")
    p_export.add_argument("--quiet", "-q", action="store_true",
                          help="Print only the output file path")
    p_export.set_defaults(func=cmd_export)

    # ---------------------------------------------------------------- #
    # combine                                                            #
    # ---------------------------------------------------------------- #
    p_combine = sub.add_parser(
        "combine",
        help="Merge descriptions from multiple projects into one CSV",
        description=(
            "Walk a directory tree, find all .idt/ project mirrors, and merge "
            "every described image into a single CSV or TSV file. "
            "Useful for analysis across a whole photo library."
        ),
    )
    p_combine.add_argument("directory", help="Root directory to search for IDT projects")
    p_combine.add_argument("--output", metavar="FILE",
                           help="Output file (default: stdout)")
    p_combine.add_argument("--format", choices=["csv", "tsv"], default="csv",
                           help="Output format (default: csv)")
    p_combine.add_argument("--sort", choices=["date", "file", "timestamp"],
                           default="timestamp",
                           help="Sort order (default: timestamp)")
    p_combine.set_defaults(func=cmd_combine)

    # ---------------------------------------------------------------- #
    # models                                                             #
    # ---------------------------------------------------------------- #
    p_models = sub.add_parser(
        "models",
        help="Show available AI models for each provider",
    )
    p_models.add_argument("--provider", choices=["anthropic", "ollama", "openai"],
                          help="Show only this provider")
    p_models.add_argument("--ollama-host", metavar="URL",
                          default="http://localhost:11434")
    p_models.add_argument("--json", dest="json_out", action="store_true",
                          help="Output as JSON")
    p_models.set_defaults(func=cmd_models)

    # ---------------------------------------------------------------- #
    # watch                                                              #
    # ---------------------------------------------------------------- #
    p_watch = sub.add_parser(
        "watch",
        help="Monitor a directory and describe new images automatically",
        description=(
            "Describes undescribed images, then polls for new arrivals. "
            "Press Ctrl+C to stop."
        ),
    )
    p_watch.add_argument("source", help="Directory to watch")
    p_watch.add_argument("--interval", type=int, default=30, metavar="SECONDS",
                         help="Polling interval in seconds (default: 30)")
    _provider_args(p_watch)
    _prompt_args(p_watch)
    p_watch.add_argument("--quiet", "-q", action="store_true",
                         help="Output tab-separated filename/description for piping")
    p_watch.set_defaults(func=cmd_watch)

    # ---------------------------------------------------------------- #
    # prompts                                                            #
    # ---------------------------------------------------------------- #
    p_prompts = sub.add_parser("prompts", help="List available prompts")
    p_prompts.add_argument("--json", dest="json_out", action="store_true")
    p_prompts.set_defaults(func=cmd_prompts)

    # ---------------------------------------------------------------- #
    # stats                                                              #
    # ---------------------------------------------------------------- #
    p_stats = sub.add_parser(
        "stats",
        help="Show token usage and cost estimates for a project",
        description=(
            "Summarise token counts and estimated API costs across all described "
            "images, broken down by provider and model. Local models (Ollama, "
            "Florence) do not report tokens so no cost is shown for them."
        ),
    )
    p_stats.add_argument("source", help="Source directory (or parent directory with --all)")
    p_stats.add_argument("--all", action="store_true",
                         help="Scan entire directory tree for IDT projects")
    p_stats.add_argument("--json", dest="json_out", action="store_true",
                         help="Output as JSON")
    p_stats.set_defaults(func=cmd_stats)

    # ---------------------------------------------------------------- #
    # config                                                             #
    # ---------------------------------------------------------------- #
    p_config = sub.add_parser("config", help="View or set default configuration")
    p_config.add_argument("--set", dest="set_value", metavar="KEY=VALUE",
                          help="Set a config value")
    p_config.set_defaults(func=cmd_config)

    # ---------------------------------------------------------------- #
    # guide                                                              #
    # ---------------------------------------------------------------- #
    p_guide = sub.add_parser(
        "guide",
        help="Interactive setup wizard — pick provider, model, directory, and run",
        description=(
            "Step-by-step wizard that asks you to choose a provider, model, image "
            "source, prompt style, and metadata options, then shows you the exact "
            "command and optionally runs it. Screen-reader friendly — no ANSI, no "
            "spinners, numbered choices throughout."
        ),
    )
    p_guide.set_defaults(func=cmd_guide)

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
