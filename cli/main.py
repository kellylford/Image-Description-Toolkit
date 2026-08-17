#!/usr/bin/env python3
"""
idt — Image Description Toolkit CLI

Usage:
  idt guideme                       Interactive setup wizard (start here)
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
  idt update
  idt --help

Run "idt <command> --help" for command-specific options.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Optional

# Allow running as "python cli/main.py" during development without installing
_here = Path(__file__).parent.parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


def _set_console_title(title: str) -> None:
    """Update the Windows console title bar. No-op on non-Windows or on error."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass


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

    print(f"Unknown provider: {provider!r}", file=sys.stderr)
    print("Valid providers: anthropic, ollama, openai", file=sys.stderr)
    sys.exit(1)


def _resolve_prompt(args, project_config) -> tuple[str, str]:
    """
    Return (prompt_name, prompt_text).
    Priority: --prompt-text > --prompt > project default > user config default.
    """
    from idt_core.config import UserConfig, BUILT_IN_PROMPTS, DEFAULT_PROMPT_NAME

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
    text = (
        user_cfg.get_prompt_text(name)
        or BUILT_IN_PROMPTS.get(DEFAULT_PROMPT_NAME, "")
        or next(iter(BUILT_IN_PROMPTS.values()), "")
    )
    return (name, text)


def _provider_args(p: argparse.ArgumentParser) -> None:
    """Add the standard provider/model/ollama-host arguments."""
    p.add_argument(
        "--provider", choices=["anthropic", "ollama", "openai"],
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

def _mirror_source_path(source: Path, root: Path) -> Path:
    """
    Derive the workspace path for a source directory.

    Uses just the leaf name of the source, placed flat under root:
      C:\\Photos\\Vacation\\2026\\06   → root/06
      \\\\ford\\home\\Photos\\06       → root/06
      /home/kelly/Photos/Vacation      → root/Vacation

    This keeps workspace paths short and human-readable. The idt root
    (~/Documents/idt/) acts as the organizer; the bundle name comes from
    the most specific part of the source path.
    """
    name = source.resolve().name or source.name
    if not name:
        name = "workspace"
    return root / name


def _open_or_create_workspace(source: Path, workspace_arg: Optional[str]):
    """
    Resolve the .idtw bundle for a describe run.
      --workspace PATH  (contains separator or ends in .idtw) → that exact path
      --workspace NAME  (bare name)                           → NAME.idtw in default workspace root
      (omitted)                                               → mirrored path under ~/Documents/idt
    """
    from idt_core.workspace import Workspace, BUNDLE_EXT
    from idt_core.config import UserConfig

    cfg = UserConfig.load()
    if workspace_arg:
        wp = Path(workspace_arg).expanduser()
        is_bare_name = (wp.parent == Path(".")) and (BUNDLE_EXT not in workspace_arg)
        if is_bare_name:
            wp = cfg.workspace_root_path() / workspace_arg
    else:
        wp = _mirror_source_path(source, cfg.workspace_root_path())

    # Seed a brand-new workspace's copy preference from the user config default.
    # An existing workspace keeps whatever preference it already recorded.
    resolved = wp if Workspace.is_bundle(wp) else wp.with_name(wp.name + BUNDLE_EXT)
    was_new = not Workspace.is_bundle(resolved)
    ws = Workspace.open(wp)
    if was_new:
        ws.copy_originals = cfg.copy_originals
        ws.save_manifest()
    return ws


def _resolve_download_workspace(url: str, workspace_arg: Optional[str]):
    """
    Resolve the .idtw bundle for `idt download`, mirroring _open_or_create_workspace:
      <arg> PATH  (contains separator or ends in .idtw) → that exact path
      <arg> NAME  (bare name)                           → NAME.idtw in default workspace root
      (omitted)                                          → <domain>.idtw under ~/Documents/idt
    Downloads accumulate in the same per-domain (or explicitly named) workspace across
    runs, same as local-folder workspaces do for `idt describe`.
    """
    from idt_core.workspace import Workspace, BUNDLE_EXT
    from idt_core.downloader import domain_name
    from idt_core.config import UserConfig

    cfg = UserConfig.load()
    if workspace_arg:
        wp = Path(workspace_arg).expanduser()
        is_bare_name = (wp.parent == Path(".")) and (BUNDLE_EXT not in workspace_arg)
        if is_bare_name:
            wp = cfg.workspace_root_path() / workspace_arg
    else:
        wp = cfg.workspace_root_path() / domain_name(url)

    resolved = wp if Workspace.is_bundle(wp) else wp.with_name(wp.name + BUNDLE_EXT)
    was_new = not Workspace.is_bundle(resolved)
    ws = Workspace.open(wp)
    if was_new:
        ws.copy_originals = cfg.copy_originals
        ws.save_manifest()
    return ws


def _find_workspace(arg: str):
    """
    For read commands: locate an existing bundle from a user-supplied path.
    Accepts a .idtw bundle directly, a source folder with a sibling bundle,
    or a source folder whose mirrored bundle exists under ~/Documents/idt.
    Returns a Workspace or None.
    """
    from idt_core.workspace import Workspace
    from idt_core.config import UserConfig

    p = Path(arg).expanduser().resolve()

    # Direct bundle path
    if Workspace.is_bundle(p):
        return Workspace.open(p)

    # Old-style sibling bundle (backwards compatibility)
    sibling = p.parent / (p.name + ".idtw")
    if Workspace.is_bundle(sibling):
        return Workspace.open(sibling)

    # New default: mirrored path under workspace root
    root = UserConfig.load().workspace_root_path()
    mirrored = _mirror_source_path(p, root)
    candidate = mirrored.with_name(mirrored.name + ".idtw")
    if Workspace.is_bundle(candidate):
        return Workspace.open(candidate)

    return None


# ------------------------------------------------------------------ #
# describe                                                             #
# ------------------------------------------------------------------ #

def _resolve_gui_launch() -> Optional[list]:
    """Return the command prefix that launches the ImageDescriber GUI, or None.

    Frozen: a sibling ImageDescriber executable next to idt(.exe), or the macOS
    app bundle. Development: the GUI script run with the current interpreter.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        for name in ("ImageDescriber.exe", "ImageDescriber"):
            cand = exe_dir / name
            if cand.exists():
                return [str(cand)]
        app_bin = exe_dir / "ImageDescriber.app" / "Contents" / "MacOS" / "ImageDescriber"
        if app_bin.exists():
            return [str(app_bin)]
        return None
    gui = Path(__file__).resolve().parent.parent / "imagedescriber" / "imagedescriber_wx.py"
    if gui.exists():
        return [sys.executable, str(gui)]
    return None


def _launch_gui_describe(source: Path, args) -> None:
    """Launch the GUI on *source*, auto-starting the batch with this run's options.

    Blocks until the GUI exits and exits with its return code, so the invocation is
    one process lifetime — closing the GUI ends the command.
    """
    import subprocess

    launch = _resolve_gui_launch()
    if launch is None:
        print("Error: --showgui requested but the ImageDescriber GUI could not be located.",
              file=sys.stderr)
        sys.exit(1)

    cmd = launch + [str(source), "--autostart"]
    if getattr(args, "provider", None):
        cmd += ["--provider", args.provider]
    if getattr(args, "model", None):
        cmd += ["--model", args.model]
    if getattr(args, "prompt", None):
        cmd += ["--prompt", args.prompt]
    if getattr(args, "geocode", False):
        cmd += ["--geocode"]
    _copy = getattr(args, "copy_originals", None)
    if _copy is True:
        cmd += ["--copy-originals"]
    elif _copy is False:
        cmd += ["--no-copy-originals"]

    if not getattr(args, "quiet", False):
        print(f"Launching ImageDescriber on {source} …")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def cmd_describe(args):
    from idt_core.pipeline import WorkspacePipeline, RunOptions
    from idt_core.progress import Progress
    from idt_core.config import UserConfig

    stdin_mode = getattr(args, "stdin", False) or args.source == "-"
    if stdin_mode:
        _cmd_describe_stdin(args)
        return

    source = Path(args.source).resolve()

    # --showgui: hand the whole run to the GUI. The GUI IS the invocation from here —
    # it opens on the directory, auto-starts the batch, and shows live progress; when
    # it closes, this command returns. We do NOT also run a headless pipeline.
    if getattr(args, "showgui", False):
        if not source.is_dir():
            print("Error: --showgui requires a source directory.", file=sys.stderr)
            sys.exit(1)
        _launch_gui_describe(source, args)
        return

    # Allow passing a workspace bundle directly to resume an interrupted run.
    # The user may not remember the original source folder but always has the bundle.
    from idt_core.workspace import Workspace
    if Workspace.is_bundle(source):
        ws = Workspace.open(source)
        source = None  # no source folder to scan
    elif not source.is_dir():
        print(f"Error: not a directory or workspace bundle: {source}", file=sys.stderr)
        sys.exit(1)
    else:
        ws = _open_or_create_workspace(source, getattr(args, "workspace", None))
    user_cfg = UserConfig.load()

    # Only inherit provider/model from the workspace manifest if this workspace
    # has previously had at least one successful description.  Without this guard,
    # a completely-failed run that already saved its provider would override the
    # user's default on every subsequent run — even after changing the default.
    _ws_provider = ws.defaults.provider if ws.has_any_descriptions else ""
    _ws_model    = ws.defaults.model    if ws.has_any_descriptions else ""
    provider_name = args.provider or _ws_provider or user_cfg.default_provider
    model         = args.model    or _ws_model    or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, ws.defaults)

    # Resolve the effective copy setting: explicit --copy-originals/--no-copy-originals
    # flag for this run overrides the workspace's stored preference.
    _copy_flag = getattr(args, "copy_originals", None)
    if _copy_flag is not None:
        ws.copy_originals = _copy_flag

    # Add this run's source images to the bundle (idempotent; originals never modified).
    # copy_originals decides whether they are copied in or referenced in place.
    # Skipped when the user passed a workspace bundle directly (source is None).
    if not args.quiet:
        if source:
            print(f"Source:     {source}")
        print(f"Workspace:  {ws.path}")
        print(f"Copy mode:  {'copy originals into workspace' if ws.copy_originals else 'reference in place'}")
    if source is not None:
        added = ws.add_source_folder(source, recursive=True, copy=ws.copy_originals)

        # Extract video frames and add them to the workspace (opt out with --no-video)
        if not getattr(args, "no_video", False):
            _extract_videos_into_workspace(ws, source, args)

    if not args.quiet:
        total_items = len(ws.media_items())
        print(f"Images:     {total_items} in workspace")
        print(f"Provider:   {provider_name}  model: {model}")
        print(f"Prompt:     {prompt_name}")
        if args.extract_metadata:
            gcstr = " + geocoding" if args.geocode else ""
            print(f"Metadata:   EXIF extraction enabled{gcstr}")
        print()

    # Record this invocation so users can find the exact command later.
    # When called from guideme, _command_parts holds the full built command.
    from datetime import datetime, timezone
    _parts = getattr(args, "_command_parts", None) or (["idt"] + sys.argv[1:])
    _ts = datetime.now(timezone.utc).isoformat()
    ws.cli_commands.append({"command": shlex.join(_parts), "timestamp": _ts})

    # Save prompt/geocode now; provider+model only saved after a successful run
    # so a completely-failed run doesn't poison the workspace with a bad provider.
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

    # Checking every referenced original for existence walks the whole library,
    # which is slow on a network share. Say so rather than leaving the previous
    # stage's title up while it runs.
    _set_console_title("IDT - Preparing (checking images)")

    all_items = ws.media_items()

    # Reference-mode originals may have moved or been deleted since they were added.
    # Mark those missing, skip them, and report the count in the summary rather than
    # letting each one fail as a read error mid-batch.
    missing = [i for i in all_items if not ws.image_path(i).exists()]
    for m in missing:
        if not m.is_missing:
            m.is_missing = True
            ws.save_item(m)
    available = [i for i in all_items if not i.is_missing]
    if missing and not args.quiet:
        print(f"Missing:    {len(missing)} referenced original(s) not found on disk — skipping")

    queue = available if args.redescribe else [i for i in available if not i.described]
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

    _total = len(queue)
    _set_console_title(f"IDT - Describing Images (0%, 0 of {_total})")

    described = errors = 0
    pipeline = WorkspacePipeline(ws, provider)

    _show = getattr(args, "show_descriptions", False)
    for event in pipeline.run(options):
        if event.success:
            described += 1
            extra = ""
            if not args.quiet and event.metadata:
                # Display only — includes the camera, which prompt_context() omits.
                ctx = event.metadata.display_context()
                if ctx:
                    extra = f"  [{ctx}]"
            progress.update(event.item.display_name, success=True, note=extra)
            if _show and event.item.descriptions:
                print(event.item.descriptions[-1].text)
                print()
        else:
            errors += 1
            progress.update(event.item.display_name, success=False, error=event.error)
        _done = described + errors
        _pct = int(_done / _total * 100) if _total else 0
        _set_console_title(f"IDT - Describing Images ({_pct}%, {_done} of {_total})")

    progress.summary(described=described, errors=errors)
    if missing and not args.quiet:
        print(f"Skipped {len(missing)} missing original(s) not found on disk.")
    _set_console_title(f"IDT - Image Description Complete ({described} of {_total})")

    if described > 0:
        ws.defaults.provider = provider_name
        ws.defaults.model = model
        ws.has_any_descriptions = True
        ws.save_manifest()

    if args.embed and described > 0:
        print()
        _do_embed_workspace(ws, force=False, dry_run=False, quiet=args.quiet)

    # Auto-export HTML report (default on; opt out with --no-export)
    if not getattr(args, "no_export", False) and described > 0:
        _auto_export_workspace(ws, args.quiet)


def _extract_one_video_into_workspace(ws, video: Path, opts,
                                      source_root: Path = None) -> list:
    """
    Extract one video's frames into ws.derived_dir("frames")/<stem>/ and register
    the video (reference item) plus each frame (extracted_frame item) in the
    workspace. Returns the list of frame WorkspaceItems (for describing).

    Raises ImportError if opencv-python is not installed.
    """
    from idt_core.video import extract_frames_to_dir
    from idt_core.workspace import WorkspaceItem

    frames_dir = ws.derived_dir("frames") / video.stem
    result = extract_frames_to_dir(video, frames_dir, opts)

    # Register the video as a reference-mode item (no copy — videos are large).
    #
    # subfolder must be set here explicitly. This is the one place an item is
    # built by hand instead of through add_image(), so it was missed when the
    # four inline subfolder computations were unified on
    # source_relative_subfolder() -- and add_source_folder() defaults to
    # include_videos=False, so nothing else ever assigned one.
    #
    # The result was a CLI bundle whose photos grouped under "07" while its
    # videos carried subfolder=None and hung off the tree root, so the folder
    # node held only part of the folder. The GUI's own scan
    # (on_files_discovered) anchors every discovered file including videos, so
    # the same folder opened as two different shapes depending on which side
    # created the workspace.
    from idt_core.workspace import source_relative_subfolder

    video_subfolder = (
        source_relative_subfolder(video, source_root) if source_root else None
    )
    video_wi = ws.get_item(video.name, video_subfolder)
    if video_wi is None:
        video_wi = WorkspaceItem(
            image=video.name,
            source_path=str(video),
            storage="reference",
            item_type="video",
            subfolder=video_subfolder,
            is_missing=not video.exists(),
        )
        ws.save_item(video_wi)
    video_gui_path = str(ws.image_path(video_wi))

    frame_items = []
    frame_paths = []
    for frame_path in result.frame_paths:
        # Frames already live in derived/frames/ — reference them there rather
        # than copying into images/ (that would duplicate every frame).
        frame_wi = ws.add_image(frame_path, subfolder=f"frames/{video.stem}", copy=False)
        frame_wi.item_type = "extracted_frame"
        frame_wi.parent_video = video_gui_path
        ws.save_item(frame_wi)
        frame_items.append(frame_wi)
        frame_paths.append(str(ws.image_path(frame_wi)))

    # Store the frame list on the video so the GUI can show the frame count.
    video_wi.extra["extracted_frames"] = frame_paths
    ws.save_item(video_wi)
    return frame_items


def _extract_videos_into_workspace(ws, source: Path, args) -> None:
    """Scan source for videos, extract frames, and add them to the workspace."""
    from idt_core.video import scan_videos, VideoExtractionOptions
    videos = list(scan_videos(source))
    if not videos:
        return
    if not args.quiet:
        print(f"Videos:     {len(videos)} file(s) found — extracting frames")
    interval = getattr(args, "video_interval", 5.0)
    opts = VideoExtractionOptions(mode="interval", interval_seconds=interval)
    total_frames = 0
    cv_missing = False
    # Extraction can run for many minutes on a large library, and until it
    # finishes cmd_describe has not reached its own title updates. Without this
    # the window still reads whatever the dispatcher set on startup -- "IDT -
    # Setup Wizard" for a guideme run -- for the entire extraction, which reads
    # as a hung wizard rather than work in progress.
    _set_console_title(f"IDT - Extracting Video Frames (0 of {len(videos)})")
    for _n, video in enumerate(videos, start=1):
        try:
            frame_items = _extract_one_video_into_workspace(ws, video, opts, source)
            total_frames += len(frame_items)
            _set_console_title(
                f"IDT - Extracting Video Frames ({_n} of {len(videos)}, "
                f"{total_frames} frames)"
            )
            if not args.quiet:
                print(f"  {video.name}: {len(frame_items)} frames")
        except ImportError:
            cv_missing = True
            break
        except Exception as exc:
            if not args.quiet:
                print(f"  {video.name}: skipped ({exc})")
    if cv_missing and not args.quiet:
        print("  Skipping video extraction: opencv-python not installed")
        print("  Install with: pip install opencv-python")
    elif total_frames and not args.quiet:
        print(f"  {total_frames} frames added to workspace")
    if not args.quiet:
        print()


def _auto_export_workspace(ws, quiet: bool) -> None:
    """Generate HTML report and tell the user where to find it."""
    try:
        from idt_core.exporter import export_workspace_html
        html_path = export_workspace_html(ws)
        if not quiet:
            print()
            print(f"Report:     {html_path}")
            print(f"Logs:       {ws.logs_dir}")
    except Exception as exc:
        if not quiet:
            print(f"\nWarning: could not generate HTML report: {exc}")


def _cmd_describe_stdin(args):
    """
    Describe image paths read from stdin, one per line, into a .idtw workspace.
    Pipeline use: get_nyt_images.bat | idt describe - --prompt aialttext
    """
    from idt_core.workspace import source_relative_subfolder
    from idt_core.pipeline import WorkspacePipeline, RunOptions
    from idt_core.progress import Progress
    from idt_core.config import UserConfig

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
    ws = _open_or_create_workspace(source, getattr(args, "workspace", None))
    user_cfg = UserConfig.load()

    _ws_provider = ws.defaults.provider if ws.has_any_descriptions else ""
    _ws_model    = ws.defaults.model    if ws.has_any_descriptions else ""
    provider_name = args.provider or _ws_provider or user_cfg.default_provider
    model         = args.model    or _ws_model    or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, ws.defaults)
    provider = _make_provider(provider_name, model, args.ollama_host)

    # Add each stdin image to the workspace (idempotent), mirroring its position
    # under the common source root as a subfolder. copy_originals decides copy vs
    # reference; originals are never modified either way.
    items = []
    for img_path in paths:
        items.append(ws.add_image(
            img_path,
            subfolder=source_relative_subfolder(img_path, source),
            copy=ws.copy_originals,
        ))

    if not args.quiet:
        print(f"Workspace: {ws.path}")
        print(f"Provider:  {provider_name}  model: {model}")
        print(f"Images:    {len(items)} from stdin")
        print()

    ws.defaults.prompt_name = prompt_name
    ws.geocode_enabled = bool(args.geocode)
    ws.save_manifest()

    options = RunOptions(
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        redescribe=args.redescribe,
        extract_metadata=args.extract_metadata,
        geocode=args.geocode,
    )
    progress = Progress(total=len(items), quiet=args.quiet)
    described = errors = 0
    pipeline = WorkspacePipeline(ws, provider)

    for event in pipeline.run_items(items, options):
        if event.success:
            described += 1
            progress.update(event.item.display_name, success=True)
            if args.quiet and event.item.descriptions:
                # Pipeline-friendly output: original source path TAB description
                print(f"{event.item.source_path}\t{event.item.descriptions[-1].text}")
        else:
            errors += 1
            progress.update(event.item.display_name, success=False, error=event.error)

    progress.summary(described=described, errors=errors)

    if described > 0:
        ws.defaults.provider = provider_name
        ws.defaults.model = model
        ws.has_any_descriptions = True
        ws.save_manifest()


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
    Download images from a URL into a workspace, and optionally describe them.

    idt download https://www.nytimes.com/ --max 20 --describe --prompt aialttext
    """
    from idt_core.downloader import download_into_workspace
    from idt_core.config import UserConfig

    cfg = UserConfig.load()
    ws = _resolve_download_workspace(args.url, args.directory)

    if not args.quiet:
        print(f"URL:       {args.url}")
        print(f"Workspace: {ws.path}")
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

    def _on_progress(i: int, total: int, url: str) -> None:
        if not args.quiet:
            pct = int(i / total * 100) if total else 0
            print(f"  {i} of {total}  {pct}%  {url[:60]}", end="\r", flush=True)

    try:
        result = download_into_workspace(
            ws, args.url,
            min_width=min_w, min_height=min_h,
            timeout=args.timeout, max_images=args.max_images,
            on_progress=_on_progress,
        )
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Install with: pip install requests beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print()  # clear progress line

    print(f"Downloaded: {result.downloaded} images  skipped: {result.skipped}  failed: {result.failed}")
    print(f"Location:  {ws.derived_dir(result.subfolder)}")

    # Explicit --preserve-alt-text/--no-preserve-alt-text overrides the user's
    # configured default (`idt config --set preserve_alt_text=...`, on by default).
    preserve_alt_text = (
        args.preserve_alt_text if args.preserve_alt_text is not None else cfg.preserve_alt_text
    )
    n_alt = sum(1 for i in result.items if i.alt_text)
    if n_alt and not args.quiet:
        suffix = " (saved as a description)" if preserve_alt_text else ""
        print(f"Alt texts: {n_alt} images had existing alt text from the site{suffix}")

    # Record alt text as its own description before describing, so it shows up in
    # history alongside the AI-generated one — filtered to reject bare filenames
    # used as alt text (matches the old GUI's "Website Alt Text" heuristic).
    if preserve_alt_text:
        from idt_core.workspace import WorkspaceDescription
        for item in result.items:
            alt = item.alt_text
            if alt and len(alt) >= 3 and " " in alt:
                item.add_description(WorkspaceDescription.create(
                    text=alt, model="Website Alt Text", provider="website", prompt_name="alt_text",
                ))
                ws.save_item(item)

    # Auto-describe the downloaded images if requested
    if args.describe and result.downloaded > 0:
        print()
        from idt_core.pipeline import WorkspacePipeline, RunOptions
        from idt_core.progress import Progress

        # Only inherit provider/model from the workspace once it has a real
        # description history (same guard cmd_describe uses).
        _ws_provider = ws.defaults.provider if ws.has_any_descriptions else ""
        _ws_model = ws.defaults.model if ws.has_any_descriptions else ""
        provider_name = args.provider or _ws_provider or cfg.default_provider
        model = args.model or _ws_model or cfg.default_model
        prompt_name, prompt_text = _resolve_prompt(args, ws.defaults)
        provider = _make_provider(provider_name, model, args.ollama_host)

        if not args.quiet:
            print(f"Describing {result.downloaded} images with {provider_name} / {model}...")
            print()

        options = RunOptions(
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            extract_metadata=False,  # downloaded images don't have EXIF
            # Freshly downloaded images should always get an AI description,
            # even when a "Website Alt Text" description was just seeded above
            # (otherwise the undescribed-only queue would skip every image whose
            # alt text we preserved). Scoped to just this batch via run_items(),
            # so it never touches other, already-described images sharing this
            # workspace.
            redescribe=args.redescribe,
        )
        progress = Progress(total=result.downloaded, quiet=args.quiet)
        described = errors = 0
        pipeline = WorkspacePipeline(ws, provider)

        for event in pipeline.run_items(result.items, options):
            if event.success:
                described += 1
                progress.update(event.item.display_name, success=True)
            else:
                errors += 1
                progress.update(event.item.display_name, success=False, error=event.error)

        progress.summary(described=described, errors=errors)

        if described > 0:
            ws.defaults.provider = provider_name
            ws.defaults.model = model
            ws.has_any_descriptions = True
            ws.save_manifest()

        if described > 0 and args.embed:
            print()
            _do_embed_workspace(ws, force=False, dry_run=False, quiet=args.quiet)

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
    from idt_core.video import VideoExtractionOptions, scan_videos
    from idt_core.scanner import is_video

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Error: not found: {source}", file=sys.stderr)
        sys.exit(1)

    # Frames and descriptions land in a .idtw workspace under the workspace root
    # (~/Documents/idt), the same model idt describe uses — never a sibling .idt/.
    ws = _open_or_create_workspace(
        source if source.is_dir() else source.parent, getattr(args, "workspace", None)
    )

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
        print(f"Workspace: {ws.path}")
        print(f"Videos:    {len(videos)}")
        print(f"Mode:      {mode}  ({'every ' + str(args.interval) + 's' if mode == 'interval' else 'threshold ' + str(args.scene)})")
        print()

    all_frame_items = []
    for video in videos:
        if not args.quiet:
            print(f"  Extracting frames: {video.name}")
        try:
            frame_items = _extract_one_video_into_workspace(ws, video, opts, source)
            all_frame_items.extend(frame_items)
            if not args.quiet:
                print(f"    {len(frame_items)} frames -> {ws.derived_dir('frames') / video.stem}")
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("Install with: pip install opencv-python", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"  Error processing {video.name}: {e}", file=sys.stderr)

    total_frames = len(all_frame_items)
    if not args.quiet:
        print(f"\nExtracted {total_frames} frames total.")

    if args.describe and total_frames > 0:
        print()
        from idt_core.pipeline import WorkspacePipeline, RunOptions
        from idt_core.progress import Progress
        from idt_core.config import UserConfig

        user_cfg = UserConfig.load()
        _ws_provider = ws.defaults.provider if ws.has_any_descriptions else ""
        _ws_model    = ws.defaults.model    if ws.has_any_descriptions else ""
        provider_name = args.provider or _ws_provider or user_cfg.default_provider
        model         = args.model    or _ws_model    or user_cfg.default_model
        prompt_name, prompt_text = _resolve_prompt(args, ws.defaults)
        provider = _make_provider(provider_name, model, args.ollama_host)

        if not args.quiet:
            print(f"Describing {total_frames} frames with {provider_name} / {model}...")
            print()

        ws.defaults.prompt_name = prompt_name
        ws.save_manifest()

        options = RunOptions(
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            extract_metadata=False,  # extracted frames carry no EXIF
            redescribe=args.redescribe,
        )
        progress = Progress(total=total_frames, quiet=args.quiet)
        described = errors = 0
        pipeline = WorkspacePipeline(ws, provider)
        for event in pipeline.run_items(all_frame_items, options):
            if event.success:
                described += 1
                progress.update(event.item.display_name, success=True)
            else:
                errors += 1
                progress.update(event.item.display_name, success=False, error=event.error)
        progress.summary(described=described, errors=errors)

        if described > 0:
            ws.defaults.provider = provider_name
            ws.defaults.model = model
            ws.has_any_descriptions = True
            ws.save_manifest()


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
        if ws.cli_commands:
            print()
            print("Commands run:")
            for entry in ws.cli_commands:
                ts = entry.get("timestamp", "")[:16].replace("T", " ")
                print(f"  [{ts}]  {entry.get('command', '')}")
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

    # Prefer a .idtw bundle.  Walk up the tree checking two things each level:
    # 1. Whether candidate itself is a bundle (target is inside the bundle's images/)
    # 2. Whether a sibling bundle exists whose items reference this file as source_path
    candidate = target.parent
    target_str = str(target)
    while True:
        # Case 1: target lives inside a bundle (e.g. 09.idtw/images/photo.jpg)
        if Workspace.is_bundle(candidate):
            ws = Workspace.open(candidate)
            for item in ws.items():
                if item.image == target.name:
                    _print_item(item, args)
                    return
        # Case 2: sibling bundle whose workspace was created from the same source folder
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

    # Last resort: the workspace may be at a mirrored location (e.g. ~/Documents/idt/).
    # _find_workspace walks workspace directories that reference the same source.
    ws = _find_workspace(str(target.parent))
    if ws is not None:
        for item in ws.items():
            if item.source_path == target_str or item.image == target.name:
                _print_item(item, args)
                return

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
    from idt_core.scanner import is_heic

    errors = []
    for item in pending:
        desc = item.active_description
        if not desc:
            continue
        if dry_run:
            n += 1
            continue
        try:
            src = ws.image_path(item)
            orig_name = Path(item.source_path).name if item.source_path else item.image
            sub = item.subfolder
            if is_heic(src):
                converted = ws.derived_dir("converted") / Path(item.image).with_suffix(".jpg").name
                if converted.exists():
                    src = converted
                out_name = Path(orig_name).stem + ".jpg"
            else:
                out_name = orig_name
            dst = out_dir / sub / out_name if (sub and sub not in (".", "")) else out_dir / out_name
            embed_image_file(src, desc.text, dst)
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
    fmt = args.format
    ws = _find_workspace(args.source)

    try:
        if ws is not None:
            from idt_core.exporter import (
                export_workspace_html, export_workspace_csv, export_workspace_txt,
            )
            exporters = {"html": export_workspace_html, "csv": export_workspace_csv,
                         "txt": export_workspace_txt}
            if fmt not in exporters:
                print(f"Unknown format: {fmt!r}", file=sys.stderr)
                sys.exit(1)
            out = exporters[fmt](ws)
        else:
            # Legacy .idt/ project fallback
            from idt_core.project import Project
            from idt_core.exporter import export_html, export_csv, export_txt
            source = Path(args.source).resolve()
            if not source.is_dir():
                print(f"Error: no workspace found at: {source}", file=sys.stderr)
                sys.exit(1)
            project = Project.open(source)
            exporters = {"html": export_html, "csv": export_csv, "txt": export_txt}
            if fmt not in exporters:
                print(f"Unknown format: {fmt!r}", file=sys.stderr)
                sys.exit(1)
            out = exporters[fmt](project)
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
    from idt_core.workspace import Workspace

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    rows = []

    def _add(item, desc, container):
        rows.append({
            "file": item.display_name,
            "source_path": str(item.source_path),
            "workspace": str(container),
            "description": desc.text,
            "model": desc.model,
            "provider": desc.provider,
            "prompt_name": desc.prompt_name,
            "timestamp": _desc_when(desc),
            "metadata_context": desc.metadata_context or "",
            "input_tokens": desc.input_tokens or "",
            "output_tokens": desc.output_tokens or "",
            "alt_text": getattr(item, "alt_text", "") or "",
        })

    # New-style .idtw bundles
    for bundle in sorted(root.rglob("*.idtw")):
        if not Workspace.is_bundle(bundle):
            continue
        try:
            ws = Workspace.open(bundle)
            for item in ws.items():
                if item.described:
                    _add(item, item.active_description, bundle)
        except Exception as e:
            print(f"Warning: could not read {bundle}: {e}", file=sys.stderr)

    # Legacy .idt/ projects
    for idt_dir in sorted(root.rglob("*.idt")):
        source = idt_dir.parent / idt_dir.stem
        if not source.is_dir():
            continue
        try:
            for item in Project.open(source).described():
                if item.active_description:
                    _add(item, item.active_description, source)
        except Exception as e:
            print(f"Warning: could not read {idt_dir}: {e}", file=sys.stderr)

    if not rows:
        print(f"No described images found under: {root}")
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

def _api_model_results(provider: str, args) -> dict:
    """Model listing for one of the API-backed providers (Claude, OpenAI).

    Cache-first, like every picker: whatever the catalog already knows is the
    answer, and a refresh is attempted only when the cache has expired or
    ``--refresh`` asked for one. That keeps `idt models` fast on the common path
    and, more importantly, keeps it working with no network at all.
    """
    from idt_core.keys import ENV_VARS, key_source, resolve_api_key
    from idt_core.providers import catalog

    if not resolve_api_key(provider):
        # Resolved through keys.py rather than os.environ: this used to check
        # the environment variable directly and so reported "no key" for anyone
        # whose key lived in the Windows Credential Manager or the config file.
        return {"status": "no_key", "models": [], "details": [],
                "env_var": ENV_VARS.get(provider, "")}

    refreshed = None
    if getattr(args, "refresh", False):
        catalog.invalidate(provider)
        refreshed = catalog.refresh_models(
            provider, include_all=getattr(args, "all_models", False), force=True
        )
    elif catalog.is_stale(provider):
        refreshed = catalog.refresh_if_stale(
            provider, include_all=getattr(args, "all_models", False)
        )

    entries = catalog.cached_models(provider)
    return {
        "status": "live" if refreshed is not None else "cached",
        "models": [entry.id for entry in entries],
        "details": [
            {
                "id": entry.id,
                "name": entry.name,
                "source": entry.source,
                "context_window": entry.context_window,
                "max_output": entry.max_output,
                "recommended": entry.recommended,
            }
            for entry in entries
        ],
        "key_source": key_source(provider) or "",
    }


def cmd_models(args):
    """
    Check which AI models are available.

    idt models                      — check all providers
    idt models --provider ollama    — list Ollama models
    idt models --provider anthropic — list Claude models for this account
    idt models --refresh            — ignore the cache and ask the APIs now
    idt models --all                — skip the OpenAI chat-model filter
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

    # Anthropic / OpenAI. Both go through the model catalog, which asks the
    # provider's own /v1/models endpoint and merges the answer with our curated
    # metadata (issue #267).
    for name, canonical in (("anthropic", "claude"), ("openai", "openai")):
        if args.provider and args.provider != name:
            continue
        try:
            results[name] = _api_model_results(canonical, args)
        except Exception as e:                                  # noqa: BLE001
            results[name] = {"status": "error", "error": str(e), "models": []}

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
        elif status in ("live", "cached"):
            freshness = "from the API" if status == "live" else "cached"
            print(f"\n{provider} ({len(models)} models, {freshness}):")
            for detail in info.get("details", []):
                label = detail["name"] or detail["id"]
                notes = []
                if detail["source"] == "live":
                    notes.append("new — details unknown")
                if detail["recommended"]:
                    notes.append("recommended")
                suffix = f"  ({', '.join(notes)})" if notes else ""
                if label != detail["id"]:
                    print(f"    {detail['id']}  —  {label}{suffix}")
                else:
                    print(f"    {detail['id']}{suffix}")
        elif status == "no_key":
            env_var = info.get("env_var") or "the provider's API key"
            print(f"\n{provider}: no API key ({env_var} not set)")
        else:
            print(f"\n{provider}: error — {info.get('error', 'unknown')}")


# ------------------------------------------------------------------ #
# chat                                                                 #
# ------------------------------------------------------------------ #

def _chat_default_model(provider: str) -> str:
    """Canonical default model for a provider.

    For the API providers this is the module default, *if the account still has
    it*. A hardcoded default that the provider has since retired is the exact
    failure issue #267 is about: it looks fine until the first request comes back
    as an API error. When the catalog knows the default is gone, the first
    recommended model that does exist is used instead.
    """
    if provider in ("claude", "openai"):
        if provider == "claude":
            from idt_core.providers.claude import DEFAULT_MODEL
        else:
            from idt_core.providers.openai_provider import DEFAULT_MODEL

        try:
            from idt_core.providers import catalog

            entries = catalog.cached_models(provider)
            if any(entry.id == DEFAULT_MODEL for entry in entries):
                return DEFAULT_MODEL
            for entry in entries:
                if entry.recommended:
                    return entry.id
            if entries:
                return entries[0].id
        except Exception:
            # The catalog is an improvement on the module default, never a
            # prerequisite for having one.
            pass
        return DEFAULT_MODEL
    from idt_core.providers.ollama import OllamaProvider, DEFAULT_MODEL
    try:
        # Chat-capable models, not vision-capable ones: this default is for
        # `idt chat`, where a text-only model is a perfectly good pick.
        available = OllamaProvider(model=DEFAULT_MODEL).list_chat_models()
        if available:
            return available[0]
    except Exception:
        # Ollama may not be running, or may not be installed at all. Fall
        # through to the module default so `idt chat --model X` still works
        # without a live service to enumerate.
        pass
    return DEFAULT_MODEL


def _chat_stream_turn(engine, text, options, quiet=False, attachments=(),
                      show_thinking=False):
    """Run one turn, printing deltas as they arrive.

    Ctrl+C cancels the turn rather than the program: the generator is closed,
    the provider's stream is released, and whatever text arrived is kept.
    Returns True if the turn completed, False if it was cancelled or failed.
    """
    from idt_core.chat import (
        ChatCancelled, ChatDelta, ChatFailed, ChatFinished, ChatRetrying,
        ChatStarted, ChatThinking, ChatToolCall, ChatToolResult,
    )

    generator = engine.send(text, attachments, options)
    completed = False
    thinking_noted = False
    try:
        for event in generator:
            if isinstance(event, ChatDelta):
                sys.stdout.write(event.text)
                sys.stdout.flush()
            elif isinstance(event, ChatThinking):
                # Thinking goes to stderr so piping stdout still yields only
                # the answer. Without --show-thinking, one note explains the
                # silence instead of pages of scratch work.
                if show_thinking:
                    sys.stderr.write(event.text)
                    sys.stderr.flush()
                elif not thinking_noted and not quiet:
                    print("[thinking…]", file=sys.stderr)
                    thinking_noted = True
            elif isinstance(event, ChatStarted):
                if event.dropped_messages and not quiet:
                    print(
                        f"[dropped {event.dropped_messages} oldest turn(s) to fit "
                        f"the context window]",
                        file=sys.stderr,
                    )
            elif isinstance(event, ChatToolCall):
                if not quiet:
                    print(f"[{event.describe()}]", file=sys.stderr)
            elif isinstance(event, ChatToolResult):
                if not quiet and event.summary:
                    print(f"[{event.summary}]", file=sys.stderr)
            elif isinstance(event, ChatRetrying):
                print(
                    f"\n[{event.error} — retrying, attempt {event.attempt}]",
                    file=sys.stderr,
                )
            elif isinstance(event, ChatFailed):
                print(f"\nError: {event.error}", file=sys.stderr)
            elif isinstance(event, (ChatFinished, ChatCancelled)):
                completed = isinstance(event, ChatFinished)
                print()
    except KeyboardInterrupt:
        generator.close()
        print("\n[stopped — partial response kept]", file=sys.stderr)
    return completed


def cmd_chat(args):
    """
    Talk to an AI model from the terminal.

    idt chat                                   — interactive session
    idt chat --message "explain HEIC"          — one-shot
    idt chat --provider claude --system "Be terse."
    idt chat --list                            — saved conversations
    idt chat --resume chat_a1b2c3              — continue one
    """
    from idt_core.chat import (
        ChatEngine, ChatOptions, ChatSession, DirectoryChatStore,
    )
    from idt_core.chat.providers import create_chat_provider
    from idt_core.keys import missing_key_message, requires_api_key, resolve_api_key
    from idt_core.providers.registry import capabilities_for

    store = None if args.no_save else DirectoryChatStore()

    if args.list_sessions:
        sessions = DirectoryChatStore().list_sessions()
        if not sessions:
            print("No saved conversations.")
            return
        print(f"{len(sessions)} saved conversation(s):\n")
        for session in sessions:
            turns = sum(1 for m in session.messages if m.role == "user")
            stamp = (session.modified or "")[:16].replace("T", " ")
            print(f"  {session.id}  {stamp}  {turns:>3} turn(s)  "
                  f"{session.display_title()}")
        return

    # Resume or start fresh.
    if args.resume:
        session = DirectoryChatStore().load(args.resume)
        if session is None:
            print(f"Error: no saved conversation with id {args.resume!r}",
                  file=sys.stderr)
            sys.exit(1)
    else:
        session = ChatSession()

    provider_name = args.provider or session.provider or "ollama"
    canonical = capabilities_for(provider_name).provider
    if canonical == "unknown":
        canonical = provider_name.lower()

    model = args.model or (session.model if not args.provider else "") \
        or _chat_default_model(canonical)

    if args.system is not None:
        session.system_prompt = args.system

    api_key = resolve_api_key(canonical)
    if requires_api_key(canonical) and not api_key:
        print(f"Error: {missing_key_message(canonical)}", file=sys.stderr)
        sys.exit(1)

    provider = create_chat_provider(canonical, model, api_key)
    engine = ChatEngine(session, provider, store)

    web_search = bool(getattr(args, "web_search", False))
    if web_search:
        from idt_core.chat.tools import missing_web_key_message, web_search_available

        if canonical != "ollama":
            print("Warning: --web-search only works with --provider ollama; "
                  "ignoring it.", file=sys.stderr)
            web_search = False
        elif not web_search_available():
            # Warn now, at the prompt, rather than mid-answer via a failed
            # tool call — but keep going: the model can still chat without it.
            print(f"Warning: {missing_web_key_message()}", file=sys.stderr)

    options = ChatOptions(
        max_output_tokens=args.max_tokens,
        temperature=args.temperature,
        web_search=web_search,
        thinking=getattr(args, "thinking", None),
    )
    show_thinking = bool(getattr(args, "show_thinking", False))

    # Attachments, prepared through the same code the GUIs use so limits,
    # HEIC conversion and provider support behave identically everywhere.
    attachments = []
    if args.attach:
        from idt_core.chat import prepare_attachments

        attachments, _converted, errors = prepare_attachments(
            args.attach, canonical)
        for problem in errors:
            print(f"Warning: {problem}", file=sys.stderr)
        if not attachments and not args.message:
            print("Error: no attachments could be prepared", file=sys.stderr)
            sys.exit(1)

    # One-shot.
    if args.message:
        ok = _chat_stream_turn(engine, args.message, options, quiet=args.quiet,
                               attachments=attachments,
                               show_thinking=show_thinking)
        if store and not args.quiet:
            print(f"[saved as {session.id}]", file=sys.stderr)
        sys.exit(0 if ok else 1)

    # Interactive.
    print(f"idt chat — {canonical} / {model}")
    if session.messages:
        print(f"Resumed {session.id} ({len(session.messages)} messages)")
    print("Type your message and press Enter. Ctrl+C stops a reply; "
          "Ctrl+D or /quit exits.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit"):
            break
        if line == "/system":
            print(session.system_prompt or "(no system prompt)")
            continue
        if line.startswith("/system "):
            session.system_prompt = line[len("/system "):].strip()
            print(f"[system prompt set]")
            continue
        if line == "/tokens":
            print(f"context {session.context_tokens:,} · "
                  f"billed {session.billed_tokens:,}")
            continue
        # Attachments ride along with the first message only; the model has
        # seen them by the second turn and re-sending would just re-upload.
        _chat_stream_turn(engine, line, options, quiet=args.quiet,
                          attachments=attachments,
                          show_thinking=show_thinking)
        attachments = []

    if store and session.messages:
        print(f"Saved as {session.id}", file=sys.stderr)


# ------------------------------------------------------------------ #
# watch                                                                #
# ------------------------------------------------------------------ #

def cmd_watch(args):
    import time
    from idt_core.workspace import source_relative_subfolder
    from idt_core.pipeline import WorkspacePipeline, RunOptions
    from idt_core.scanner import scan_images
    from idt_core.config import UserConfig

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"Error: not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    # New images described here land in a .idtw workspace under the workspace root
    # (~/Documents/idt), the same model idt describe uses — never a sibling .idt/.
    ws = _open_or_create_workspace(source, getattr(args, "workspace", None))
    user_cfg = UserConfig.load()

    _ws_provider = ws.defaults.provider if ws.has_any_descriptions else ""
    _ws_model    = ws.defaults.model    if ws.has_any_descriptions else ""
    provider_name = args.provider or _ws_provider or user_cfg.default_provider
    model         = args.model    or _ws_model    or user_cfg.default_model
    prompt_name, prompt_text = _resolve_prompt(args, ws.defaults)
    provider = _make_provider(provider_name, model, args.ollama_host)

    if not args.quiet:
        print(f"Watching:  {source}")
        print(f"Workspace: {ws.path}")
        print(f"Provider:  {provider_name}  model: {model}")
        print(f"Interval:  {args.interval}s  prompt: {prompt_name}")
        print("Press Ctrl+C to stop.\n")

    ws.defaults.prompt_name = prompt_name
    ws.save_manifest()
    options = RunOptions(
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        extract_metadata=getattr(args, "extract_metadata", True),
        geocode=getattr(args, "geocode", False),
    )

    def _describe(new_items) -> None:
        pipeline = WorkspacePipeline(ws, provider)
        for event in pipeline.run_items(new_items, options):
            if event.success:
                desc = event.item.active_description
                if not args.quiet:
                    print(f"Described: {event.item.display_name}")
                    if desc:
                        preview = desc.text[:120] + ("..." if len(desc.text) > 120 else "")
                        print(f"  {preview}\n")
                elif desc:
                    print(f"{event.item.source_path}\t{desc.text}")
            else:
                print(f"Error: {event.item.display_name}: {event.error}", file=sys.stderr)
        if any(i.described for i in new_items):
            ws.defaults.provider = provider_name
            ws.defaults.model = model
            ws.has_any_descriptions = True
            ws.save_manifest()

    def _add_source_images(paths) -> list:
        added = []
        for p in sorted(paths):
            added.append(ws.add_image(
                p,
                subfolder=source_relative_subfolder(p, source),
                copy=ws.copy_originals,
            ))
        return added

    try:
        # Initial pass: add everything currently in the folder and describe what's new.
        known = set(scan_images(source))
        initial = [i for i in _add_source_images(known) if not i.described]
        if initial:
            _describe(initial)

        # Poll loop
        while True:
            remaining = args.interval
            while remaining > 0:
                if not args.quiet and remaining % 30 == 0:
                    print(f"  ... next scan in {remaining}s", flush=True)
                time.sleep(min(5, remaining))
                remaining -= 5

            current = set(scan_images(source))
            new_paths = current - known
            known |= current
            if new_paths:
                new_items = [i for i in _add_source_images(new_paths) if not i.described]
                if new_items:
                    _describe(new_items)
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
    Show progress and token/cost breakdown across one or more workspaces.

    idt stats Vacation.idtw
    idt stats ~/Documents/idt/ --all
    idt stats Vacation.idtw --json
    """
    from idt_core.project import Project
    from idt_core.workspace import Workspace

    root = Path(args.source).resolve()

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

    # workspace_rows: [(name, total, described, undescribed), ...]
    workspace_rows = []
    described_items = []

    def _collect_ws(ws):
        st = ws.status()
        workspace_rows.append((ws.name, st["total"], st["described"], st["undescribed"]))
        described_items.extend(i for i in ws.media_items() if i.described)

    def _collect_proj(pr):
        all_items = list(pr.items())
        desc_items = list(pr.described())
        total = len(all_items)
        described = len(desc_items)
        workspace_rows.append((str(pr.source_dir), total, described, total - described))
        described_items.extend(desc_items)

    if args.all:
        for bundle in sorted(root.rglob("*.idtw")):
            if Workspace.is_bundle(bundle):
                try:
                    _collect_ws(Workspace.open(bundle))
                except Exception:
                    pass
        for idt_dir in sorted(root.rglob("*.idt")):
            source = idt_dir.parent / idt_dir.stem
            if source.is_dir():
                try:
                    _collect_proj(Project.open(source))
                except Exception:
                    pass
        if not workspace_rows:
            print(f"No IDT workspaces found under: {root}")
            return
    else:
        ws = _find_workspace(args.source)
        if ws is not None:
            _collect_ws(ws)
        else:
            if not root.is_dir():
                print(f"Error: not a directory: {root}", file=sys.stderr)
                sys.exit(1)
            _collect_proj(Project.open(root))

    # Accumulate token stats per provider+model
    totals: dict = {}
    grand_images = grand_in = grand_out = 0
    no_token_count = 0

    for item in described_items:
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

    if args.json_out:
        grand_total = sum(r[1] for r in workspace_rows)
        grand_described = sum(r[2] for r in workspace_rows)
        token_rows = []
        for (prov, model), d in sorted(totals.items()):
            cost_in, cost_out = COST_TABLE.get(model, (0, 0))
            cost = (d["input_tokens"] / 1_000_000 * cost_in +
                    d["output_tokens"] / 1_000_000 * cost_out)
            token_rows.append({
                "provider": prov, "model": model,
                "images": d["images"],
                "input_tokens": d["input_tokens"],
                "output_tokens": d["output_tokens"],
                "estimated_cost_usd": round(cost, 4) if cost else None,
            })
        print(json.dumps({
            "workspaces": [
                {"name": r[0], "total": r[1], "described": r[2], "undescribed": r[3]}
                for r in workspace_rows
            ],
            "grand_total": grand_total,
            "grand_described": grand_described,
            "token_breakdown": token_rows,
        }, indent=2))
        return

    # ── Progress section ────────────────────────────────────────────────
    grand_total = sum(r[1] for r in workspace_rows)
    grand_described = sum(r[2] for r in workspace_rows)
    pct = int(100 * grand_described / grand_total) if grand_total else 0

    print(f"Progress: {grand_described:,} of {grand_total:,} images described ({pct}%)")
    if len(workspace_rows) > 1:
        print()
        print(f"  {'Workspace':<40} {'Total':>6} {'Done':>6} {'Left':>6} {'%':>4}")
        print("  " + "-" * 60)
        for name, total, described, undescribed in workspace_rows:
            ws_pct = int(100 * described / total) if total else 0
            print(f"  {name:<40} {total:>6,} {described:>6,} {undescribed:>6,} {ws_pct:>3}%")

    if not totals:
        return

    # ── Token/cost section ──────────────────────────────────────────────
    print()
    print(f"Token usage: {grand_images:,} described images")
    if no_token_count:
        print(f"  (No token data for {no_token_count} image(s) — token counts may not be recorded for all runs)")
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
        total_in_str = f"{grand_in:,}" if grand_in else "n/a"
        total_out_str = f"{grand_out:,}" if grand_out else "n/a"
        print("-" * 90)
        print(f"{'TOTAL':<12} {'':<35} {grand_images:>7} {total_in_str:>10} {total_out_str:>11} {''!s:>10}")


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
        elif key == "workspace_root":
            cfg.workspace_root = value or None
        elif key == "preserve_alt_text":
            cfg.preserve_alt_text = value.strip().lower() not in ("false", "0", "no", "off")
        else:
            print(f"Unknown config key: {key!r}", file=sys.stderr)
            print("Valid keys: default_provider, default_model, default_prompt_name, "
                  "workspace_root, preserve_alt_text", file=sys.stderr)
            sys.exit(1)
        cfg.save()
        print(f"Set {key} = {value}")
        return

    print(f"Config file:      {Path.home() / '.idt' / 'config.json'}")
    print(f"default_provider: {cfg.default_provider}")
    print(f"default_model:    {cfg.default_model}")
    print(f"default_prompt:   {cfg.default_prompt_name}")
    print(f"workspace_root:   {cfg.workspace_root_path()}")
    print(f"preserve_alt_text: {cfg.preserve_alt_text}")
    if cfg.custom_prompts:
        print(f"custom_prompts:   {', '.join(cfg.custom_prompts.keys())}")


# ------------------------------------------------------------------ #
# guideme                                                              #
# ------------------------------------------------------------------ #

def cmd_guideme(args):
    from cli.guide import run_guide
    run_guide()


def cmd_version(args):
    try:
        from idt_core import __version__ as _v
        print(f"idt {_v}")
    except Exception:
        print("idt (version unknown)")
    print(f"Python {sys.version.split()[0]}")
    if getattr(sys, "frozen", False):
        print(f"Binary: {sys.executable}")
    # Deliberately no update check here: `idt version` should be instant and work
    # offline. Use `idt update` to check.


def cmd_update(args):
    """Report whether a newer release exists. Notify-only by design.

    Downloading and running the installer is the GUI's job (Help > Check for
    Updates); the installer updates idt and ImageDescriber together, so there is
    no separate CLI-only download to offer.
    """
    from idt_core import updater

    installed = updater.current_version()
    if not installed:
        print("Couldn't determine the installed version, so there is nothing to compare.")
        print(f"Releases: {updater.RELEASES_PAGE}")
        return
    print(f"Installed: idt {installed}")
    try:
        info = updater.check_for_update()
    except Exception as exc:
        print(f"Couldn't check for updates: {exc}")
        print(f"Releases: {updater.RELEASES_PAGE}")
        return

    if info is None:
        print("You are up to date.")
        return

    print(f"Available: idt {info['version']}")
    print("")
    print(f"Download:  {info.get('url') or info.get('page_url') or updater.RELEASES_PAGE}")
    print("Installing it updates both idt and ImageDescriber.")


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
  idt guideme                                            # start here — interactive wizard
  idt describe ~/Pictures/Vacation/
  idt describe ~/Pictures/Vacation/ --provider anthropic --model claude-opus-4-6
  idt describe ~/Pictures/Vacation/ --provider ollama --model llava
  idt describe ~/Pictures/Vacation/ --prompt concise --limit 10 --embed
  idt describe ~/Pictures/Vacation/ --geocode            # add city/state to prompt context
  idt describe ~/Pictures/Web/ --prompt aialttext --quiet
  idt download https://www.nytimes.com/ --max 20 --describe --prompt aialttext
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
  idt watch ~/Downloads/ --interval 60 --prompt aialttext
  get_nyt_images.bat | idt describe - --prompt aialttext --provider anthropic
  idt models
  idt models --provider ollama
  idt prompts
  idt stats ~/Pictures/Vacation/
  idt stats ~/Pictures/ --all                           # across entire photo library
  idt config --set default_provider=anthropic
  idt config --set default_model=claude-opus-4-6
  idt update                                            # is a newer release out?

Supported providers:
  anthropic  Claude (requires ANTHROPIC_API_KEY)
  openai     GPT-4o (requires OPENAI_API_KEY)
  ollama     Local models via Ollama (no API key)
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
            "Describe images in a directory. Creates a .idtw workspace bundle "
            "that holds the descriptions (and, with --copy-originals, copies of "
            "the images). Your original files are never modified. By default the "
            "bundle is named '<folder>.idtw' and created under the workspace root "
            "(~/Documents/idt — see 'idt config'); use --workspace to choose a "
            "different name or location."
        ),
    )
    p_desc.add_argument(
        "source",
        help="Directory containing images, or '-' to read image paths from stdin",
    )
    p_desc.add_argument("--workspace", "-w", metavar="NAME|PATH",
                        help="Workspace bundle to create/use. Bare name -> under the "
                             "workspace root; path or .idtw -> that exact location. "
                             "Default: '<source-folder>.idtw' under the workspace root.")
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
    p_desc.add_argument("--copy-originals", dest="copy_originals", action="store_true", default=None,
                        help="Copy source images into the workspace (self-contained, portable). "
                             "Overrides the workspace/config default for this run.")
    p_desc.add_argument("--no-copy-originals", dest="copy_originals", action="store_false",
                        help="Reference originals in place instead of copying them into the workspace.")
    p_desc.add_argument("--no-video", action="store_true",
                        help="Skip automatic video frame extraction (videos are included by default)")
    p_desc.add_argument("--video-interval", type=float, default=5.0, metavar="SECONDS",
                        help="Seconds between extracted video frames (default: 5.0)")
    p_desc.add_argument("--no-export", action="store_true",
                        help="Skip automatic HTML report generation after describing")
    p_desc.add_argument("--showgui", action="store_true",
                        help="Run this describe in the ImageDescriber GUI instead of the console: "
                             "the GUI opens on the directory, starts the batch, and shows live "
                             "progress. Closing the GUI ends the command.")
    p_desc.add_argument("--show-descriptions", action="store_true", dest="show_descriptions",
                        help="Print each description to the screen as it is generated")
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
            "Download images from a web page into a .idtw workspace (see 'idt describe "
            "--help' for the workspace model). Captures HTML alt text alongside each "
            "image. Use --describe to describe downloaded images immediately."
        ),
    )
    p_dl.add_argument("url", help="URL to download images from")
    p_dl.add_argument("directory", nargs="?",
                      help="Workspace name or path (default: derived from the URL's "
                           "domain, under the workspace root — see 'idt config')")
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
    p_dl.add_argument("--preserve-alt-text", dest="preserve_alt_text", action="store_true", default=None,
                      help="Save existing HTML alt text as an additional description. "
                           "Overrides the configured default for this run (see 'idt config').")
    p_dl.add_argument("--no-preserve-alt-text", dest="preserve_alt_text", action="store_false",
                      help="Do not save alt text as a description; keep it only as prompt context")
    p_dl.add_argument("--redescribe", dest="redescribe", action="store_true", default=True,
                      help="Generate an AI description even for images whose alt text was "
                           "preserved as a description (default: on)")
    p_dl.add_argument("--no-redescribe", dest="redescribe", action="store_false",
                      help="Skip AI description for images that already have a description "
                           "(e.g. preserved alt text)")
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
            "Extract frames from video files into a .idtw workspace's "
            "derived/frames/ folder (under the workspace root — see 'idt config'). "
            "Supports interval mode (one frame every N seconds) and scene-change "
            "detection. Use --describe to describe the extracted frames."
        ),
    )
    p_vid.add_argument("source", help="Video file or directory containing video files")
    p_vid.add_argument("--workspace", "-w", metavar="NAME|PATH",
                       help="Workspace to extract into (bare name → under the workspace "
                            "root; path/.idtw → that location). Default: mirrored from the source.")
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
    p_vid.add_argument("--redescribe", action="store_true",
                       help="Re-describe frames that already have a description")
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
            "Copy described images to <bundle>.idtw/embedded/ and write the description "
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
    p_models.add_argument("--refresh", action="store_true",
                          help="Ignore the cache and ask the APIs now")
    p_models.add_argument("--all", dest="all_models", action="store_true",
                          help="Include every model the API reports, skipping "
                               "the filter that hides non-chat OpenAI models")
    p_models.set_defaults(func=cmd_models)

    # ---------------------------------------------------------------- #
    # chat                                                             #
    # ---------------------------------------------------------------- #
    p_chat = sub.add_parser(
        "chat",
        help="Talk to an AI model from the terminal",
        description=(
            "Multi-turn chat with Ollama, Claude or OpenAI. Responses stream "
            "as they arrive. Ctrl+C stops a reply and keeps what arrived; "
            "Ctrl+D or /quit exits. Conversations are saved to ~/.idt/chats "
            "and share their format with ImageDescriber's chat items."
        ),
    )
    p_chat.add_argument("--provider", choices=["ollama", "claude", "openai", "anthropic"],
                        help="Which backend to talk to (default: ollama)")
    p_chat.add_argument("--model", help="Model id (default: the provider's default)")
    p_chat.add_argument("--system", metavar="TEXT",
                        help="System prompt for the conversation")
    p_chat.add_argument("--message", "-m", metavar="TEXT",
                        help="Send one message and exit instead of going interactive")
    p_chat.add_argument("--attach", metavar="PATH", action="append", default=[],
                        help=("Attach a file to the first message. Repeat for "
                              "several. HEIC is converted to JPEG."))
    p_chat.add_argument("--resume", metavar="ID",
                        help="Continue a saved conversation")
    p_chat.add_argument("--list", dest="list_sessions", action="store_true",
                        help="List saved conversations and exit")
    p_chat.add_argument("--no-save", action="store_true",
                        help="Do not write the conversation to disk")
    p_chat.add_argument("--max-tokens", type=int, metavar="N",
                        help="Cap the reply length")
    p_chat.add_argument("--temperature", type=float, metavar="F",
                        help="Sampling temperature")
    p_chat.add_argument("--web-search", action="store_true",
                        help=("Let the model search the web (Ollama only; "
                              "needs a free ollama.com API key in "
                              "OLLAMA_API_KEY)"))
    p_chat.add_argument("--think", dest="thinking", action="store_const",
                        const=True, default=None,
                        help="Force reasoning-model thinking on (Ollama)")
    p_chat.add_argument("--no-think", dest="thinking", action="store_const",
                        const=False,
                        help="Force thinking off for faster answers (Ollama)")
    p_chat.add_argument("--show-thinking", action="store_true",
                        help="Stream the model's thinking to stderr")
    p_chat.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress status notes on stderr")
    p_chat.set_defaults(func=cmd_chat)

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
    p_watch.add_argument("--workspace", "-w", metavar="NAME|PATH",
                         help="Workspace to describe into (bare name → under the workspace "
                              "root; path/.idtw → that location). Default: mirrored from the source.")
    p_watch.add_argument("--interval", type=int, default=30, metavar="SECONDS",
                         help="Polling interval in seconds (default: 30)")
    _provider_args(p_watch)
    _prompt_args(p_watch)
    _metadata_args(p_watch)
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
            "images, broken down by provider and model. Local models (Ollama) "
            "do not report tokens so no cost is shown for them."
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
    # guideme                                                            #
    # ---------------------------------------------------------------- #
    p_guideme = sub.add_parser(
        "guideme",
        help="Interactive setup wizard — pick provider, model, directory, and run",
        description=(
            "Step-by-step wizard that asks you to choose a provider, model, image "
            "source, prompt style, and metadata options, then shows you the exact "
            "command and optionally runs it. Screen-reader friendly — no ANSI, no "
            "spinners, numbered choices throughout."
        ),
    )
    p_guideme.set_defaults(func=cmd_guideme)

    p_version = sub.add_parser("version", help="Print version information")
    p_version.set_defaults(func=cmd_version)

    p_update = sub.add_parser(
        "update",
        help="Check whether a newer release is available",
        description=(
            "Checks GitHub for a newer release and prints where to get it. "
            "The installer updates both idt and ImageDescriber."
        ),
    )
    p_update.set_defaults(func=cmd_update)

    return parser


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def main():
    # Ensure stdout/stderr can emit any Unicode character on Windows (cp1252 is the
    # default and chokes on arrows, curly quotes, etc. found in AI descriptions).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    _set_console_title("IDT - Image Description Toolkit")
    parser = build_parser()
    args = parser.parse_args()
    _cmd_titles = {
        "describe": "IDT - Describing Images",
        "download": "IDT - Downloading Images",
        "video":    "IDT - Extracting Video Frames",
        "export":   "IDT - Exporting Descriptions",
        "embed":    "IDT - Embedding Descriptions",
        "combine":  "IDT - Combining Descriptions",
        "watch":    "IDT - Watching for New Images",
        "guideme":  "IDT - Setup Wizard",
        "chat":     "IDT - Chat",
    }
    cmd = getattr(args, "command", None)
    if cmd and cmd in _cmd_titles:
        _set_console_title(_cmd_titles[cmd])
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
